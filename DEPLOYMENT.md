# Deployment Guide - Hybrid Architecture

This guide explains how to deploy the Resume Analyzer with a hybrid architecture where the frontend and backend are hosted, but users run Ollama locally on their machines.

## Architecture Overview

```
┌─────────────────┐      ┌─────────────────┐      ┌──────────────────┐
│  Hosted         │      │  Hosted         │      │  User's Machine  │
│  Frontend       │─────▶│  Backend        │      │                  │
│  (Vercel)       │      │  (AWS/GCP)      │      │  Ollama          │
│                 │◀─────│                 │      │  (localhost)     │
└─────────────────┘      └─────────────────┘      └──────────────────┘
         │                                                   ▲
         │                                                   │
         └───────────────────────────────────────────────────┘
                      Browser connects to both
```

**Flow:**
1. User opens hosted frontend in browser
2. Frontend checks if Ollama is running locally (localhost:11434)
3. User uploads resume → sent to hosted backend
4. Backend extracts PDF text, stores in vector DB, finds similar resumes
5. Backend returns parsed text to frontend
6. Frontend calls user's local Ollama for AI analysis
7. Results displayed to user

## Benefits

✅ **Zero API Costs**: No OpenAI/Anthropic charges
✅ **Privacy**: AI analysis happens on user's machine
✅ **Scalability**: Backend handles lightweight operations (PDF parsing, vector DB)
✅ **Shared Database**: All users benefit from shared vector database of resumes

## Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Docker (optional, for containerized deployment)
- Vercel account (or other hosting platform)
- Cloud provider account (AWS, GCP, Azure, etc.)

## Step 1: Deploy Frontend

### Option A: Vercel (Recommended)

1. **Prepare the frontend:**

```bash
cd frontend

# Ensure package.json has all dependencies
npm install

# Test production build locally
npm run build
npm start
```

2. **Deploy to Vercel:**

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

3. **Set Environment Variables in Vercel:**

Go to your Vercel project settings → Environment Variables:

```
NEXT_PUBLIC_API_URL=https://your-backend-url.com/api
```

### Option B: Netlify

1. **Create `netlify.toml` in frontend directory:**

```toml
[build]
  command = "npm run build"
  publish = ".next"

[[plugins]]
  package = "@netlify/plugin-nextjs"
```

2. **Deploy:**

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Login and deploy
netlify login
netlify deploy --prod
```

3. **Set environment variables in Netlify dashboard.**

### Option C: Static Export + Any Host

If using a simple static host:

```bash
# Update next.config.js to add:
# output: 'export'

npm run build

# Upload .next/static to your host
```

## Step 2: Deploy Backend

### Option A: Docker + Any Cloud Provider

1. **Create Dockerfile** (if not exists):

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application
COPY . .

# Create directories
RUN mkdir -p uploads vectordb

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Build and test locally:**

```bash
cd backend

docker build -t resume-analyzer-backend .
docker run -p 8000:8000 resume-analyzer-backend

# Test: http://localhost:8000/docs
```

3. **Deploy to cloud:**

**AWS (ECS/Fargate):**
```bash
# Push to ECR
aws ecr create-repository --repository-name resume-analyzer
aws ecr get-login-password | docker login --username AWS --password-stdin YOUR_ECR_URL
docker tag resume-analyzer-backend:latest YOUR_ECR_URL/resume-analyzer:latest
docker push YOUR_ECR_URL/resume-analyzer:latest

# Create ECS task and service (via AWS Console or CLI)
```

**GCP (Cloud Run):**
```bash
# Push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/resume-analyzer
gcloud run deploy resume-analyzer --image gcr.io/PROJECT_ID/resume-analyzer --platform managed --allow-unauthenticated
```

**Azure (Container Instances):**
```bash
# Push to Azure Container Registry
az acr create --resource-group myResourceGroup --name myContainerRegistry --sku Basic
az acr login --name myContainerRegistry
docker tag resume-analyzer-backend myContainerRegistry.azurecr.io/resume-analyzer
docker push myContainerRegistry.azurecr.io/resume-analyzer
az container create --resource-group myResourceGroup --name resume-analyzer --image myContainerRegistry.azurecr.io/resume-analyzer
```

### Option B: Traditional VM Deployment

1. **Set up a VM** (Ubuntu example):

```bash
# SSH into your VM
ssh user@your-vm-ip

# Install dependencies
sudo apt update
sudo apt install -y python3.9 python3-pip

# Clone or upload your code
git clone your-repo-url
cd Resume_Analyzer/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Create directories
mkdir -p uploads vectordb
```

2. **Create systemd service** (`/etc/systemd/system/resume-analyzer.service`):

```ini
[Unit]
Description=Resume Analyzer Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/Resume_Analyzer/backend
Environment="PATH=/path/to/Resume_Analyzer/backend/venv/bin"
ExecStart=/path/to/Resume_Analyzer/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

