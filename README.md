# LexAI - Intelligent Document Completion

AI-powered full-stack application for automatically detecting placeholders in legal documents, analyzing their context using LLMs, and enabling intelligent document filling with a modern web interface.

## Overview

LexAI is a complete document processing solution consisting of:

1. **Frontend** - Next.js web application with TypeScript and React
2. **Backend** - Flask REST API for document processing
3. **AI Analysis** - LLM-powered placeholder detection and context understanding

### Key Features

- **Intelligent Placeholder Detection** - Detects various placeholder formats (`[text]`, `{text}`, `_text_`, etc.) and label fields
- **LLM-Powered Analysis** - Uses OpenRouter API (Qwen2.5) to understand placeholder context and requirements
- **Smart Field Matching** - Distinguishes identical placeholders in different contexts
- **Formatting Preservation** - Maintains original document formatting during replacement
- **Modern Web UI** - Beautiful, responsive interface built with Next.js and Tailwind CSS
- **Real-time Validation** - AI-powered input validation with helpful suggestions
- **Production Ready** - Docker support, environment-based configuration, and error handling

## Architecture

### Project Structure

```
Lexys AI/
├── frontend/          # Next.js frontend (TypeScript, React, Tailwind)
├── backend2/          # Flask backend API (Python)
└── Dockerfile         # Docker configuration
```

### Technology Stack

**Frontend:** Next.js 14, TypeScript, React 18, Tailwind CSS, Framer Motion, Three.js, Axios  
**Backend:** Flask, python-docx, OpenRouter API, Gunicorn

## Quick Start

### Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.8+ (for backend)
- **OpenRouter API Key** - Get one at https://openrouter.io

### Local Development

#### Backend Setup

```bash
cd backend2
pip install -r requirements.txt

# Create .env file
echo "OPENROUTER_API_KEY=your_api_key_here" > .env
echo "API_PORT=5001" >> .env
echo "CORS_ORIGINS=http://localhost:3000" >> .env

python app.py
```

Backend runs on `http://localhost:5001`

#### Frontend Setup

```bash
cd frontend
npm install

# Optional: Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:5001" > .env.local

npm run dev
```

Frontend runs on `http://localhost:3000`

### Docker Deployment

See [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) for details.

**Quick Start:**
```bash
docker build -t lexys-ai-backend:latest .
docker run -p 5001:5001 \
  -e OPENROUTER_API_KEY=your_key_here \
  -e API_PORT=5001 \
  -e CORS_ORIGINS=http://localhost:3000 \
  lexys-ai-backend:latest
```

## API Endpoints

### Core Endpoints

**`GET /api/health`** - Health check

**`POST /api/process`** - Process document (detect placeholders + LLM analysis)
- Body: `multipart/form-data` with `file=<docx_file>`
- Returns: `placeholders`, `analyses`, `placeholder_count`, `analyzed`

**`POST /api/fill`** - Fill placeholders and return completed document
- Body: `multipart/form-data` with `file` and `values` (JSON string)
- Returns: Filled `.docx` file

**`POST /api/placeholders`** - Fast placeholder detection (no LLM)
- Body: `multipart/form-data` with `file=<docx_file>`

**`POST /api/validate`** - Validate single field input
- Body: JSON with `user_input`, `field_type`, `field_name`, `placeholder_name`

**`POST /api/validate-batch`** - Validate multiple fields in parallel
- Body: JSON with `validations` array

### Response Example

```json
{
  "success": true,
  "placeholder_count": 5,
  "placeholders": [{"text": "[Company Name]", "name": "Company Name", "format": "square_brackets"}],
  "analyses": [{
    "placeholder_text": "[Company Name]",
    "placeholder_name": "Company Name",
    "data_type": "string",
    "suggested_question": "What is the company's legal name?",
    "example": "Acme Corporation",
    "required": true
  }],
  "analyzed": true
}
```

## Supported Placeholder Formats

- `[placeholder]` - Square brackets
- `{placeholder}` - Curly brackets
- `{{placeholder}}` - Double curly brackets
- `_placeholder_` - Single underscore
- `__placeholder__` - Double underscore
- `<placeholder>` - Angle brackets
- `Label: ` - Label fields (implicit placeholders)

## How It Works

1. **Document Upload** - User uploads `.docx` file through web interface
2. **Placeholder Detection** - Backend uses regex patterns and heuristics to detect placeholders
3. **LLM Analysis** - Each placeholder analyzed with context using OpenRouter API to:
   - Identify actual form fields vs legal text
   - Deduplicate similar placeholders
   - Distinguish identical placeholder texts in different contexts
   - Generate user-friendly questions and examples
   - Determine data types and validation rules
4. **Form Generation** - Frontend generates dynamic form with AI-suggested questions, validation, and examples
5. **Document Filling** - Backend replaces placeholders while preserving formatting
6. **Download** - User downloads the completed document

## Architecture Details

### Backend Modules

- **`document_handler.py`** - Loads, parses, and modifies .docx files with formatting preservation
- **`placeholder_detector.py`** - Detects placeholders using regex patterns and heuristics
- **`llm_analyzer.py`** - Integrates with OpenRouter API for context analysis
- **`document_processor.py`** - Orchestrates the entire workflow

### Frontend Components

- **UploadZone** - File upload with drag-and-drop
- **FormField** - Dynamic form fields with validation
- **ProgressBar** - Progress tracking
- **ParsingLoader** - Loading states during processing
- **FormContext** - Global form state management
- **apiService** - Centralized API communication

## Environment Variables

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `API_PORT` | Server port | `5001` |
| `CORS_ORIGINS` | CORS origins (comma-separated) | `http://localhost:3000,http://localhost:3001` |
| `ENVIRONMENT` | `production` or `development` | `development` |
| `OPENROUTER_API_KEY` | LLM API key | Required |
| `VERBOSE_LOGGING` | Enable verbose logs | `false` |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:5001` |

## Production Deployment

### Backend

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 --timeout 120 app:app
```

Or set `ENVIRONMENT=production` with Docker.

### Frontend

```bash
cd frontend
npm run build
npm start
```

See [RAILWAY_SETUP.md](./RAILWAY_SETUP.md) for Railway deployment.

## Performance

- Placeholder Detection: < 100ms
- LLM Analysis: 2-5 seconds
- Placeholder Filling: < 200ms
- Document Saving: < 500ms
- Frontend Load: < 2 seconds

## Document Formatting Preservation

Preserves paragraph alignment, spacing, font properties (name, size, color), text formatting (bold, italic, underline), document structure, and table formatting.

## Error Handling

**Backend not accessible** - Check port, verify `NEXT_PUBLIC_API_URL`, check CORS  
**OpenRouter API key not found** - Add to `.env` file; system falls back to heuristics  
**Placeholder not replaced** - Text must match exactly (case-sensitive)  
**LLM analysis fails** - System automatically falls back to heuristic analysis

## Development

```bash
# Backend tests
cd backend2 && python test_backend.py

# Frontend type checking
cd frontend && npm run type-check
```

## Roadmap

- [ ] Batch processing multiple documents
- [ ] Template creation and management
- [ ] Advanced placeholder validation rules
- [ ] Multi-language support
- [ ] PDF support
- [ ] Document signing integration
- [ ] User authentication and document history

## License

Internal use only - Lexsy AI

## Support

For issues or questions, contact: tech@lexsy.ai

## Additional Documentation

- [Docker Deployment Guide](./DOCKER_DEPLOYMENT.md)
- [Railway Setup Guide](./RAILWAY_SETUP.md)
- [Backend API Documentation](./backend2/README.md)
