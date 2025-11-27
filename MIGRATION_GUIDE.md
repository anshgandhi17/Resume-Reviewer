# Migration Guide: Standard → Enhanced RAG

This guide helps you transition from the standard Resume Analyzer to the enhanced RAG implementation.

## Quick Start

### 1. Install New Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `python-docx` (for DOCX support)
- `rank-bm25` (for BM25 search)
- `ragas` (for evaluation)
- `arize-phoenix` (for observability)

### 2. Keep Using Standard Version (No Changes Required)

Your existing code continues to work! The original services remain unchanged:
- `app/services/analysis_service.py` - Original service
- `app/services/vector_store.py` - Enhanced with backward compatibility
- `app/api/routes.py` - Original endpoints still work

### 3. Test Enhanced Version

```python
# Option A: Python Script
from app.services.enhanced_analysis_service import enhanced_service

result = enhanced_service.analyze_resume_enhanced(
    resume_path="resume.pdf",
    job_description="job description...",
    enable_evaluation=False  # Start without evaluation
)

print(f"Match Score: {result['match_analysis']['overall_score']}")
print(f"Pipeline Duration: {result['rag_metadata']['total_duration']:.2f}s")
```

```bash
# Option B: Test with curl
curl -X POST "http://localhost:8000/api/upload-enhanced" \
  -F "resume=@resume.pdf" \
  -F "job_description=Software Engineer with Python..."
```

---

## Migration Strategies

### Strategy 1: Parallel Deployment (Recommended)

Keep both systems running and gradually migrate users.

**Step 1**: Add new endpoint to `routes.py`

```python
from app.services.enhanced_analysis_service import enhanced_service

@router.post("/analyze-enhanced")
async def analyze_enhanced(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: Optional[str] = Form(None)
):
    # Save file
    file_id = str(uuid.uuid4())
    file_path = settings.upload_dir / f"{file_id}.pdf"

    with open(file_path, "wb") as f:
        f.write(await resume.read())

    # Use enhanced service
    try:
        result = enhanced_service.analyze_resume_enhanced(
            resume_path=str(file_path),
            job_description=job_description,
            job_title=job_title,
            enable_evaluation=False
        )

        # Cleanup
        if file_path.exists():
            file_path.unlink()

        return JSONResponse({"status": "completed", "result": result})

    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2**: Test with subset of users

```bash
# Standard endpoint (existing users)
POST /api/upload

# Enhanced endpoint (test users)
POST /api/analyze-enhanced
```

**Step 3**: Compare results

```python
# Script to compare both versions
from app.services.analysis_service import analyze_resume
from app.services.enhanced_analysis_service import enhanced_service

def compare_versions(resume_path, job_description):
    # Standard version
    standard_result = analyze_resume(resume_path, job_description)

    # Enhanced version
    enhanced_result = enhanced_service.analyze_resume_enhanced(
        resume_path=resume_path,
        job_description=job_description
    )

    print("Standard Score:", standard_result['match_analysis']['overall_score'])
    print("Enhanced Score:", enhanced_result['match_analysis']['overall_score'])
    print("Enhanced Duration:", enhanced_result['rag_metadata']['total_duration'])
```

**Step 4**: Migrate gradually

- Week 1-2: 10% of traffic to enhanced
- Week 3-4: 50% of traffic to enhanced
- Week 5+: 100% to enhanced, keep standard as fallback

---

### Strategy 2: Feature Flags

Use configuration to toggle between standard and enhanced.

**Step 1**: Add feature flag to `config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Feature flags
    use_enhanced_rag: bool = False
```

**Step 2**: Create unified endpoint

```python
from app.services.analysis_service import analyze_resume
from app.services.enhanced_analysis_service import enhanced_service
from app.core.config import settings

@router.post("/analyze")
async def analyze(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: Optional[str] = Form(None)
):
    file_path = save_uploaded_file(resume)

    try:
        if settings.use_enhanced_rag:
            result = enhanced_service.analyze_resume_enhanced(
                resume_path=str(file_path),
                job_description=job_description,
                job_title=job_title
            )
        else:
            result = analyze_resume(
                resume_path=str(file_path),
                job_description=job_description,
                job_title=job_title
            )

        # Cleanup
        if file_path.exists():
            file_path.unlink()

        return JSONResponse({"status": "completed", "result": result})

    except Exception as e:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3**: Toggle via environment variable

```bash
# .env
USE_ENHANCED_RAG=false  # Use standard
# or
USE_ENHANCED_RAG=true   # Use enhanced
```

---

### Strategy 3: Direct Replacement

Replace standard with enhanced (highest risk).

**⚠️ Warning**: Test thoroughly before production deployment!

**Step 1**: Backup current code

```bash
git checkout -b backup-standard-version
git commit -am "Backup before enhanced migration"
```

**Step 2**: Update `routes.py` to use enhanced service

```python
# Replace
from app.services.analysis_service import analyze_resume

# With
from app.services.enhanced_analysis_service import enhanced_service

# Update function
result = enhanced_service.analyze_resume_enhanced(...)
```

**Step 3**: Test extensively

```bash
# Run existing test suite
pytest tests/

# Run new benchmarks
python scripts/benchmark.py --quick
```

**Step 4**: Monitor performance

- Check latency (enhanced is slower but more accurate)
- Monitor error rates
- Track user satisfaction metrics

---

## Configuration Tuning

### For Latency-Sensitive Applications

