# Lexsy Document AI - Full Stack Setup Guide

This guide will help you set up and run both the backend and frontend together.

## Prerequisites

- Python 3.8+ (for backend)
- Node.js 18+ (for frontend)
- OpenRouter API key (for LLM analysis)

## Backend Setup (backend2)

1. **Navigate to backend directory**:
   ```bash
   cd backend2
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the `backend2` directory:
   ```bash
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   API_PORT=5001
   ENVIRONMENT=development
   CORS_ORIGINS=http://localhost:3000
   ```

4. **Start the backend server**:
   ```bash
   python run.py
   ```
   
   Or directly:
   ```bash
   python app.py
   ```
   
   The server will start on `http://localhost:5001`

## Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables** (optional):
   Create a `.env.local` file in the `frontend` directory:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:5001
   ```
   
   If not set, it defaults to `http://localhost:5001`

4. **Start the development server**:
   ```bash
   npm run dev
   ```
   
   The frontend will start on `http://localhost:3000`

## Verify Connection

1. **Check backend health**:
   Open `http://localhost:5001/api/health` in your browser. You should see:
   ```json
   {
     "status": "healthy",
     "version": "2.0.0",
     "service": "Lexsy Document AI Backend2 (python-docx)"
   }
   ```

2. **Check frontend**:
   Open `http://localhost:3000` in your browser. The frontend should automatically check backend health on load.

## API Endpoints

### Backend Endpoints

- `GET /api/health` - Health check
- `POST /api/process` - Upload and process document (detects placeholders + LLM analysis)
- `POST /api/placeholders` - Get placeholders only (no LLM analysis)
- `POST /api/fill` - Fill placeholders in document
- `POST /api/validate` - Validate single field input
- `POST /api/validate-batch` - Validate multiple fields in batch

### Frontend Pages

- `/` - Home page with file upload
- `/form` - Form page to fill placeholders
- `/review` - Review and download filled document

## End-to-End Flow

1. **Upload Document**: User uploads a `.docx` file on the home page
2. **Process**: Backend detects placeholders and analyzes with LLM
3. **Form**: Frontend displays form fields based on LLM analysis
4. **Fill**: User fills in the form fields
5. **Validate**: Frontend validates inputs (optional)
6. **Review**: User reviews filled values
7. **Download**: Backend fills document and returns filled `.docx` file

## Troubleshooting

### Backend not starting
- Check Python version: `python --version` (should be 3.8+)
- Check if port 5001 is available: `lsof -i :5001`
- Check `.env` file exists and has `OPENROUTER_API_KEY`
- **Note**: Port 5000 is often used by AirPlay Receiver on macOS. We use port 5001 to avoid conflicts.

### Frontend can't connect to backend
- Verify backend is running on port 5001
- Check CORS settings in `backend2/app.py`
- Verify `NEXT_PUBLIC_API_URL` in frontend `.env.local` matches backend URL

### LLM analysis failing
- Verify `OPENROUTER_API_KEY` is set correctly
- Check OpenRouter API status
- Backend will fallback to basic analysis if LLM fails

### Document not filling correctly
- Check browser console for errors
- Verify placeholder text matches exactly (case-sensitive)
- Check backend logs for fill operation details

## Development Tips

1. **Backend logs**: Check terminal where backend is running for detailed logs
2. **Frontend logs**: Check browser console (F12) for frontend errors
3. **API testing**: Use Postman or curl to test backend endpoints directly
4. **Hot reload**: Both frontend and backend support hot reload during development

## Production Deployment

For production:
1. Set `ENVIRONMENT=production` in backend `.env`
2. Set `NEXT_PUBLIC_API_URL` to production backend URL
3. Build frontend: `npm run build`
4. Start frontend: `npm start`
5. Use a process manager (PM2, systemd) for backend

