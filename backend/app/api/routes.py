from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from app.models.schemas import JobDescription, TaskStatus, AnalysisResult
from app.services.analysis.analysis_service import analyze_resume
from app.services.parsing.pdf_parser import PDFParser
from app.services.storage.vector_store import VectorStore
from app.core.config import settings
import os
import uuid
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload")
async def upload_resume(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: Optional[str] = Form(None)
):
    """
    Upload a resume and analyze it against a job description.
    Returns the analysis result directly.
    (Legacy endpoint - uses backend LLM)
    """
    # Validate file type
    if not resume.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Validate file size
    contents = await resume.read()
    if len(contents) > settings.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_file_size / 1024 / 1024}MB"
        )

    # Save file
    file_id = str(uuid.uuid4())
    file_path = settings.upload_dir / f"{file_id}.pdf"

    try:
        with open(file_path, "wb") as f:
            f.write(contents)

        # Perform analysis
        logger.info(f"Starting analysis for file: {file_id}")
        result = analyze_resume(
            resume_path=str(file_path),
            job_description=job_description,
            job_title=job_title
        )

        return JSONResponse({
            "status": "completed",
            "result": result
        })

    except Exception as e:
        logger.error(f"Error analyzing resume: {str(e)}")
        # Clean up the uploaded file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/process-resume")
async def process_resume(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    job_title: Optional[str] = Form(None)
):
    """
    Process a resume: extract text and find similar resumes.
    Returns parsed text and similar resumes for client-side LLM analysis.
    This endpoint enables hosting the backend while users run Ollama locally.
    """
    # Validate file type
    if not resume.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Validate file size
    contents = await resume.read()
    if len(contents) > settings.max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_file_size / 1024 / 1024}MB"
        )

    # Save file
    file_id = str(uuid.uuid4())
    file_path = settings.upload_dir / f"{file_id}.pdf"

    try:
        with open(file_path, "wb") as f:
            f.write(contents)

        # Extract text from PDF
        logger.info(f"Extracting text from PDF: {file_id}")
        pdf_parser = PDFParser()
        resume_text = pdf_parser.extract_text(str(file_path))

        if not resume_text:
            raise ValueError("Could not extract text from PDF")

        # Search for similar resumes
        logger.info("Searching similar resumes")
        vector_store = VectorStore()
        similar_resumes = vector_store.search_similar_resumes(
            query_text=job_description,
            n_results=5
        )

        # Store resume in vector DB for future comparisons
        logger.info("Storing resume for future use")
        vector_store.add_resume(
            resume_text=resume_text,
            metadata={
                "job_title": job_title or "Unknown",
                "filename": resume.filename
            }
        )

        # Clean up the uploaded file
        if file_path.exists():
            file_path.unlink()

        # Return data for client-side LLM processing
        return JSONResponse({
            "status": "success",
            "resume_text": resume_text,
            "job_description": job_description,
            "similar_resumes": [
                {
                    "id": sr["id"],
                    "similarity": 1 - sr.get("distance", 0) if sr.get("distance") is not None else 0,
                    "metadata": sr.get("metadata", {})
                }
                for sr in similar_resumes[:3]  # Top 3
            ]
        })

    except Exception as e:
        logger.error(f"Error processing resume: {str(e)}")
        # Clean up the uploaded file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.services.storage.vector_store import VectorStore

    try:
        # Check vector store
        vector_store = VectorStore()
        resume_count = vector_store.count_resumes()

        return {
            "status": "healthy",
            "vector_store": "connected",
            "resumes_stored": resume_count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
