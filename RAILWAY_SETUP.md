# Railway Deployment Guide - Lexsy AI Backend

## ✅ What's Been Set Up

Your backend is now **production-ready** with:
- ✅ **Dockerfile** - Multi-stage build optimized for production
- ✅ **wsgi.py** - Proper WSGI entry point for gunicorn
- ✅ **Absolute imports** - All Python files use absolute imports for gunicorn compatibility
- ✅ **railway.json** - Railway platform configuration
- ✅ **.env files properly ignored** - Your API keys are safe

## 🚀 Railway Deployment Steps

### Step 1: Commit Your Changes
```bash
cd "/Users/anishgillella/Desktop/Stuff/Projects/Lexys AI"
git add -A
git commit -m "Production-ready Docker setup for Railway deployment"
git push origin main
```

### Step 2: Connect to Railway
1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your repo: `Lexys-AI` (or your repo name)

### Step 3: Configure Environment Variables in Railway
In the Railway dashboard:
1. Go to your project
2. Click on the service
3. Go to **Variables** tab
4. The `railway.json` will auto-populate some values, but you need to verify:
   - `ENVIRONMENT` = `production`
   - `OPENROUTER_API_KEY` = Already set from `railway.json`
   - `CORS_ORIGINS` = `http://localhost:3000` (update after Vercel deployment)

### Step 4: Railway Will Automatically Deploy
- Railway detects the `Dockerfile`
- Builds the image automatically
- Deploys with gunicorn
- Assigns a public URL like: `https://your-project.up.railway.app`

### Step 5: Test Your Deployed Backend
```bash
curl https://your-project.up.railway.app/api/health
# Response: {"status":"healthy","version":"1.0.0","service":"Lexsy Document AI Backend"}
```

### Step 6: After Vercel Frontend Deployment
Once your frontend is deployed on Vercel:
1. Get your Vercel frontend URL
2. Update `CORS_ORIGINS` in Railway variables
3. Example: `CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000`

## 🔒 Security Notes

- **API Keys are NOT committed** - `.env` and `.env.railway` are in `.gitignore`
- **Production Key is in railway.json** - Only for Railway to read, not committed to git
- **Before going live**, remove the API key from `railway.json` and set it only in Railway dashboard:
  1. Go to Railway dashboard
  2. Select your project
  3. Go to **Variables**
  4. Add `OPENROUTER_API_KEY` manually (don't commit to code!)

## 📊 Monitoring

After deployment, you can monitor your backend:
1. Go to Railway dashboard
2. View logs in real-time
3. Check deployment status
4. Scale workers if needed (in `Dockerfile`)

## 🧪 Local Testing (Already Done!)

Your Docker image was tested locally on port 8003 and working:
```bash
docker run -p 8003:5000 --env-file .env lexys-ai-backend:latest
curl http://localhost:8003/api/health
# Response: {"status":"healthy","version":"1.0.0","service":"Lexsy Document AI Backend"}
```

## 📱 Frontend Configuration

Update your frontend to use the Railway backend URL:

**In `frontend/services/api.ts` or similar:**
```typescript
// Production
const API_URL = process.env.REACT_APP_API_URL || 'https://your-railway-url.up.railway.app';

// Local development
if (process.env.NODE_ENV === 'development') {
    API_URL = 'http://localhost:8003'; // or your test port
}
```

## ❓ Troubleshooting

### 502 Bad Gateway
- Check logs in Railway dashboard
- Ensure `OPENROUTER_API_KEY` is set
- Verify `.env` variables are correct

### Import Errors
- All imports in backend are now absolute (not relative)
- If you add new imports, use: `from module_name import X` (not `from .module_name import X`)

### Port Issues
- Railway automatically assigns a port to `$PORT` variable
- Dockerfile uses `0.0.0.0:5000` internally
- Railway maps this to the public URL automatically

## 🎯 Next Steps

1. ✅ Backend Docker: **DONE** (tested and working)
2. 📋 Next: Deploy frontend to Vercel
3. 🔗 Then: Update CORS_ORIGINS with Vercel URL
4. ✨ Finally: Test end-to-end integration

---

**Questions?** Check Railway docs: https://docs.railway.app
