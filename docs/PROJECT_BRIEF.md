# Resume Analyzer - Project Organization Brief

## Project Context
This is an AI-powered resume analysis system that matches resumes against job descriptions using local LLMs (Ollama). The project has grown organically and now includes both standard and advanced RAG (Retrieval-Augmented Generation) implementations.

## Current Git Status
- **Branch**: experimenting-rag
- **Main branch**: Not set
- **Status**: Multiple untracked files and modified files indicating active development

### Modified Files:
- `.claude/settings.local.json`
- `.gitignore`
- `backend/app/core/config.py`
- `backend/app/services/vector_store.py`
- `backend/requirements.txt`

### Untracked Files/Directories:
- `INSTALLATION_STATUS.md`
- `MIGRATION_GUIDE.md`
- `README_RAG.md`
- `backend/app/evaluation/` (entire directory)
- `backend/app/services/enhanced_analysis_service.py`
- `backend/app/services/hyde.py`
- `backend/app/services/knowledge_base.py`
- `backend/app/services/observability.py`
- `backend/app/services/reranker.py`
- `backend/app/services/retriever.py`
- `backend/app/services/semantic_chunker.py`
- `backend/evaluation_results/`
- `backend/quick_test.py`
- `backend/requirements_core.txt`
- `backend/scripts/`
- `backend/test_rag.py`
- `nul` (likely an error file)

## Architecture Overview

### Tech Stack

**Backend:**
- FastAPI 0.104.1 + Uvicorn 0.24.0
- ChromaDB 0.4.18 (vector database)
- sentence-transformers 2.7.0 (embeddings)
- LangChain 0.1.0 + Ollama 0.1.6
- pdfplumber 0.10.3 + python-docx 1.1.0
- spaCy 3.7.2
- rank-bm25 0.2.2
- ragas 0.1.5 (optional)
- arize-phoenix 3.0.0 (optional)

**Frontend:**
- Next.js 14 + TypeScript 5.3.3
- React 18.2.0 + Tailwind CSS 3.4.0
- Axios 1.6.2 + ollama 0.6.3

### Application Workflows

#### 1. Standard Workflow
```
User Upload (PDF + Job Description)
  → Backend: PDF extraction
  → Backend: Vector similarity search
  → Backend: LLM analysis (Ollama)
  → Results returned to frontend
```

#### 2. Hybrid Workflow (Recommended)
```
User Upload
  → Backend: PDF extraction + vector search only
  → Frontend: LLM analysis using user's local Ollama
  → Zero API costs + Complete privacy
```

#### 3. Enhanced RAG Workflow
```
Upload
  → Semantic Chunking (section-aware)
  → Vector Storage
  → Query + HyDE Expansion (generate hypothetical docs)
  → Bi-Encoder Retrieval (top 30)
  → Cross-Encoder Re-ranking (top 10)
  → LLM Analysis
  → Optional: Evaluation (LLM-as-Judge, Ragas, Phoenix)
```

## Core Features

### User-Facing Features:
1. **Resume Analysis Dashboard** - Overall score, skills breakdown, ATS score
2. **Skills Analysis** - Matched/missing/transferable skills
3. **Improvement Suggestions** - Section-specific, prioritized recommendations
4. **Requirement Comparison** - Job requirements vs resume evidence
5. **Similar Resume Search** - Vector similarity search

### Advanced RAG Features:
6. **Semantic Chunking** - Intelligent resume parsing by sections
7. **HyDE** - Hypothetical document embeddings for better retrieval
8. **Cross-Encoder Re-ranking** - Hybrid scoring for accuracy
9. **Evaluation Framework** - LLM-as-Judge, Ragas metrics, Phoenix tracing
10. **Knowledge Base Management** - Multi-format batch ingestion

## Directory Structure

