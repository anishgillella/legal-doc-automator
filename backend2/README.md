# Backend2 - Document Processing API

Document processing API using python-docx for placeholder detection and replacement.

## Setup

### 1. Install dependencies

```bash
cd backend2
pip install -r requirements.txt
```

### 2. Run the API server

```bash
python app.py
```

The server will start on `http://localhost:5000` by default.

You can change the port by setting the `API_PORT` environment variable:
```bash
API_PORT=8000 python app.py
```

## API Endpoints

### Health Check
```bash
GET /api/health
```

### Process Document (Detect Placeholders)
```bash
POST /api/process
Content-Type: multipart/form-data
Body: file=<docx_file>
```

### Fill Placeholders
```bash
POST /api/fill
Content-Type: multipart/form-data
Body: 
  - file=<docx_file>
  - values={"placeholder_text": "value", ...}
```

### Get Placeholders Only
```bash
POST /api/placeholders
Content-Type: multipart/form-data
Body: file=<docx_file>
```

## Example Usage

### Using curl

```bash
# Detect placeholders
curl -X POST http://localhost:5000/api/process \
  -F "file=@document.docx"

# Fill placeholders
curl -X POST http://localhost:5000/api/fill \
  -F "file=@document.docx" \
  -F 'values={"[Company Name]": "Acme Inc", "Name: ": "John Doe"}' \
  --output filled_document.docx
```

### Using Python

```python
import requests

# Process document
with open('document.docx', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/process',
        files={'file': f}
    )
    placeholders = response.json()
    print(placeholders)

# Fill placeholders
values = {
    "[Company Name]": "Acme Inc",
    "Name: ": "John Doe"
}

with open('document.docx', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/fill',
        files={'file': f},
        data={'values': json.dumps(values)}
    )
    with open('filled_document.docx', 'wb') as out:
        out.write(response.content)
```

## Environment Variables

- `API_PORT` - Port to run the server on (default: 5000)
- `CORS_ORIGINS` - Comma-separated list of allowed CORS origins (default: http://localhost:3000)
- `ENVIRONMENT` - Set to 'development' for debug mode (default: development)

## Features

- ✅ Detects explicit placeholders: `[text]`, `{text}`, `(text)`, etc.
- ✅ Detects implicit placeholders: `Label: ` (blank fields)
- ✅ Smart replacement: Different logic for bracketed vs blank fields
- ✅ Table support: Handles placeholders in tables
- ✅ Position-based replacement: Replace specific occurrences
- ✅ Free & local: Uses python-docx only, no API costs

## See Also

- `IMPLEMENTATION_SUMMARY.md` - Detailed implementation documentation
