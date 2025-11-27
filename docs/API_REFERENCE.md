# Resume Analyzer - API Reference

## Base URL
- Development: `http://localhost:8000/api`
- Production: `https://your-domain.com/api`

## Endpoints

### POST /upload
Upload and analyze resume (backend LLM mode).

**Request:**
```typescript
FormData {
  resume: File (PDF),
  job_description: string,
  job_title?: string
}
```

**Response:**
```json
{
  "status": "completed",
  "result": {
    "match_analysis": {
      "overall_score": 85,
      "skills": {
        "matched": ["python", "react"],
        "missing": ["kubernetes"],
        "transferable": []
      },
      "ats_score": 78
    },
    "improvements": [...],
    "comparisons": [...],
    "similar_resumes": [...]
  }
}
```

### POST /process-resume
Process resume for client-side LLM analysis (hybrid mode).

**Request:** Same as /upload

**Response:**
```json
{
  "status": "success",
  "resume_text": "...",
  "job_description": "...",
  "similar_resumes": [...]
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "vector_store": "connected",
  "resumes_stored": 42
}
```

## Error Codes

TODO: Document error codes and handling.

## Rate Limiting

TODO: Document rate limiting policies.

## Authentication

TODO: Document authentication if implemented.
