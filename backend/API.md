# Lexsy Document AI - API Documentation

## Base URL
```
http://localhost:5000/api
```

---

## Endpoints

### 1. Health Check
Check if the API is running.

**Endpoint:** `GET /api/health`

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "Lexsy Document AI Backend"
}
```

---

### 2. Process Document
Upload a document and detect placeholders with LLM analysis.

**Endpoint:** `POST /api/process`

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `file` (required): The .docx document

**Response:**
```json
{
  "success": true,
  "document_path": "path/to/document.docx",
  "text_length": 5000,
  "placeholder_count": 13,
  "placeholders": [
    {
      "text": "[Company Name]",
      "name": "Company Name",
      "format": "bracket",
      "position": 1234
    }
  ],
  "analyses": [
    {
      "placeholder_text": "[Company Name]",
      "placeholder_name": "Company Name",
      "data_type": "string",
      "description": "The legal name of the company",
      "suggested_question": "What is your company name?",
      "example": "Acme Corp",
      "required": true,
      "validation_hint": "Must be a valid company name"
    }
  ],
  "analyzed": true
}
```

**Example cURL:**
```bash
curl -X POST -F "file=@document.docx" http://localhost:5000/api/process
```

---

### 3. Get Placeholders
Extract placeholders without LLM analysis (faster).

**Endpoint:** `POST /api/placeholders`

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `file` (required): The .docx document

**Response:**
```json
{
  "success": true,
  "document_path": "path/to/document.docx",
  "text_length": 5000,
  "placeholder_count": 13,
  "placeholders": [
    {
      "text": "[Company Name]",
      "name": "Company Name",
      "format": "bracket",
      "position": 1234
    }
  ]
}
```

---

### 4. Fill Document
Fill placeholders in a document with provided values.

**Endpoint:** `POST /api/fill`

**Request:**
- Content-Type: `multipart/form-data`
- Body:
  - `file` (required): The .docx document
  - `values` (required): JSON string with placeholder values

**Example Request:**
```bash
curl -X POST \
  -F "file=@document.docx" \
  -F 'values={"[Company Name]": "Acme Corp", "[Date]": "2024-11-02"}' \
  http://localhost:5000/api/fill \
  -o filled_document.docx
```

**Response:**
- Returns the filled .docx file as binary data
- Or error JSON if failed

---

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Error message describing what went wrong"
}
```

**Common Errors:**
- `400`: No file provided / Invalid file type
- `500`: Server error (check logs)

---

## Data Types Returned by LLM Analysis

- `string`: Text value
- `email`: Email address
- `currency`: Money amount
- `date`: Date value
- `number`: Numeric value
- `phone`: Phone number
- `address`: Physical address
- `url`: Website URL

---

## Running the API

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The API will start on `http://localhost:5000`

---

## Integration Example

```python
import requests
import json

# 1. Upload and process
files = {'file': open('document.docx', 'rb')}
response = requests.post('http://localhost:5000/api/process', files=files)
result = response.json()

placeholders = result['placeholders']
analyses = result['analyses']

# 2. Collect user values
values = {}
for analysis in analyses:
    user_input = input(f"{analysis['suggested_question']}: ")
    values[analysis['placeholder_text']] = user_input

# 3. Fill document
files = {'file': open('document.docx', 'rb')}
data = {'values': json.dumps(values)}
response = requests.post('http://localhost:5000/api/fill', files=files, data=data)

# 4. Save filled document
with open('filled_document.docx', 'wb') as f:
    f.write(response.content)
```
