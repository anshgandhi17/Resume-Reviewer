# Resume Analyzer - AI-Powered Job Matching System

An intelligent resume analysis application that uses AI to match resumes against job descriptions, providing actionable insights and improvement suggestions.

## Features

- **Match Analysis Dashboard**: Overall compatibility score, skills breakdown, and ATS-friendliness score
- **Skills Analysis**: Identifies matched, missing, and transferable skills
- **Improvement Suggestions**: Specific, prioritized recommendations to enhance your resume
- **Requirement Comparison**: Side-by-side comparison of job requirements vs. resume content
- **Similar Resume Search**: Finds similar successful resumes using vector similarity
- **Instant Results**: Direct synchronous processing for immediate feedback
- **Modern UI**: Beautiful, responsive interface built with Next.js and Tailwind CSS
- **🆕 Hybrid Architecture**: Frontend and backend can be hosted while users run Ollama locally for zero API costs

## Architecture Options

This application supports two deployment modes:

### Option 1: Fully Local (Traditional)
Run everything on your machine - ideal for development and complete privacy.
- Frontend: localhost:3000
- Backend: localhost:8000
- Ollama: localhost:11434

### Option 2: Hybrid Hosted (🆕 Recommended for Production)
Host the frontend and backend while users run Ollama locally - best for sharing with others.
- Frontend: Hosted (Vercel/Netlify) - accessible to anyone
- Backend: Hosted (AWS/GCP/Azure) - handles PDF processing and vector database
- Ollama: User's local machine - zero API costs, complete privacy

**How it works:**
1. User opens hosted frontend in browser
2. Frontend checks if user has Ollama running locally
3. User uploads resume → sent to hosted backend
4. Backend extracts PDF text and searches vector database
5. Frontend receives parsed data and calls user's local Ollama for AI analysis
6. Results displayed immediately

## Tech Stack

### Backend
- **FastAPI**: High-performance Python web framework
- **LangChain**: RAG framework for LLM orchestration (optional for hosted mode)
- **ChromaDB**: Vector database for embeddings
- **Sentence Transformers**: Text embeddings
- **pdfplumber**: PDF text extraction
- **spaCy**: NLP processing

### Frontend
- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Ollama.js**: Browser-based Ollama client
- **Axios**: HTTP client

### LLM
- **Ollama**: Local LLM (free, no API costs, complete privacy)

## Prerequisites

Before running this application, ensure you have the following installed:

1. **Python 3.9+**
2. **Node.js 18+** and npm
3. **Ollama** (for local LLM)

### Installing Prerequisites

#### Windows

