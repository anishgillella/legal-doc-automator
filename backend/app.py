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


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.getenv('API_PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
