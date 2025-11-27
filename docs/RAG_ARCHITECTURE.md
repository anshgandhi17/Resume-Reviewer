# Resume Analyzer - Advanced RAG Implementation

## Overview

This document describes the enhanced RAG (Retrieval-Augmented Generation) implementation for the Resume/Job Description Matcher. The system has been upgraded with state-of-the-art retrieval and evaluation techniques.

## What's New

### 1. Semantic Chunking
- **Previous**: Fixed-size character chunks
- **Now**: Intelligent semantic boundaries (job experiences, projects, skills, education)
- **Benefits**: Better context preservation, more relevant retrieval

### 2. HyDE (Hypothetical Document Embeddings)
- Generates hypothetical "perfect match" resume bullets for a given job description
- Uses these hypothetical documents to improve retrieval quality
- Configurable strategies: `bullets` or `experiences`

### 3. Cross-Encoder Re-ranking
- Initial retrieval with fast bi-encoder (sentence-transformers)
- Re-ranks top candidates with more accurate cross-encoder
- Hybrid scoring combines both retrieval and re-ranking scores

### 4. Evaluation Framework
- **Ragas**: Automated metrics for context relevance, faithfulness, and answer relevancy
- **LLM-as-Judge**: Uses local Ollama LLM to evaluate retrieval quality, coverage, and output quality
- **Arize Phoenix**: Optional tracing and observability

---

## Architecture

### RAG Pipeline Flow

```
1. Resume Ingestion
   ↓
2. Semantic Chunking
   ↓
3. Vector Storage (ChromaDB)
   ↓
4. Job Description Query
   ↓
5. HyDE Query Expansion (optional)
   ↓
6. Bi-Encoder Retrieval (top 30)
   ↓
7. Cross-Encoder Re-ranking (top 10)
   ↓
8. LLM Generation
   ↓
9. Evaluation (optional)
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Semantic Chunker | `app/services/semantic_chunker.py` | Chunks resumes by semantic boundaries |
| Knowledge Base | `app/services/knowledge_base.py` | Ingests various document types |
| HyDE Service | `app/services/hyde.py` | Generates hypothetical documents |
| Advanced Retriever | `app/services/retriever.py` | Orchestrates retrieval with HyDE |
| Re-Ranker | `app/services/reranker.py` | Cross-encoder re-ranking |
| Observability | `app/services/observability.py` | Tracing with Arize Phoenix |
| Ragas Evaluator | `app/evaluation/ragas_eval.py` | Automated RAG metrics |
| LLM Judge | `app/evaluation/llm_judge.py` | LLM-based evaluation |
| Enhanced Service | `app/services/enhanced_analysis_service.py` | Main pipeline orchestrator |

---

## Installation

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Download Models

The system will automatically download required models on first use:
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Cross-encoder: `cross-encoder/ms-marco-MiniLM-L-6-v2`

### 3. Start Ollama (for LLM features)

```bash
# Install Ollama: https://ollama.ai
ollama pull llama2
# or
ollama pull mistral
```

### 4. Optional: Enable Arize Phoenix

```bash
# Phoenix will auto-launch if enabled
# Access UI at http://localhost:6006
```

---

## Configuration

All settings are in `app/core/config.py`. Key parameters:

### RAG Settings

```python
# Retrieval
retrieval_top_k: int = 30          # Initial retrieval count
rerank_top_k: int = 10             # Final count after re-ranking
use_hyde: bool = True              # Enable HyDE
use_reranking: bool = True         # Enable cross-encoder

# HyDE
hyde_num_documents: int = 5        # Number of hypothetical docs
hyde_strategy: str = "bullets"     # 'bullets' or 'experiences'
hyde_temperature: float = 0.7      # LLM temperature

# Scoring Weights
retrieval_score_weight: float = 0.3
rerank_score_weight: float = 0.7

# Evaluation
enable_tracing: bool = False       # Arize Phoenix tracing
enable_ragas: bool = False         # Ragas metrics

# Chunking
enable_semantic_chunking: bool = True
min_chunk_size: int = 100
max_chunk_size: int = 2000
```

### Environment Variables

Create `.env` file:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Optional: Override defaults
USE_HYDE=true
USE_RERANKING=true
RETRIEVAL_TOP_K=30
RERANK_TOP_K=10
```

---

## Usage

### Basic Analysis (Enhanced Pipeline)

```python
from app.services.enhanced_analysis_service import enhanced_service

# Analyze a resume
result = enhanced_service.analyze_resume_enhanced(
    resume_path="path/to/resume.pdf",
    job_description="Job description text...",
    job_title="Software Engineer",
    enable_evaluation=True  # Optional
)

# Result includes:
# - match_analysis: Scores and matched/missing skills
# - improvements: Suggested improvements
# - retrieved_chunks: Top relevant chunks
# - rag_metadata: Pipeline stats (duration, chunks, etc.)
# - evaluation: Optional evaluation scores
```

