# LexAI Docker Deployment Guide

## Overview
This guide explains how to build and run the LexAI application using Docker. The application consists of:
- **Backend**: Flask API (Python) running on port 5000
- **Frontend**: Next.js application (Node.js) running on port 3000

## Prerequisites
- Docker & Docker Compose installed
- API credentials (OpenRouter API key for LLM features)

## Building the Backend Docker Image

### Build Command
```bash
docker build -t lexys-ai-backend:latest .
```

### Image Details
- **Base Image**: `python:3.11-slim`
- **Multi-stage Build**: Uses builder stage to optimize image size
- **Port**: 5000 (configurable via `API_PORT` environment variable)
- **Health Check**: Enabled (30s interval, 40s startup period)

## Running the Backend Container

### Basic Run
```bash
docker run -p 5000:5000 lexys-ai-backend:latest
```

### With Environment Variables
```bash
docker run -p 5000:5000 \
  -e API_PORT=5000 \
  -e OPENROUTER_API_KEY=your_key_here \
  -e CORS_ORIGINS=http://localhost:3000 \
  lexys-ai-backend:latest
```

### Available Environment Variables
- `API_PORT` (default: 5000) - Port the Flask app runs on
- `OPENROUTER_API_KEY` - API key for LLM analysis (optional but recommended)
- `CORS_ORIGINS` (default: http://localhost:3000) - Comma-separated CORS origins
- `ENVIRONMENT` (default: production) - Flask environment

## Docker Compose Setup

### docker-compose.yml Example
```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    environment:
      - API_PORT=5000
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - CORS_ORIGINS=http://localhost:3000
    healthcheck:
      test: ["CMD", "python", "-c", "import socket; socket.create_connection(('localhost', 5000), timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:5000
    depends_on:
      - backend
```

## Application Architecture

### Backend Structure
```
backend/
├── app.py                 # Flask application & API routes
├── document_handler.py    # .docx file handling
├── document_processor.py  # Main processing orchestration
├── placeholder_detector.py # Placeholder detection logic
├── llm_analyzer.py        # LLM integration for analysis
├── input_validator.py     # Input validation
├── requirements.txt       # Python dependencies
```

### API Endpoints
- `GET /api/health` - Health check
- `POST /api/process` - Upload and process document
- `POST /api/fill` - Fill placeholders with values
- `POST /api/validate` - Validate single input
- `POST /api/validate-batch` - Validate multiple inputs
- `POST /api/placeholders` - Extract placeholders only

## Key Features

### Document Processing
1. **Fast Path**: Regex-based placeholder detection (< 100ms)
2. **Smart Path**: LLM analysis for context understanding (2-5 seconds)
3. **Fallback**: Heuristic analysis if LLM fails

### Supported Placeholder Formats
- `_placeholder_` (underscore)
- `__placeholder__` (double underscore)
- `[placeholder]` (square brackets)
- `{placeholder}` (curly brackets)
- `{{placeholder}}` (double curly brackets)
- `<placeholder>` (angle brackets)

### Data Types
- String
- Email
- Currency
- Date
- Phone
- Number
- Address
- URL

## Handling Documents with No Placeholders

The application gracefully handles documents that don't contain any placeholder fields:

1. **Detection**: Backend returns `status: "no_placeholders"`
2. **User Interface**: Frontend shows a friendly message
3. **Options**: Users can download the original or upload another document

## Performance Considerations

### Resource Usage
- **Memory**: ~400MB for backend container
- **CPU**: Minimal (except during LLM analysis)
- **Disk**: ~2GB for Docker image

### Optimization Tips
1. Use `slim` Python base image (already done)
2. Multi-stage builds to reduce final image size
3. Health checks ensure container availability
4. Proper error handling prevents crashes

## Troubleshooting

### Build Fails
- Ensure `docker build` is run from project root
- Check that `backend/requirements.txt` exists
- Verify Python 3.11 compatibility

### Container Won't Start
```bash
# Check logs
docker logs <container_id>

# Verify port availability
lsof -i :5000
```

### CORS Issues
- Update `CORS_ORIGINS` environment variable
- Format: comma-separated list (no spaces)
- Example: `http://localhost:3000,http://example.com`

### LLM Analysis Fails
- Verify `OPENROUTER_API_KEY` is set
- Check OpenRouter API status
- System falls back to heuristic analysis

## Production Deployment

### Recommendations
1. Use Docker Compose for multi-container orchestration
2. Set `ENVIRONMENT=production` in backend
3. Use environment file (`.env`) instead of hardcoding values
4. Add reverse proxy (nginx) for URL routing
5. Enable SSL/TLS with valid certificates
6. Use managed secrets for API keys
7. Set up monitoring and logging

### Example .env File
```
API_PORT=5000
OPENROUTER_API_KEY=sk-or-v1-xxxxx
CORS_ORIGINS=https://yourdomain.com
ENVIRONMENT=production
```

## Maintenance

### Cleaning Up
```bash
# Remove unused images
docker image prune

# Remove stopped containers
docker container prune

# Full cleanup (be careful!)
docker system prune -a
```

### Updating the Image
```bash
docker build -t lexys-ai-backend:latest .
docker push lexys-ai-backend:latest  # if using registry
```

## Additional Resources

- [Python Docker Best Practices](https://docs.docker.com/language/python/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [OpenRouter API Docs](https://openrouter.io/docs)
- [Flask Deployment Guide](https://flask.palletsprojects.com/deployment/)
