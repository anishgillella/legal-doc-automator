# Production Deployment Guide

## Backend2 API Server

### Environment Variables

Set these environment variables for production:

```bash
# Required
API_PORT=5001
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend-domain.com

# Optional
VERBOSE_LOGGING=false  # Set to 'true' for detailed logging
OUTPUT_DIR=/tmp  # Directory for temporary filled documents
```

### Running in Production

#### Option 1: Using run.py
```bash
cd backend2
ENVIRONMENT=production API_PORT=5001 python run.py
```

#### Option 2: Using app.py directly
```bash
cd backend2
ENVIRONMENT=production API_PORT=5001 python app.py
```

#### Option 3: Using gunicorn (recommended for production)
```bash
pip install gunicorn
cd backend2
gunicorn -w 4 -b 0.0.0.0:5001 --timeout 120 app:app
```

### Frontend Configuration

The frontend is already configured to connect to the backend. Set the API URL:

```bash
# In frontend/.env.local or production environment
NEXT_PUBLIC_API_URL=http://localhost:5001  # Development
NEXT_PUBLIC_API_URL=https://your-backend-domain.com  # Production
```

### API Endpoints

- `GET /api/health` - Health check
- `POST /api/process` - Detect placeholders and analyze with LLM
- `POST /api/fill` - Fill placeholders and return filled document
- `POST /api/placeholders` - Get placeholders only (no LLM)
- `POST /api/validate` - Validate single field input
- `POST /api/validate-batch` - Validate multiple fields

### Production Checklist

- ✅ Debug prints removed or made conditional
- ✅ Error logging goes to stderr
- ✅ CORS configured via environment variables
- ✅ Output directory configurable
- ✅ Port configurable via environment variable
- ✅ File cleanup after processing
- ✅ Proper error handling
- ✅ Test script removed

### Security Notes

1. **CORS**: Configure `CORS_ORIGINS` to only allow your frontend domain
2. **File Size**: Max file size is 50MB (configurable in app.py)
3. **Temporary Files**: Files are cleaned up after processing
4. **Error Messages**: Generic error messages returned to clients (detailed errors in logs)

### Monitoring

- Health check endpoint: `GET /api/health`
- Check logs for errors (all errors go to stderr)
- Set `VERBOSE_LOGGING=true` for detailed operation logs