```
Resume_Analyzer/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Configuration
│   │   ├── models/       # Data models
│   │   ├── services/     # Business logic
│   │   │   ├── analysis_service.py
│   │   │   ├── enhanced_analysis_service.py (untracked)
│   │   │   ├── llm_service.py
│   │   │   ├── vector_store.py (modified)
│   │   │   ├── pdf_parser.py
│   │   │   ├── semantic_chunker.py (untracked)
│   │   │   ├── hyde.py (untracked)
│   │   │   ├── retriever.py (untracked)
│   │   │   ├── reranker.py (untracked)
│   │   │   ├── knowledge_base.py (untracked)
│   │   │   └── observability.py (untracked)
│   │   └── evaluation/   # Evaluation framework (untracked)
│   │       ├── llm_judge.py
│   │       └── ragas_eval.py
│   ├── scripts/          # Utility scripts (untracked)
│   ├── evaluation_results/ # Evaluation outputs (untracked)
│   ├── requirements.txt  # Main dependencies (modified)
│   ├── requirements_core.txt (untracked)
│   ├── test_rag.py (untracked)
│   └── quick_test.py (untracked)
├── frontend/
│   ├── app/              # Next.js App Router
│   ├── components/       # React components
│   │   ├── FileUpload.tsx
│   │   ├── MatchAnalysis.tsx
│   │   ├── ImprovementSuggestions.tsx
│   │   └── ComparisonView.tsx
│   └── lib/              # Utilities
│       ├── api.ts
│       └── ollama.ts
├── .claude/
│   └── settings.local.json (modified)
├── .gitignore (modified)
├── README.md
├── README_RAG.md (untracked)
├── INSTALLATION_STATUS.md (untracked)
├── MIGRATION_GUIDE.md (untracked)
└── nul (error file - untracked)
```

## Key Services and Their Roles

### Backend Services

| Service | File | Status | Purpose |
|---------|------|--------|---------|
| Analysis Service | `backend/app/services/analysis_service.py` | Tracked | Standard analysis pipeline |
| Enhanced Analysis | `backend/app/services/enhanced_analysis_service.py` | Untracked | Advanced RAG pipeline |
| LLM Service | `backend/app/services/llm_service.py` | Tracked | LLM integration & prompting |
| Vector Store | `backend/app/services/vector_store.py` | Modified | ChromaDB management |
| PDF Parser | `backend/app/services/pdf_parser.py` | Tracked | PDF text extraction |
| Semantic Chunker | `backend/app/services/semantic_chunker.py` | Untracked | Section-aware chunking |
| HyDE | `backend/app/services/hyde.py` | Untracked | Query expansion |
| Retriever | `backend/app/services/retriever.py` | Untracked | Advanced retrieval |
| Re-ranker | `backend/app/services/reranker.py` | Untracked | Cross-encoder re-ranking |
| Knowledge Base | `backend/app/services/knowledge_base.py` | Untracked | Multi-format ingestion |
| Observability | `backend/app/services/observability.py` | Untracked | Phoenix tracing |

### Evaluation Services

| Service | File | Status | Purpose |
|---------|------|--------|---------|
| LLM Judge | `backend/app/evaluation/llm_judge.py` | Untracked | LLM-as-judge evaluation |
| Ragas Eval | `backend/app/evaluation/ragas_eval.py` | Untracked | Ragas metrics |

### Frontend Components

| Component | Purpose |
|-----------|---------|
| FileUpload.tsx | Drag-and-drop upload, Ollama connection check |
| MatchAnalysis.tsx | Score visualization, skills breakdown |
| ImprovementSuggestions.tsx | Prioritized recommendations |
| ComparisonView.tsx | Requirement-by-requirement comparison |

## Configuration

### Backend Config (`backend/app/core/config.py` - modified)
- Ollama settings (base URL, model selection)
- File handling (upload dir, max size)
- CORS origins
- Embedding models (sentence-transformers, cross-encoder)
- RAG settings (retrieval_top_k, rerank_top_k, use_hyde, use_reranking)
- HyDE settings (num_documents, strategy, temperature)
- Scoring weights (retrieval vs rerank)
- ChromaDB HNSW parameters
- Evaluation toggles (tracing, ragas)
- Chunking settings

### Frontend Config
- API URL: `http://localhost:8000/api`
- Ollama URL: `http://localhost:11434`

## Current Issues and Observations

### 1. Git Status Concerns
- **Main branch not set**: Need to establish main/master branch
- **Many untracked files**: Enhanced RAG features not committed
- **Branch name**: "experimenting-rag" suggests experimental work
- **Error file**: `nul` file should be investigated and removed

### 2. Documentation Proliferation
- Multiple README files: `README.md`, `README_RAG.md`
- Installation docs: `INSTALLATION_STATUS.md`
- Migration docs: `MIGRATION_GUIDE.md`
- Potential for confusion or outdated information

