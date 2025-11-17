# Quick Start Guide

This guide will get you up and running in under 5 minutes.

## Prerequisites Check

Run these commands to verify prerequisites:

```bash
# Check Python
python --version  # Should be 3.9+

# Check Node.js
node --version    # Should be 18+

# Check Ollama
ollama list       # Should list available models
```

If any are missing, see the main README for installation instructions.

## Step 1: Install Dependencies

### Backend
```bash
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Frontend
```bash
cd frontend
npm install
```

## Step 2: Pull Ollama Model

```bash
ollama pull llama2
```

This will download the Llama 2 model (about 3.8GB). You only need to do this once.

## Step 3: Start Services

Open 2 separate terminals:

### Terminal 1: Backend API
```bash
cd backend
# Activate venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```

## Step 4: Use the Application

1. Open http://localhost:3000
2. Upload a resume PDF
3. Paste a job description
4. Click "Analyze Resume"
5. Wait for the analysis to complete (results appear immediately)

## Verification

After starting both services, verify they're running:

- Frontend: http://localhost:3000 (should show upload page)
- Backend API: http://localhost:8000/docs (should show API documentation)
- Health Check: http://localhost:8000/api/health (should return healthy status)

## Common Issues

**"Connection refused" errors:**
- Make sure Ollama is running: `ollama serve`
- Check if the backend is running on port 8000

**Analysis fails:**
- First run downloads models and creates embeddings (slower)
- Check Ollama is running: `ollama list`
- Verify the model is downloaded: `ollama pull llama2`

**Frontend can't connect to backend:**
- Ensure backend is running on http://localhost:8000
- Check browser console for CORS errors

## Next Steps

- Read the full README for configuration options
- Try different Ollama models for better results
- Customize the skill extraction in the backend
- Adjust the UI theme in Tailwind config

## Need Help?

Check the Troubleshooting section in the main README.md
