"""
Lexsy Document AI - Flask API
REST endpoints for document processing
"""

import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import tempfile
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from .document_processor import DocumentProcessor

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'docx'}

# CORS Configuration - Production Ready
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
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
        'version': '1.0.0',
        'service': 'Lexsy Document AI Backend'
    })


@app.route('/api/process', methods=['POST'])
def process_document():
    """
    Upload and process a document
    
    Returns:
        - placeholders: List of detected placeholders
        - analyses: LLM-powered analysis if available, otherwise basic analysis
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
            # Process document - fast regex detection first
            processor = DocumentProcessor(temp_path)
            result = processor.process(analyze_with_llm=False)
            
            # Try to get LLM analysis
            try:
                result_with_llm = processor.process(analyze_with_llm=True)
                if result_with_llm.get('analyses'):
                    # Add unique IDs to each analysis based on position
                    for idx, analysis in enumerate(result_with_llm['analyses']):
                        analysis['placeholder_id'] = f"{analysis['placeholder_text']}_{idx}"
                    result['analyses'] = result_with_llm['analyses']
                    result['analyzed'] = True
                else:
                    result['analyzed'] = False
            except Exception as llm_error:
                # If LLM fails, use basic analysis
                print(f"LLM analysis failed (non-blocking): {str(llm_error)}")
                result['analyzed'] = False
                
                # Generate basic analyses without LLM
                if result.get('success') and result.get('placeholders'):
                    analyses = []
                    for idx, p in enumerate(result['placeholders']):
                        analyses.append({
                            'placeholder_text': p['text'],
                            'placeholder_name': p['name'],
                            'placeholder_id': f"{p['text']}_{idx}",
                            'data_type': 'string',
                            'description': f"Enter {p['name'].lower()}",
                            'suggested_question': f"What is the {p['name'].lower()}?",
                            'example': f"{p['name']} value",
                            'required': True,
                            'validation_hint': None
                        })
                    result['analyses'] = analyses
            
            return jsonify(result), 200
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    except Exception as e:
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
            
            # Debug: Log what we're trying to replace
            print(f"Attempting to fill {len(values)} placeholders")
            for key, val in list(values.items())[:3]:
                print(f"  {key[:50]}: {val[:30] if len(val) > 30 else val}")
            
            success, output_path = processor.fill_placeholders(values)
            
            if not success:
                print(f"Fill operation failed for file: {filename}")
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
        print(f"Fill endpoint error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate', methods=['POST'])
def validate_input():
    """
    Validate user input using LLM
    
    Request body:
    {
        "user_input": "user's text input",
        "field_type": "string/email/currency/date/phone/number/address",
        "field_name": "name of the field",
        "placeholder_name": "placeholder name for context"
    }
    
    Returns:
    {
        "is_valid": true/false,
        "is_ambiguous": true/false,
        "formatted_value": "auto-formatted if applicable",
        "confidence": 0.0-1.0,
        "message": "validation message",
        "clarification_needed": "clarification question if ambiguous"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        user_input = data.get('user_input', '').strip()
        field_type = data.get('field_type', 'string')
        field_name = data.get('field_name', 'field')
        placeholder_name = data.get('placeholder_name', '')
        
        if not user_input:
            return jsonify({
                'is_valid': False,
                'is_ambiguous': False,
                'formatted_value': '',
                'confidence': 0,
                'message': f'{field_name} cannot be empty',
                'clarification_needed': None
            }), 200
        
        # Import validator
        from .input_validator import InputValidator
        
        validator = InputValidator()
        validation_result = validator.validate_input(
            user_input=user_input,
            field_name=field_name,
            data_type=field_type,
            suggested_question=f"What is the {field_name.lower()}?"
        )
        
        # Convert to JSON-serializable format
        return jsonify({
            'is_valid': validation_result.is_valid,
            'is_ambiguous': validation_result.is_ambiguous,
            'formatted_value': validation_result.formatted_value,
            'confidence': validation_result.confidence,
            'message': validation_result.message,
            'clarification_needed': validation_result.clarification_needed,
            'what_was_entered': validation_result.what_was_entered,
            'what_expected': validation_result.what_expected,
            'suggestion': validation_result.suggestion,
            'example': validation_result.example
        }), 200
    
    except Exception as e:
        print(f"Validation error: {str(e)}")
        import traceback
        traceback.print_exc()
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
        
        # Get placeholders only (no LLM analysis)
        processor = DocumentProcessor(temp_path)
        result = processor.process(analyze_with_llm=False)
        
        # Clean up
        os.remove(temp_path)
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/validate-batch', methods=['POST'])
def validate_batch():
    """
    Validate multiple fields in parallel
    
    Request body:
    {
        "validations": [
            {
                "field": "tenant_name",
                "value": "12345",
                "type": "string",
                "name": "Tenant Name"
            },
            ...
        ]
    }
    
    Returns:
    {
        "results": [
            {
                "field": "tenant_name",
                "is_valid": false,
                "is_ambiguous": false,
                "message": "That looks like numbers...",
                ...
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        validations = data.get('validations', [])
        
        if not validations:
            return jsonify({'error': 'No validations provided'}), 400
        
        # Import validator
        from .input_validator import InputValidator
        
        def validate_field(validation_item):
            """Validate a single field - called in parallel"""
            try:
                validator = InputValidator()
                result = validator.validate_input(
                    user_input=validation_item.get('value', ''),
                    field_name=validation_item.get('name', validation_item.get('field', 'field')),
                    data_type=validation_item.get('type', 'string'),
                    suggested_question=f"What is the {validation_item.get('name', 'field').lower()}?"
                )
                
                # Return result with field identifier
                return {
                    'field': validation_item.get('field'),
                    'is_valid': result.is_valid,
                    'is_ambiguous': result.is_ambiguous,
                    'formatted_value': result.formatted_value,
                    'confidence': result.confidence,
                    'message': result.message,
                    'clarification_needed': result.clarification_needed,
                    'what_was_entered': result.what_was_entered,
                    'what_expected': result.what_expected,
                    'suggestion': result.suggestion,
                    'example': result.example
                }
            except Exception as e:
                print(f"Error validating field {validation_item.get('field')}: {str(e)}")
                return {
                    'field': validation_item.get('field'),
                    'is_valid': True,  # Fallback to valid if LLM fails
                    'is_ambiguous': False,
                    'formatted_value': validation_item.get('value', ''),
                    'confidence': 0.5,
                    'message': 'Validation skipped (LLM unavailable)',
                    'clarification_needed': None,
                    'what_was_entered': validation_item.get('value', ''),
                    'what_expected': '',
                    'suggestion': None,
                    'example': None
                }
        
        # Validate all fields in parallel
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(validate_field, v): v for v in validations}
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    validation_item = futures[future]
                    print(f"Thread error for {validation_item.get('field')}: {str(e)}")
                    results.append({
                        'field': validation_item.get('field'),
                        'is_valid': True,
                        'is_ambiguous': False,
                        'formatted_value': validation_item.get('value', ''),
                        'confidence': 0.5,
                        'message': 'Validation failed (error occurred)',
                        'clarification_needed': None,
                        'what_was_entered': validation_item.get('value', ''),
                        'what_expected': '',
                        'suggestion': None,
                        'example': None
                    })
        
        # Cross-field validation: Check date logic
        start_date_field = None
        end_date_field = None
        for result in results:
            field_name = result.get('field', '').lower()
            if 'start' in field_name and 'date' in field_name:
                start_date_field = result
            elif 'end' in field_name and 'date' in field_name:
                end_date_field = result
        
        # Validate date range if both dates are present and valid
        if start_date_field and end_date_field and start_date_field.get('is_valid') and end_date_field.get('is_valid'):
            try:
                from datetime import datetime
                start_str = start_date_field.get('formatted_value', '')
                end_str = end_date_field.get('formatted_value', '')
                
                # Try to parse dates
                start_date = datetime.strptime(start_str, '%Y-%m-%d')
                end_date = datetime.strptime(end_str, '%Y-%m-%d')
                
                if start_date >= end_date:
                    # Start date is after or equal to end date - invalid!
                    end_date_field['is_valid'] = False
                    end_date_field['message'] = f'End date must be after start date ({start_str}). Currently set to {end_str}.'
                    end_date_field['suggestion'] = f'The end date should be after {start_str}. Please enter a later date.'
                    end_date_field['what_expected'] = f'A date after {start_str}'
            except Exception as e:
                print(f"Date range validation error: {str(e)}")
                # If parsing fails, just continue - individual validation already handled it
        
        return jsonify({'results': results}), 200
    
    except Exception as e:
        print(f"Batch validation error: {str(e)}")
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
    port = int(os.getenv('API_PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
