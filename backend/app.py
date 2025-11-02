"""
Lexsy Document AI - Flask API
REST endpoints for document processing
"""

from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import tempfile
import json
from .document_processor import DocumentProcessor

app = Flask(__name__)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'docx'}

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
        - analyses: LLM analysis for each placeholder
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
        
        # Process document
        processor = DocumentProcessor(temp_path)
        result = processor.process(analyze_with_llm=True)
        
        # Clean up temp file
        os.remove(temp_path)
        
        return jsonify(result), 200
    
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
        
        values = json.loads(values)
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        
        # Process document
        processor = DocumentProcessor(temp_path)
        success, output_path = processor.fill_placeholders(values)
        
        # Clean up original temp file
        os.remove(temp_path)
        
        if not success:
            return jsonify({'error': 'Failed to fill document'}), 500
        
        # Send filled document
        return send_file(
            output_path,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name='filled_document.docx'
        )
    
    except Exception as e:
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
    app.run(debug=True, host='0.0.0.0', port=5000)