### Ingest Documents to Knowledge Base

```python
from app.services.enhanced_analysis_service import enhanced_service

# Ingest single resume
result = enhanced_service.ingest_resume_to_knowledge_base(
    resume_path="resume.pdf",
    metadata={"candidate_name": "John Doe"}
)

# Batch ingest directory
result = enhanced_service.batch_ingest_directory(
    directory_path="./resumes",
    document_type='resume'  # 'resume', 'project', 'star', or 'auto'
)
```

### Get Pipeline Stats

```python
stats = enhanced_service.get_pipeline_stats()
print(f"Vector store has {stats['vector_store_count']} documents")
print(f"HyDE enabled: {stats['hyde_enabled']}")
print(f"Re-ranking enabled: {stats['reranking_enabled']}")
```

---

## Evaluation

### LLM-as-Judge

```python
from app.evaluation.llm_judge import llm_judge

# Evaluate retrieval quality
evaluation = llm_judge.evaluate_complete_pipeline(
    job_description="JD text...",
    retrieved_chunks=["chunk1", "chunk2"],
    generated_content="Generated resume..."
)

# Results: relevance_score, coverage_score, quality_score (1-5)
print(f"Overall Score: {evaluation['overall_score']}/5")

# Get evaluation history
stats = llm_judge.get_evaluation_stats()
recent = llm_judge.get_recent_evaluations(limit=10)
```

### Ragas Evaluation

```python
from app.evaluation.ragas_eval import ragas_evaluator

# Prepare test cases
test_cases = [
    {
        'query': 'Job description...',
        'retrieved_contexts': ['chunk1', 'chunk2'],
        'generated_answer': 'Resume text...',
        'ground_truth_answer': 'Expected answer...'  # Optional
    }
]

# Run evaluation
result = ragas_evaluator.evaluate_full_pipeline(test_cases)

# Metrics: context_relevancy, context_precision, faithfulness, answer_relevancy
print(result['metrics'])
```

---

## Benchmarking

Compare different RAG configurations:

```bash
cd backend

# Quick benchmark with sample data
python scripts/benchmark.py --quick

# With custom test cases
python scripts/benchmark.py \
    --test-cases test_data/test_cases.json \
    --output results/benchmark_20240101.json
```

Test cases JSON format:

```json
[
    {
        "resume_path": "./resumes/resume1.pdf",
        "job_description": "Software Engineer role..."
    },
    {
        "resume_path": "./resumes/resume2.pdf",
        "job_description": "Data Scientist role..."
    }
]
```

Benchmark compares:
1. **Baseline**: No HyDE, no re-ranking
2. **HyDE Only**: HyDE enabled, no re-ranking
3. **Re-ranking Only**: No HyDE, re-ranking enabled
4. **Full Pipeline**: Both HyDE and re-ranking

Metrics:
- Average latency
- Retrieval quality scores
- Evaluation scores
- Success rates

---

## API Integration

### Option 1: Update Existing Endpoint

Modify `app/api/routes.py`:

```python
from app.services.enhanced_analysis_service import enhanced_service

@router.post("/upload-enhanced")
async def upload_resume_enhanced(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: Optional[str] = Form(None),
    enable_evaluation: bool = Form(False)
):
    # Save file
    file_path = save_uploaded_file(resume)

    # Use enhanced service
    result = enhanced_service.analyze_resume_enhanced(
        resume_path=str(file_path),
        job_description=job_description,
        job_title=job_title,
        enable_evaluation=enable_evaluation
    )

    return JSONResponse(result)
```

### Option 2: New Endpoint for Knowledge Base

```python
@router.post("/ingest")
async def ingest_document(
    document: UploadFile = File(...),
    doc_type: str = Form("resume"),  # resume, project, star
    metadata: Optional[str] = Form(None)
):
    file_path = save_uploaded_file(document)

    metadata_dict = json.loads(metadata) if metadata else {}

    result = enhanced_service.ingest_resume_to_knowledge_base(
        resume_path=str(file_path),
        metadata=metadata_dict
    )

    return JSONResponse(result)
```

---

## Performance Tuning

### Latency vs Quality Trade-offs

| Configuration | Latency | Quality | Use Case |
|---------------|---------|---------|----------|
| Baseline | Fastest | Good | High-volume, low-latency |
| HyDE Only | Medium | Better | Quality over speed |
| Re-ranking Only | Medium | Better | Balanced |
| Full Pipeline | Slowest | Best | Highest quality |

### Optimization Tips

1. **Reduce `retrieval_top_k`**: Fewer candidates = faster re-ranking
   ```python
   retrieval_top_k = 20  # Instead of 30
   rerank_top_k = 5      # Instead of 10
   ```

2. **Use smaller cross-encoder model**:
   ```python
   cross_encoder_model = "cross-encoder/ms-marco-TinyBERT-L-2-v2"
   ```