3. **Start service:**

```bash
sudo systemctl daemon-reload
sudo systemctl start resume-analyzer
sudo systemctl enable resume-analyzer
sudo systemctl status resume-analyzer
```

4. **Set up Nginx reverse proxy:**

```nginx
server {
    listen 80;
    server_name your-backend-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option C: Serverless (AWS Lambda + API Gateway)

This requires some code adjustments for Lambda compatibility:

```bash
# Install Mangum for AWS Lambda
pip install mangum

# Modify app/main.py to add:
from mangum import Mangum
handler = Mangum(app)

# Deploy using Serverless Framework or AWS SAM
```

## Step 3: Configure CORS

Update `backend/app/core/config.py` to allow your frontend URL:

```python
class Settings(BaseSettings):
    # ...existing settings...

    cors_origins: list = [
        "http://localhost:3000",
        "https://your-frontend-url.vercel.app",  # Add your production URL
    ]
```

Or use environment variables:

```bash
# Set in your deployment platform
CORS_ORIGINS=["https://your-frontend-url.vercel.app"]
```

## Step 4: Set Up Persistent Storage

For production, configure persistent storage for:

1. **Vector Database** (ChromaDB data)
2. **Uploaded PDFs** (temporary)

### Option A: Cloud Storage

```python
# backend/.env
VECTOR_DB_DIR=/persistent/storage/vectordb
UPLOAD_DIR=/persistent/storage/uploads
```

Mount cloud storage (EFS, Cloud Filestore, Azure Files) to these paths.

### Option B: Managed Vector Database

Consider migrating to a managed solution:

```python
# Replace ChromaDB with Pinecone/Weaviate
# Update backend/app/services/vector_store.py
```

## Step 5: Test the Deployment

1. **Visit your hosted frontend URL**
2. **You should see**: "Checking Ollama connection..."
3. **Start Ollama locally**: `ollama serve`
4. **Refresh the page**: Should show "Ollama connected - Ready to analyze"
5. **Upload a test resume** and verify the full flow works

## Step 6: User Instructions

Create a user guide for your hosted app:

---

### How to Use Resume Analyzer

**One-time Setup:**

1. Download and install Ollama: https://ollama.ai/download
2. Open terminal/command prompt and run:
   ```bash
   ollama pull llama2
   ```

**Every Time You Use the App:**

1. Start Ollama:
   ```bash
   ollama serve
   ```
   (Keep this running in the background)

2. Visit: https://your-app-url.com

3. You should see a green "Ollama connected" message

4. Upload your resume and job description!

---

## Troubleshooting

### Frontend can't connect to local Ollama

**Issue**: Yellow warning "Ollama Not Connected"

**Solutions**:
- Verify Ollama is running: `ollama list`
- Check browser allows localhost connections (most do by default)
- Try using Chrome/Firefox (best compatibility)
- Check firewall isn't blocking port 11434

### Backend CORS errors

**Issue**: Browser console shows CORS errors

**Solutions**:
- Add frontend URL to `cors_origins` in backend config
- Redeploy backend with updated CORS settings
- Verify backend is accessible from browser

### Slow analysis

**Issue**: Analysis takes very long

**Solutions**:
- User's machine specs matter (Ollama runs locally)
- Suggest lighter models: `ollama pull llama2:7b`
- Consider showing estimated time based on model

## Monitoring & Maintenance

### Backend Monitoring

Monitor these metrics:
- API response times
- PDF processing errors
- Vector DB size
- Storage usage

### Frontend Monitoring

Use Vercel Analytics or similar:
- Page load times
- Ollama connection success rate
- Analysis completion rate

## Cost Estimate

**Hybrid Architecture (Recommended):**
- Frontend (Vercel): $0-$20/month (free tier usually sufficient)
- Backend (AWS t3.small): $10-15/month
- Storage (S3/EBS): $5-10/month
- **Total: ~$15-45/month** (scales with usage)

**Traditional Architecture (Backend runs LLM):**
- Frontend: $0-$20/month
- Backend (GPU instance): $200-500/month
- Storage: $10-20/month
- **Total: ~$210-540/month**

## Security Considerations

1. **Rate Limiting**: Add rate limiting to prevent abuse
2. **File Validation**: Backend validates PDF files
3. **Size Limits**: Enforce max file size (10MB default)
4. **HTTPS**: Use HTTPS for all connections
5. **Environment Variables**: Never commit secrets
6. **Vector DB Access**: Restrict access to vector database

## Scaling

As usage grows:

1. **Backend**: Scale horizontally (add more instances)
2. **Vector DB**: Migrate to managed service (Pinecone, Weaviate)
3. **CDN**: Add CloudFlare for frontend caching
4. **Analytics**: Track usage patterns for optimization

## Support

For issues:
- Check logs in your deployment platform
- Test locally first
- Verify environment variables
- Check CORS configuration

---

Happy deploying! 🚀
