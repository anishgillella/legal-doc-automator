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
except ImportError as e:
    print(f"ERROR: Failed to import DocumentProcessor: {e}", file=sys.stderr)
    print(f"Python path: {sys.path}", file=sys.stderr)
    raise

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'docx'}

# CORS Configuration
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
        'version': '2.0.0',
        'service': 'Lexsy Document AI Backend2 (python-docx)'
    })


@app.route('/api/process', methods=['POST'])
def process_document():
    """
    Upload and process a document
    
    Returns:
        - placeholders: List of detected placeholders (explicit and implicit)
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
            print(f"\n{'='*80}")
            print(f"FILL OPERATION - Attempting to fill {len(values)} placeholders")
            print(f"{'='*80}")
            for key, val in values.items():
                val_preview = val[:40] if len(val) > 40 else val
                print(f"  Placeholder: {key:40} | Value: {val_preview}")
            print(f"{'='*80}\n")
            
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
        
        # Get placeholders only
        processor = DocumentProcessor(temp_path)
        result = processor.process()
        
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
    environment = os.getenv('ENVIRONMENT', 'development')
    debug_mode = environment == 'development'
    
    app.run(debug=debug_mode, host='0.0.0.0', port=port)