1. **Python**: Download from [python.org](https://www.python.org/downloads/)
2. **Node.js**: Download from [nodejs.org](https://nodejs.org/)
3. **Ollama**:
   - Download from [ollama.ai](https://ollama.ai/)
   - After installation, pull a model: `ollama pull llama2`

#### macOS

```bash
# Using Homebrew
brew install python node ollama

# Pull Ollama model
ollama pull llama2
```

#### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip nodejs npm

# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull Ollama model
ollama pull llama2
```

## Installation

### 1. Clone the Repository

```bash
cd Resume_Analyzer
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Create .env file
cp .env.example .env

# Edit .env if needed (defaults should work for local development)
```

### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Environment is pre-configured in .env.local
```

## Running the Application

### Mode 1: Fully Local Development

You need to run 3 services:

#### 1. Start Ollama

```bash
# Ollama should be running as a service after installation
# Verify it's running:
ollama list

# If not running, start it:
ollama serve

# Ensure you have a model downloaded:
ollama pull llama2
```

#### 2. Start Backend API

```bash
cd backend

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. Start Frontend

Open a new terminal:

```bash
cd frontend

# Start Next.js development server
npm run dev
```

#### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

### Mode 2: Using Hosted Frontend/Backend with Local Ollama

If the application is hosted, you only need to run Ollama locally:

#### 1. Start Ollama Locally

```bash
# Verify Ollama is running:
ollama list

# If not running, start it:
ollama serve

# Ensure you have a model downloaded:
ollama pull llama2
```

#### 2. Open the Hosted Frontend

Visit the hosted URL (e.g., https://your-app.vercel.app)

The frontend will automatically:
- Detect your local Ollama instance at localhost:11434
- Show connection status (green = connected, yellow = disconnected)
- Process your resume on the hosted backend
- Run AI analysis on your local Ollama (keeping your data private)

**Note:** The browser must allow connections to localhost:11434. Most modern browsers support this by default.

## Usage

1. Open http://localhost:3000 in your browser
2. Upload your resume (PDF format)
3. Paste the job description
4. Optionally enter the job title
5. Click "Analyze Resume"
6. Results appear immediately after processing (typically 30-60 seconds on first run)
7. Review results:
   - Overall match score and ATS score
   - Skills breakdown (matched/missing)
   - Improvement suggestions
   - Requirement comparison
   - Similar successful resumes

## Configuration

### Backend (.env)

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2  # or llama3, mistral, etc.

# Application Settings
UPLOAD_DIR=./uploads
VECTOR_DB_DIR=./vectordb
MAX_FILE_SIZE=10485760  # 10MB
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## Troubleshooting

### Ollama Connection Error
- Verify Ollama is running: `ollama list`
- Check if model is downloaded: `ollama pull llama2`
- Verify OLLAMA_BASE_URL in backend/.env

### PDF Upload Fails
- Check file size (max 10MB by default)
- Ensure file is a valid PDF
- Check backend logs for detailed error

### Frontend Can't Connect to Backend
- Verify backend is running on port 8000
- Check CORS settings in backend/app/core/config.py
- Clear browser cache and restart frontend

### Analysis Takes Too Long
- First run downloads models and creates embeddings (slower)
- Subsequent analyses are faster
- Consider using a lighter/faster Ollama model

## Development

### Adding More LLM Models

You can use different Ollama models by changing the `OLLAMA_MODEL` in `.env`:

```bash
# Download a different model
ollama pull mistral
ollama pull llama3
ollama pull codellama

# Update .env
OLLAMA_MODEL=mistral
```

### Customizing Skill Extraction

Edit `backend/app/services/llm_service.py` to add more skills to the `common_tech_skills` list or implement custom NER with spaCy.

### Modifying UI Theme

Edit `frontend/tailwind.config.ts` to customize colors and styling.

## Architecture

The application uses a simplified synchronous architecture:

1. **Frontend** sends resume + job description to backend
2. **Backend** processes the request directly:
   - Extracts text from PDF
   - Generates embeddings and searches vector store
   - Calls Ollama LLM for analysis
   - Returns complete results
3. **Frontend** displays results immediately

This approach is simpler and easier to maintain than async task queues, while still providing good performance for typical resume analysis workloads.

## Production Deployment

### Hybrid Deployment (Hosted Frontend/Backend + User's Local Ollama)

This is the recommended approach for production use.

#### Deploy Frontend (Vercel)

```bash
cd frontend

# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod

# Set environment variable:
# NEXT_PUBLIC_API_URL=https://your-backend-url.com/api
```

#### Deploy Backend (Example: AWS/Docker)

```bash
cd backend

# Update backend/.env for production:
# - Set CORS origins to include your frontend URL
# - Configure production database paths

# Using Docker:
docker build -t resume-analyzer-backend .
docker run -p 8000:8000 resume-analyzer-backend

# Or deploy to AWS/GCP/Azure using their deployment tools
```

#### User Setup

Users only need to:
1. Install Ollama: https://ollama.ai/download
2. Run `ollama pull llama2`
3. Keep Ollama running (`ollama serve`)
4. Visit your hosted frontend URL

**Benefits:**
- ✅ Zero LLM API costs
- ✅ Complete privacy (AI processing happens on user's machine)
- ✅ Shared vector database for better recommendations
- ✅ No need to distribute your entire codebase

---

### Traditional Deployment (All Services Hosted)

If you prefer to run Ollama on the server:

1. Deploy backend with Ollama installed on the same machine
2. Use the `/upload` endpoint instead of `/process-resume`
3. Consider using cloud-hosted Ollama or switch to OpenAI/Anthropic APIs
4. Use a production vector database like Pinecone or Weaviate
5. Set up proper environment variables
6. Use a process manager like PM2 or systemd
7. Add authentication and rate limiting
8. Set up monitoring and logging

**Trade-offs:**
- ❌ Higher infrastructure costs (GPU/CPU for LLM)
- ❌ Privacy concerns (resumes processed on your server)
- ✅ Simpler user experience (no local Ollama needed)
- ✅ More control over LLM version/model

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
