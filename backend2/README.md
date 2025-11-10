# Backend2 - Document Processing API

Production-ready Flask API for intelligent document placeholder detection and replacement using python-docx and LLM analysis.

## Features

- ✅ **Intelligent Placeholder Detection**: Detects explicit placeholders (`[text]`, `{text}`, `(text)`) and implicit label fields (`Label: `)
- ✅ **LLM-Powered Analysis**: Uses OpenRouter API to analyze placeholders, provide context, suggest questions, and deduplicate fields
- ✅ **Context-Aware Replacement**: Handles multiple occurrences of the same placeholder text based on surrounding context
- ✅ **Formatting Preservation**: Maintains original formatting (bold, italic, underline, font, size, color) during replacement
- ✅ **Smart Field Matching**: Distinguishes between identical placeholder texts in different contexts (e.g., `[_____________]` for Purchase Amount vs Post-Money Valuation Cap)
- ✅ **Table Support**: Handles placeholders in both paragraphs and tables
- ✅ **Production Ready**: Configurable logging, error handling, and environment-based settings

## Setup

### 1. Install Dependencies

```bash
cd backend2
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file (optional, for LLM features):

```bash
OPENROUTER_API_KEY=your_api_key_here
```

### 3. Run the API Server

**Development:**
```bash
python app.py
# or
python run.py
```

**Production:**
```bash
ENVIRONMENT=production API_PORT=5001 python app.py
```

The server will start on `http://localhost:5001` by default.

## API Endpoints

### Health Check
```bash
GET /api/health
```

Returns server status and version information.

### Process Document (Detect Placeholders + LLM Analysis)
```bash
POST /api/process
Content-Type: multipart/form-data
Body: file=<docx_file>
```

Detects placeholders and analyzes them with LLM. Returns:
- `placeholders`: List of detected placeholders
- `analyses`: LLM-analyzed fields with questions, examples, and data types
- `placeholder_count`: Number of placeholders found
- `analyzed`: Whether LLM analysis was successful

### Fill Placeholders
```bash
POST /api/fill
Content-Type: multipart/form-data
Body: 
  - file=<docx_file>
  - values={"placeholder_text": "value", "placeholder_text__field_fieldname": "value", ...}
```

Fills placeholders in the document and returns the filled document as a `.docx` file.

**Value Format:**
- Simple placeholder: `"[Company Name]": "Acme Corp"`
- Field-based (for multiple occurrences): `"[_____________]__field_purchase_amount": "100000"`
- Label field: `"Address: ": "123 Main St"`

### Get Placeholders Only (No LLM)
```bash
POST /api/placeholders
Content-Type: multipart/form-data
Body: file=<docx_file>
```

Fast endpoint that returns only detected placeholders without LLM analysis.

### Validate Input
```bash
POST /api/validate
Content-Type: application/json
Body: {
  "user_input": "value",
  "field_type": "string",
  "field_name": "name",
  "placeholder_name": "name"
}
```

Validates a single field input.

### Validate Batch
```bash
POST /api/validate-batch
Content-Type: application/json
Body: {
  "validations": [
    {"field": "field_id", "value": "input", "type": "string", "name": "Field Name"}
  ]
}
```

Validates multiple fields in parallel.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_PORT` | Port to run the server on | `5001` |
| `CORS_ORIGINS` | Comma-separated CORS origins | `http://localhost:3000,http://localhost:3001` |
| `ENVIRONMENT` | `production` or `development` | `development` |
| `VERBOSE_LOGGING` | Enable verbose operation logs | `false` |
| `OUTPUT_DIR` | Directory for filled documents | Temp dir (production) or `output/` (development) |
| `OPENROUTER_API_KEY` | API key for LLM analysis | Required for LLM features |

## Example Usage

### Using curl

```bash
# Detect placeholders with LLM analysis
curl -X POST http://localhost:5001/api/process \
  -F "file=@document.docx"

# Fill placeholders
curl -X POST http://localhost:5001/api/fill \
  -F "file=@document.docx" \
  -F 'values={"[Company Name]": "Acme Inc", "Address: ": "123 Main St"}' \
  --output filled_document.docx
```

### Using Python

```python
import requests
import json

# Process document
with open('document.docx', 'rb') as f:
    response = requests.post(
        'http://localhost:5001/api/process',
        files={'file': f}
    )
    result = response.json()
    print(f"Found {result['placeholder_count']} placeholders")
    print(f"LLM analyzed {len(result['analyses'])} fields")

# Fill placeholders
values = {
    "[Company Name]": "Acme Inc",
    "[_____________]__field_purchase_amount": "100000",
    "Address: ": "123 Main St"
}

with open('document.docx', 'rb') as f:
    response = requests.post(
        'http://localhost:5001/api/fill',
        files={'file': f},
        data={'values': json.dumps(values)}
    )
    with open('filled_document.docx', 'wb') as out:
        out.write(response.content)
```

## How It Works

1. **Placeholder Detection**: Uses regex patterns to detect explicit placeholders and heuristics for label fields
2. **LLM Analysis**: Analyzes detected placeholders with context to:
   - Identify actual form fields vs legal text
   - Deduplicate similar placeholders
   - Distinguish identical placeholder texts in different contexts
   - Generate user-friendly questions and examples
3. **Smart Replacement**: 
   - Explicit placeholders (`[text]`): Replaced entirely
   - Label fields (`Label: `): Value inserted after label, preserving formatting
   - Multiple occurrences: Matched by context using field names
4. **Formatting Preservation**: Maintains original text formatting during replacement

## Production Deployment

For production deployment:

1. Set environment variables:
   ```bash
   export ENVIRONMENT=production
   export API_PORT=5001
   export CORS_ORIGINS=https://your-frontend-domain.com
   export VERBOSE_LOGGING=false
   ```

2. Use a production WSGI server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5001 --timeout 120 app:app
   ```

3. Configure frontend to use production API URL:
   ```bash
   NEXT_PUBLIC_API_URL=https://your-backend-domain.com
   ```

## Architecture

- `app.py` - Flask API server with REST endpoints
- `document_processor.py` - Orchestrates document processing and placeholder filling
- `document_handler.py` - Handles Word document operations (load, replace, save)
- `placeholder_detector.py` - Detects placeholders using regex and heuristics
- `llm_analyzer.py` - LLM integration for placeholder analysis
- `main.py` - CLI tool for interactive document processing

## License

See main project LICENSE file.