```python
# config.py
use_hyde = False                # Disable HyDE (saves ~2-3s)
use_reranking = True            # Keep re-ranking (minor overhead)
retrieval_top_k = 20            # Reduce candidates
rerank_top_k = 5                # Fewer final results
```

Expected performance:
- Latency: ~2-4s (vs 5-8s full pipeline)
- Quality: Better than standard, not as good as full

### For Quality-Critical Applications

```python
# config.py
use_hyde = True
use_reranking = True
retrieval_top_k = 30
rerank_top_k = 10
hyde_num_documents = 5
```

Expected performance:
- Latency: ~5-8s
- Quality: Highest

### Balanced Configuration

```python
# config.py
use_hyde = True
use_reranking = True
retrieval_top_k = 25
rerank_top_k = 8
hyde_num_documents = 3
```

Expected performance:
- Latency: ~3-5s
- Quality: Very Good

---

## Data Migration

### Vector Database

Enhanced RAG uses semantic chunks instead of full documents.

**Option 1**: Re-ingest all resumes (recommended)

```python
from app.services.enhanced_analysis_service import enhanced_service
import os

# Get all resumes
resume_dir = "./resumes"

for resume_file in os.listdir(resume_dir):
    if resume_file.endswith('.pdf'):
        result = enhanced_service.ingest_resume_to_knowledge_base(
            resume_path=os.path.join(resume_dir, resume_file),
            metadata={"source": "migration"}
        )
        print(f"Ingested {resume_file}: {result['chunk_count']} chunks")
```

**Option 2**: Keep existing data (backward compatible)

The enhanced vector store works with existing data. Old documents remain accessible via standard methods.

```python
# Old method still works
vector_store = VectorStore()
results = vector_store.search_similar_resumes(query="Python developer", n_results=5)
```

---

## Testing Checklist

Before deploying enhanced RAG:

- [ ] Install all dependencies
- [ ] Verify Ollama is running (`ollama list`)
- [ ] Test semantic chunking on sample resume
- [ ] Test HyDE generation with sample job description
- [ ] Test full pipeline end-to-end
- [ ] Run benchmark comparing standard vs enhanced
- [ ] Check latency is acceptable
- [ ] Verify quality improvements
- [ ] Test error handling (malformed PDFs, etc.)
- [ ] Monitor memory usage under load
- [ ] Test with various resume formats (PDF, DOCX)

---

## Rollback Plan

If issues arise, rollback is simple:

**If using Strategy 1 (Parallel)**:
- Route traffic back to standard endpoint
- No code changes needed

**If using Strategy 2 (Feature Flags)**:
```bash
# .env
USE_ENHANCED_RAG=false
```
- Restart server
- Traffic automatically uses standard version

**If using Strategy 3 (Direct Replacement)**:
```bash
git checkout backup-standard-version
git push --force
# Redeploy
```

---

## Monitoring

### Key Metrics to Track

1. **Latency** (p50, p95, p99)
   - Standard: ~1-2s
   - Enhanced (no HyDE): ~2-3s
   - Enhanced (full): ~5-8s

2. **Error Rates**
   - Should remain < 1%

3. **Match Quality**
   - Use evaluation scores
   - Track user feedback

4. **Resource Usage**
   - CPU: Enhanced uses ~30% more
   - Memory: Enhanced uses ~20% more
   - Disk: Chunks use ~2-3x space

### Logging

Enhanced service provides detailed logs:

```python
import logging

logging.basicConfig(level=logging.INFO)

# Logs show:
# - Chunking stats
# - HyDE generation time
# - Retrieval results count
# - Re-ranking improvements
# - Total pipeline duration
```

---

## Common Issues

### Issue: "Cross-encoder model not found"

**Solution**:
```bash
pip install --upgrade sentence-transformers
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"
```

### Issue: Enhanced version is too slow

**Solution**:
```python
# config.py
use_hyde = False  # Biggest latency reduction
retrieval_top_k = 20  # Reduce candidates
```

### Issue: "Ollama connection refused"

**Solution**:
```bash
ollama serve
# In another terminal
ollama pull llama2
```

### Issue: Memory errors during re-ranking

**Solution**:
```python
# config.py
rerank_top_k = 5  # Reduce candidates to re-rank
```

---

## Support

For migration assistance:
1. Review logs for specific errors
2. Check configuration settings
3. Run benchmark to diagnose performance
4. Use evaluation tools to compare quality
5. Consult README_RAG.md for detailed documentation

---

## Timeline Suggestion

**Week 1**: Setup and Testing
- Install dependencies
- Test with sample data
- Run benchmarks
- Review evaluation results

**Week 2**: Pilot Deployment
- Deploy to staging
- Test with real data
- Monitor performance
- Gather feedback

**Week 3**: Limited Production
- Deploy to 10-25% of users
- Monitor closely
- Compare metrics

**Week 4**: Full Rollout
- Gradually increase to 100%
- Keep standard as fallback
- Continue monitoring

---

## Success Criteria

Enhanced RAG is ready for production when:

- ✅ Latency is acceptable for your use case
- ✅ Quality scores improved vs standard
- ✅ Error rate < 1%
- ✅ Resource usage is sustainable
- ✅ Team comfortable with monitoring/debugging
- ✅ Rollback plan tested

---

## Next Steps

1. Choose migration strategy (recommend: Parallel Deployment)
2. Install dependencies: `pip install -r requirements.txt`
3. Configure settings in `config.py`
4. Test with sample data
5. Run benchmark: `python scripts/benchmark.py --quick`
6. Deploy to staging
7. Gradual production rollout
8. Monitor and optimize

Happy migrating! 🚀