### 3. Dependency Management
- Two requirements files: `requirements.txt`, `requirements_core.txt`
- Purpose of split unclear
- `requirements.txt` modified but not committed

### 4. Code Organization
- Services directory growing large (10+ files)
- Unclear separation between standard and enhanced features
- Test files in root backend directory (`test_rag.py`, `quick_test.py`)

### 5. Feature Maturity
- Standard vs Enhanced RAG: Which is production-ready?
- Evaluation framework: Optional but many untracked files
- Observability: Arize Phoenix integration incomplete?

### 6. Frontend-Backend Integration
- Two modes (standard and hybrid): Which should be default?
- API endpoints: `/upload` vs `/process-resume`
- Client-side vs server-side LLM: Configuration management?

## Data Flow

### API Endpoints

#### `/api/upload` (Standard Mode)
```
Request: FormData {resume: File, job_description: string, job_title?: string}
Response: {status, result: {match_analysis, improvements, comparisons, similar_resumes}}
```

#### `/api/process-resume` (Hybrid Mode)
```
Request: Same as /upload
Response: {status, resume_text, job_description, similar_resumes}
```

### Database

#### ChromaDB Collection: "resumes"
- Documents: Full resume text OR semantic chunks
- Embeddings: 384-dim vectors (all-MiniLM-L6-v2)
- Metadata: source_type, resume_id, chunk_type, job_title, etc.

#### SQLite (LLM Judge)
- Table: evaluations
- Stores: relevance_score, coverage_score, quality_score, overall_score

## Performance Characteristics

- **Standard mode**: 1-2 seconds
- **Enhanced (no HyDE)**: 2-3 seconds
- **Enhanced (full pipeline)**: 5-8 seconds
- **Resource usage**: Enhanced uses ~30% more CPU, ~20% more memory

## Questions for Organization

1. **Version Control Strategy**
   - Should we merge experimenting-rag into main?
   - Which features should be committed?
   - How to handle the untracked files?

2. **Documentation Strategy**
   - Should we consolidate multiple README files?
   - Where should migration guides live?
   - How to maintain installation docs?

3. **Code Structure**
   - Should we split services into standard/ and enhanced/ subdirectories?
   - Where should test files live?
   - How to organize evaluation code?

4. **Dependency Management**
   - Why two requirements files?
   - Should we use requirements.txt + requirements-dev.txt pattern?
   - How to handle optional dependencies (ragas, phoenix)?

5. **Feature Roadmap**
   - Which workflow should be the default?
   - Should evaluation be core or optional?
   - Production readiness of enhanced RAG?

6. **Configuration Management**
   - Should RAG features be configurable via env vars?
   - How to toggle between standard and enhanced modes?
   - Production vs development configurations?

7. **Testing Strategy**
   - Where should test files be organized?
   - Need for test/ directory structure?
   - Integration vs unit tests?

8. **Deployment**
   - Which deployment mode is recommended?
   - Docker setup needed?
   - Environment-specific configurations?

## Desired Outcomes

1. **Clean Git Status**: All relevant files tracked, branch strategy clear
2. **Clear Documentation**: Consolidated, up-to-date, user and developer focused
3. **Organized Code Structure**: Logical separation of concerns, easy navigation
4. **Dependency Clarity**: Clear separation of core vs optional dependencies
5. **Configuration Management**: Environment-based config, feature toggles
6. **Test Infrastructure**: Proper test organization and coverage
7. **Production Readiness**: Clear path from development to production

## Additional Context

- This project supports a unique hybrid architecture where the backend is hosted but LLM inference runs on the user's local machine (via Ollama)
- The enhanced RAG features represent significant improvements but are currently experimental
- The codebase appears to be in transition from a simple prototype to a production-ready system
- There are multiple audiences: end users (using the app), developers (contributing), and potentially enterprise customers

---

## Request for Claude

Please analyze this project brief and provide:

1. **Recommended project structure**: File organization, directory layout
2. **Git strategy**: What to commit, branch organization, .gitignore updates
3. **Documentation strategy**: How to consolidate and organize docs
4. **Code organization**: Service organization, test structure, configuration management
5. **Dependency management**: How to handle requirements files
6. **Configuration strategy**: Environment variables, feature flags, mode selection
7. **Actionable tasks**: Prioritized list of organizational improvements

Focus on practical, implementable solutions that will make this project more maintainable, scalable, and production-ready.
