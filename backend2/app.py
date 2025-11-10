"""
Lexsy Document AI - Flask API for backend2
REST endpoints for document processing using python-docx only
"""

import os
import sys
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import json

try:
    from document_processor import DocumentProcessor
    from llm_analyzer import LLMAnalyzer
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}", file=sys.stderr)
    print(f"Python path: {sys.path}", file=sys.stderr)
    raise

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'docx'}

# CORS Configuration
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:3001').split(',')
CORS(app, resources={
    r"/api/*": {
        "origins": cors_origins,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '2.0.0',
        'service': 'Lexsy Document AI Backend2 (python-docx)'
    })


@app.route('/api/process', methods=['POST'])
def process_document():
    """
    Upload and process a document with LLM analysis
    
    Returns:
        - placeholders: List of detected placeholders
        - analyses: List of PlaceholderAnalysis objects with LLM context
    """
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only .docx files are allowed'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        try:
            # Process document
            processor = DocumentProcessor(temp_path)
            result = processor.process()
            
            if not result.get('success'):
                return jsonify(result), 200
            
            # Add LLM analysis if placeholders were found
            analyses = []
            analyzed = False
            
            if result.get('placeholder_count', 0) > 0:
                try:
                    llm_analyzer = LLMAnalyzer()
                    placeholders_data = result.get('placeholders', [])
                    full_text = processor.full_text
                    
                    # Analyze with LLM
                    llm_analyses = llm_analyzer.analyze_placeholders_with_context(
                        full_text, 
                        placeholders_data
                    )
                    
                    # Convert PlaceholderAnalysis objects to dict format
                    for idx, analysis in enumerate(llm_analyses):
                        # Create unique placeholder_id based on position
                        placeholder_id = f"{analysis.placeholder_text}__pos_{idx}"
                        
                        analyses.append({
                            'placeholder_text': analysis.placeholder_text,
                            'placeholder_name': analysis.placeholder_name,
                            'placeholder_id': placeholder_id,
                            'data_type': analysis.data_type,
                            'description': analysis.description,
                            'suggested_question': analysis.suggested_question,
                            'example': analysis.example,
                            'required': analysis.required,
                            'validation_hint': analysis.validation_hint
                        })
                    
                    analyzed = True
                    
                except Exception as e:
                    print(f"LLM analysis failed: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
                    # Fallback: create basic analyses from placeholders
                    for idx, ph in enumerate(result.get('placeholders', [])):
                        placeholder_id = f"{ph['text']}__pos_{idx}"
                        analyses.append({
                            'placeholder_text': ph['text'],
                            'placeholder_name': ph['name'],
                            'placeholder_id': placeholder_id,
                            'data_type': 'string',
                            'description': f"Field: {ph['name']}",
                            'suggested_question': f"What is the {ph['name'].lower().replace('_', ' ')}?",
                            'example': '',
                            'required': False,
                            'validation_hint': None
                        })
            
            # Add analyses to result
            result['analyses'] = analyses
            result['analyzed'] = analyzed
            result['status'] = 'success' if analyzed else ('no_placeholders' if result.get('placeholder_count', 0) == 0 else 'success_no_llm')
            
            return jsonify(result), 200
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        print(f"Process endpoint error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/fill', methods=['POST'])
def fill_document():
    """
    Fill placeholders in a document
    
    Request body:
    {
        "file": <binary file>,
        "values": {
            "placeholder_text": "value",
            ...
        }
    }
    
    Returns:
        - Filled document as .docx file
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only .docx files are allowed'}), 400
        
        # Get values from JSON
        values = request.form.get('values')
        if not values:
            return jsonify({'error': 'No values provided'}), 400
        
        try:
            values = json.loads(values)
        except json.JSONDecodeError as e:
            return jsonify({'error': f'Invalid JSON in values: {str(e)}'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        try:
            # Process document
            processor = DocumentProcessor(temp_path)
            
            success, output_path = processor.fill_placeholders(values)
            
            if not success:
                print(f"Fill operation failed for file: {filename}", file=sys.stderr)
                return jsonify({'error': 'Failed to fill document'}), 500
            
            # Send filled document
            return send_file(
                output_path,
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                as_attachment=True,
                download_name='filled_document.docx'
            )
        
        finally:
            # Clean up original temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
        print(f"Fill endpoint error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({'error': str(e)}), 500


@app.route('/api/placeholders', methods=['POST'])
def get_placeholders():
    """
    Extract placeholders from a document without processing
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Only .docx files are allowed'}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        # Get placeholders only
        processor = DocumentProcessor(temp_path)
        result = processor.process()
        
        # Clean up
        os.remove(temp_path)
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate', methods=['POST'])
def validate_input():
    """
    Validate a single field input using LLM
    
    Request body:
    {
        "user_input": "value",
        "field_type": "string",
        "field_name": "name",
        "placeholder_name": "name"
    }
    
    Returns:
        ValidationResponse object
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_input = data.get('user_input', '')
        field_type = data.get('field_type', 'string')
        field_name = data.get('field_name', '')
        placeholder_name = data.get('placeholder_name', field_name)
        
        if not user_input:
            return jsonify({
                'field': placeholder_name,
                'is_valid': False,
                'is_ambiguous': False,
                'formatted_value': '',
                'confidence': 0.0,
                'message': 'Input is required',
                'clarification_needed': None,
                'what_was_entered': user_input,
                'what_expected': f'A valid {field_type} value',
                'suggestion': None,
                'example': None
            }), 200
        
        try:
            llm_analyzer = LLMAnalyzer()
            
            # Simple validation - in a real implementation, you'd use LLM
            # For now, return basic validation
            is_valid = len(user_input.strip()) > 0
            formatted_value = user_input.strip()
            
            return jsonify({
                'field': placeholder_name,
                'is_valid': is_valid,
                'is_ambiguous': False,
                'formatted_value': formatted_value,
                'confidence': 1.0 if is_valid else 0.0,
                'message': 'Valid' if is_valid else 'Invalid input',
                'clarification_needed': None,
                'what_was_entered': user_input,
                'what_expected': f'A valid {field_type} value',
                'suggestion': None,
                'example': None
            }), 200
            
        except Exception as e:
            print(f"Validation error: {e}", file=sys.stderr)
            return jsonify({
                'field': placeholder_name,
                'is_valid': True,  # Default to valid on error
                'is_ambiguous': False,
                'formatted_value': user_input,
                'confidence': 0.5,
                'message': 'Validation unavailable',
                'clarification_needed': None,
                'what_was_entered': user_input,
                'what_expected': None,
                'suggestion': None,
                'example': None
            }), 200
    
    except Exception as e:
        print(f"Validate endpoint error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate-batch', methods=['POST'])
def validate_batch():
    """
    Validate multiple fields in batch
    
    Request body:
    {
        "validations": [
            {
                "field": "field_id",
                "value": "user input",
                "type": "string",
                "name": "field name"
            },
            ...
        ]
    }
    
    Returns:
        {
            "results": [ValidationResponse, ...]
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        validations = data.get('validations', [])
        
        if not validations:
            return jsonify({'results': []}), 200
        
        results = []
        
        for validation in validations:
            field = validation.get('field', '')
            value = validation.get('value', '')
            field_type = validation.get('type', 'string')
            field_name = validation.get('name', field)
            
            # Basic validation
            is_valid = len(value.strip()) > 0 if value else False
            formatted_value = value.strip() if value else ''
            
            results.append({
                'field': field,
                'is_valid': is_valid,
                'is_ambiguous': False,
                'formatted_value': formatted_value,
                'confidence': 1.0 if is_valid else 0.0,
                'message': 'Valid' if is_valid else 'Invalid input',
                'clarification_needed': None,
                'what_was_entered': value,
                'what_expected': f'A valid {field_type} value' if not is_valid else None,
                'suggestion': None,
                'example': None
            })
        
        return jsonify({'results': results}), 200
    
    except Exception as e:
        print(f"Batch validate endpoint error: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Railway sets PORT, fallback to API_PORT, then default to 5001
    port = int(os.getenv('PORT') or os.getenv('API_PORT', 5001))
    environment = os.getenv('ENVIRONMENT', 'development')
    debug_mode = environment == 'development'
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