3. **Disable HyDE for real-time**:
   ```python
   use_hyde = False
   ```

4. **Batch processing**: Ingest resumes offline, only do retrieval online

5. **Cache embeddings**: Vector store automatically caches embeddings

---

## Troubleshooting

### Models Not Downloading

```bash
# Manually download models
python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

### Ollama Connection Issues

```bash
# Check Ollama is running
ollama list

# Test connection
curl http://localhost:11434/api/generate -d '{
  "model": "llama2",
  "prompt": "test"
}'
```

### ChromaDB Errors

```bash
# Clear vector database
rm -rf ./vectordb

# Recreate on next run
python -c "from app.services.vector_store import VectorStore; VectorStore()"
```

### Memory Issues

For large-scale deployments:

```python
# Reduce batch sizes
hyde_num_documents = 3  # Instead of 5
retrieval_top_k = 20    # Instead of 30

# Use quantized models (future enhancement)
```

---

## Advanced Features

### Custom Chunking Strategy

Extend `SemanticChunker`:

```python
from app.services.semantic_chunker import SemanticChunker

class MyCustomChunker(SemanticChunker):
    def chunk_resume(self, resume_text: str, resume_id: str = None):
        # Your custom chunking logic
        pass
```

### Custom HyDE Prompts

Modify `app/services/hyde.py`:

```python
CUSTOM_PROMPT = """Generate resume bullets for:
{job_description}

Focus on: {specific_skills}
"""
```

### Custom Evaluation Metrics

Add to `app/evaluation/llm_judge.py`:

```python
CUSTOM_METRIC_PROMPT = """Evaluate X on a scale of 1-5..."""

def evaluate_custom_metric(self, ...):
    # Your evaluation logic
    pass
```

---

## Monitoring & Observability

### Enable Arize Phoenix

```python
# In config.py
enable_tracing = True
phoenix_port = 6006
```

Access UI: `http://localhost:6006`

### View Traces

Phoenix shows:
- Embedding generation times
- Retrieval latencies
- Re-ranking times
- LLM call durations
- Full pipeline traces

### Custom Logging

```python
from app.services.observability import observability, TraceStep

with TraceStep("custom_operation", observability) as step:
    # Your code
    result = do_something()
    step.log_result({"metric": value})
```

---

## Evaluation Results Storage

### LLM Judge Results

Stored in SQLite: `./evaluation_results/llm_judge.db`

Query:

```sql
SELECT
    evaluation_type,
    AVG(relevance_score) as avg_relevance,
    AVG(coverage_score) as avg_coverage,
    AVG(quality_score) as avg_quality
FROM evaluations
GROUP BY evaluation_type;
```

### Ragas Results

JSON files in: `./evaluation_results/ragas_eval_*.json`

```python
from app.evaluation.ragas_eval import ragas_evaluator

# Load history
results = ragas_evaluator.load_results(evaluation_type='full_pipeline')

# Compare two runs
comparison = ragas_evaluator.compare_results(results[0], results[1])
```

---

## FAQ

**Q: Do I need to use all features?**
A: No! Features are modular. Start with semantic chunking, then add HyDE and re-ranking as needed.

**Q: What's the recommended configuration?**
A: For production: HyDE + Re-ranking. For development: Baseline for speed.

**Q: Can I use a different LLM?**
A: Yes! Update `ollama_model` in config. Supports any Ollama model.

**Q: How do I know if improvements are working?**
A: Run benchmarks with your test data. Compare metrics across configurations.

**Q: What if I don't have ground truth data?**
A: Use LLM-as-judge for automated evaluation without ground truth.

**Q: Can I use paid APIs like OpenAI?**
A: The code uses Ollama (free), but you can modify `HyDEService` and `LLMService` to use OpenAI SDK.

---

## Next Steps

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Test basic functionality**: Run with a sample resume
3. **Configure settings**: Adjust `config.py` for your use case
4. **Run benchmarks**: Compare configurations with your data
5. **Integrate with API**: Add enhanced endpoints
6. **Monitor performance**: Enable tracing and evaluation
7. **Iterate**: Use evaluation metrics to improve

---

## References

- **HyDE Paper**: [Precise Zero-Shot Dense Retrieval without Relevance Labels](https://arxiv.org/abs/2212.10496)
- **Ragas**: [RAG Assessment Framework](https://github.com/explodinggradients/ragas)
- **Arize Phoenix**: [LLM Observability](https://docs.arize.com/phoenix)
- **Cross-Encoders**: [Sentence-Transformers Documentation](https://www.sbert.net/examples/applications/cross-encoder/README.html)

---

## Support

For issues or questions:
1. Check troubleshooting section
2. Review evaluation metrics to diagnose problems
3. Consult code comments for implementation details
4. Use observability tools to trace pipeline execution

---

## License

MIT License - see LICENSE file for details
