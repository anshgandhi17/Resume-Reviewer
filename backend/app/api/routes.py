from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import JSONResponse
from app.models.schemas import JobDescription, TaskStatus, AnalysisResult
from app.services.analysis.analysis_service import analyze_resume
from app.services.parsing.pdf_parser import PDFParser
from app.services.parsing.batch_processor import BatchProcessor
from app.services.parsing.project_extractor import ProjectExtractor
from app.services.parsing.experience_extractor import ExperienceExtractor
from app.services.llm.project_ranker import ProjectRanker
from app.services.generation.star_formatter import STARFormatter
from app.services.generation.star_validator import STARValidator
from app.services.generation.resume_builder import ResumeBuilder
from app.services.generation.latex_renderer import LaTeXRenderer
from app.services.storage.vector_store import VectorStore
from fastapi.responses import FileResponse
from app.core.config import settings
import os
import uuid
from typing import Optional, List, Dict
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


@router.post("/upload/batch")
async def batch_upload_resumes(
    files: List[UploadFile] = File(...),
):
    """
    Upload and process multiple resume files in parallel.

    This endpoint:
    1. Accepts up to 5 PDF files simultaneously
    2. Processes them in parallel (parse → chunk → embed → store)
    3. Returns aggregated results with success/failure counts

    Args:
        files: List of PDF files to process (max 5)

    Returns:
        Batch processing result with individual results and summary statistics
    """
    # Validate number of files
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > settings.batch_max_files:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum: {settings.batch_max_files}"
        )

    # Validate file types and sizes
    temp_file_paths = []
    file_metadata = []

    try:
        for idx, file in enumerate(files):
            # Validate file type
            if not file.filename.endswith('.pdf'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is not a PDF. Only PDF files are supported."
                )

            # Read and validate file size
            contents = await file.read()
            if len(contents) > settings.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} exceeds maximum size of {settings.max_file_size / 1024 / 1024}MB"
                )

            # Save to temporary location
            file_id = str(uuid.uuid4())
            file_path = settings.upload_dir / f"{file_id}_{file.filename}"

            with open(file_path, "wb") as f:
                f.write(contents)

            temp_file_paths.append(str(file_path))
            file_metadata.append({
                "resume_id": file_id,
                "original_filename": file.filename,
                "file_size": len(contents)
            })

            logger.info(f"Saved temporary file: {file.filename} → {file_path}")

        # Process batch in parallel
        logger.info(f"Starting batch processing of {len(temp_file_paths)} files")
        batch_processor = BatchProcessor(
            timeout_per_file=settings.batch_timeout_per_file
        )

        result = batch_processor.process_batch(
            file_paths=temp_file_paths,
            metadata_list=file_metadata
        )

        # Clean up temporary files
        batch_processor.cleanup_temp_files(temp_file_paths)

        return JSONResponse({
            "status": result['status'],
            "message": f"Processed {result['summary']['successful']} of {result['summary']['total_files']} files successfully",
            "summary": result['summary'],
            "results": result['results']
        })

    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        # Clean up any temp files
        for file_path in temp_file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
        raise

    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        # Clean up temp files
        for file_path in temp_file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@router.post("/rank-projects")
async def rank_projects(
    files: List[UploadFile] = File(...),
    job_description: str = Form(...),
    top_k: int = Form(10),
    ranking_method: str = Form("llm")
):
    """
    Extract and rank projects from multiple resumes.

    This endpoint:
    1. Accepts multiple resume PDFs
    2. Extracts all projects from each resume
    3. Ranks projects by relevance to job description using LLM or vector similarity
    4. Returns top K projects with relevance scores

    Args:
        files: List of resume PDF files (max 10)
        job_description: Job description to match against
        top_k: Number of top projects to return (default: 10)
        ranking_method: Ranking method to use - "llm" or "vector" (default: "llm")

    Returns:
        Ranked list of projects with scores and metadata
    """
    # Validate inputs
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Too many files. Maximum: 10 resumes"
        )

    if ranking_method not in ["llm", "vector"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid ranking_method. Must be 'llm' or 'vector'"
        )

    temp_file_paths = []
    all_projects = []
    all_experiences = []

    try:
        # Process each resume
        for idx, file in enumerate(files):
            # Validate file type
            if not file.filename.endswith('.pdf'):
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} is not a PDF"
                )

            # Read file
            contents = await file.read()
            if len(contents) > settings.max_file_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} exceeds maximum size"
                )

            # Save to temporary location
            file_id = str(uuid.uuid4())
            file_path = settings.upload_dir / f"{file_id}_{file.filename}"

            with open(file_path, "wb") as f:
                f.write(contents)

            temp_file_paths.append(str(file_path))

            # Extract text from PDF
            logger.info(f"Extracting text from {file.filename}")
            resume_text = PDFParser.extract_text(str(file_path))

            # Extract projects from this resume
            logger.info(f"Extracting projects from {file.filename}")
            projects = ProjectExtractor.extract_projects_from_text(
                resume_text,
                resume_id=file.filename
            )

            logger.info(f"Found {len(projects)} projects in {file.filename}")
            all_projects.extend(projects)

            # Extract work experiences from this resume
            logger.info(f"Extracting work experiences from {file.filename}")
            experiences = ExperienceExtractor.extract_experiences_from_text(
                resume_text,
                resume_id=file.filename
            )

            logger.info(f"Found {len(experiences)} work experiences in {file.filename}")
            all_experiences.extend(experiences)

        # Rank all projects using selected method
        logger.info(f"Ranking {len(all_projects)} total projects using {ranking_method} method")
        if ranking_method == "llm":
            from app.services.llm.project_ranker import ProjectRanker
            ranker = ProjectRanker()
        else:  # vector
            from app.services.llm.vector_ranker import VectorRanker
            ranker = VectorRanker()

        ranked_projects = ranker.rank_projects(
            projects=all_projects,
            job_description=job_description,
            top_k=top_k
        )

        # Rank all experiences (using the same ranker with different content)
        logger.info(f"Ranking {len(all_experiences)} total experiences against job description")
        # Convert experiences to project-like format for ranking
        experience_as_projects = []
        for exp in all_experiences:
            from app.services.parsing.project_extractor import Project
            proj = Project(
                title=f"{exp.title} at {exp.company}",
                description=f"{exp.date_range} | {exp.location}" if exp.date_range else exp.location,
                technologies=exp.technologies,
                bullets=exp.bullets,
                source_resume_id=exp.source_resume_id,
                raw_text=exp.raw_text
            )
            experience_as_projects.append(proj)

        ranked_experiences = ranker.rank_projects(
            projects=experience_as_projects,
            job_description=job_description,
            top_k=top_k
        ) if all_experiences else []

        # Clean up temporary files
        for file_path in temp_file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.warning(f"Could not delete temp file {file_path}: {e}")

        # Return ranked projects and experiences
        return JSONResponse({
            "status": "success",
            "total_resumes": len(files),
            "total_projects_found": len(all_projects),
            "total_experiences_found": len(all_experiences),
            "top_projects": ranked_projects,
            "top_experiences": ranked_experiences,
            "summary": ranker.generate_project_summary(ranked_projects, top_k=min(5, len(ranked_projects)))
        })

    except HTTPException:
        # Clean up temp files on validation errors
        for file_path in temp_file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
        raise

    except Exception as e:
        logger.error(f"Error in project ranking: {str(e)}")
        # Clean up temp files
        for file_path in temp_file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Project ranking failed: {str(e)}")


@router.post("/generate-resume")
async def generate_resume(
    ranked_projects: List[Dict] = Body(...),
    ranked_experiences: List[Dict] = Body([]),
    source_resume: UploadFile = File(...),
    candidate_name: Optional[str] = Body(None),
    job_title: str = Body("Software Engineer"),
    top_k_projects: int = Body(3),
    top_k_experiences: int = Body(3)
):
    """
    Generate an optimized resume PDF with best matching projects and experiences.

    This endpoint:
    1. Takes ranked projects and experiences from frontend
    2. Extracts contact info from source resume
    3. Builds resume data with top K projects and experiences
    4. Generates PDF using LaTeX renderer

    Args:
        ranked_projects: List of ranked project dicts from /rank-projects
        ranked_experiences: List of ranked experience dicts from /rank-projects
        source_resume: Primary resume PDF for extracting contact info
        candidate_name: Optional name (extracted from resume if not provided)
        job_title: Target job title for the resume
        top_k_projects: Number of top projects to include (default: 3)
        top_k_experiences: Number of top experiences to include (default: 3)

    Returns:
        PDF file download
    """
    temp_file_path = None

    try:
        # Save source resume temporarily
        contents = await source_resume.read()
        file_id = str(uuid.uuid4())
        temp_file_path = settings.upload_dir / f"{file_id}_{source_resume.filename}"

        with open(temp_file_path, "wb") as f:
            f.write(contents)

        # Extract text from source resume
        logger.info(f"Extracting contact info from {source_resume.filename}")
        resume_text = PDFParser.extract_text(str(temp_file_path))

        # Extract contact info and name
        contact_info = ResumeBuilder.extract_contact_from_resume(resume_text)
        name = candidate_name or ResumeBuilder.extract_name_from_resume(resume_text)

        # Extract education
        education = ResumeBuilder.extract_education_from_resume(resume_text)

        # Get all skills from projects and experiences
        all_skills = []
        for proj in ranked_projects[:top_k_projects]:
            if proj.get('matched_skills'):
                all_skills.extend(proj['matched_skills'])

        for exp in ranked_experiences[:top_k_experiences]:
            if exp.get('matched_skills'):
                all_skills.extend(exp['matched_skills'])

        # Build resume data
        logger.info(f"Building resume with top {top_k_projects} projects and {top_k_experiences} experiences")
        resume_data = ResumeBuilder.build_resume_data(
            ranked_projects=ranked_projects,
            contact_info=contact_info,
            skills=all_skills,
            name=name,
            job_title=job_title,
            summary=None,
            education=education,
            ranked_experiences=ranked_experiences,
            top_k_projects=top_k_projects,
            top_k_experiences=top_k_experiences
        )

        # Generate PDF
        logger.info("Generating PDF resume")
        renderer = LaTeXRenderer()
        pdf_path = renderer.generate_pdf(
            resume_data=resume_data,
            output_filename=f"{name.replace(' ', '_')}_optimized_resume.pdf"
        )

        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        # Return PDF file
        logger.info(f"Resume generated successfully: {pdf_path}")
        return FileResponse(
            path=str(pdf_path),
            media_type='application/pdf',
            filename=f"{name.replace(' ', '_')}_resume.pdf"
        )

    except Exception as e:
        logger.error(f"Error generating resume: {str(e)}")
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Resume generation failed: {str(e)}")


@router.post("/format-star")
async def format_star(
    resume_text: str = Body(..., embed=True),
    filter_section: Optional[str] = Body(None, embed=True),
    enable_validation: bool = Body(True, embed=True),
    strictness: str = Body("high", embed=True)
):
    """
    Format resume bullets into STAR format with validation.

    This endpoint:
    1. Extracts bullet points from resume text
    2. Formats each bullet using STAR framework (Situation, Task, Action, Result)
    3. Validates formatted bullets to detect hallucination
    4. Returns both formatted bullets and validation results

    Args:
        resume_text: Full resume text or specific section text
        filter_section: Optional section filter ('experience', 'projects')
        enable_validation: Whether to run validation (default: True)
        strictness: Validation strictness ('low', 'medium', 'high')

    Returns:
        Formatted bullets with validation results
    """
    try:
        # Initialize services
        formatter = STARFormatter()
        validator = STARValidator(strictness=strictness) if enable_validation else None

        # Format bullets
        logger.info("Formatting resume bullets to STAR format")
        formatted_bullets = formatter.format_resume_bullets(
            resume_text=resume_text,
            filter_section=filter_section
        )

        # Validate if requested
        if enable_validation and validator:
            logger.info("Validating formatted bullets")
            for bullet in formatted_bullets:
                if bullet['status'] == 'formatted':
                    validation = validator.validate_bullet(
                        original=bullet['original'],
                        star_formatted=bullet['star_formatted']
                    )
                    bullet['validation'] = validation

        # Calculate summary statistics
        total = len(formatted_bullets)
        successful = sum(1 for b in formatted_bullets if b['status'] == 'formatted')
        failed = sum(1 for b in formatted_bullets if b['status'] == 'failed')

        if validate:
            valid = sum(
                1 for b in formatted_bullets
                if b.get('validation', {}).get('is_valid', False)
            )
            flagged = sum(
                1 for b in formatted_bullets
                if b.get('validation', {}).get('flags', [])
            )
        else:
            valid = successful
            flagged = 0

        summary = {
            'total_bullets': total,
            'successfully_formatted': successful,
            'failed': failed,
            'valid': valid,
            'flagged': flagged
        }

        logger.info(
            f"STAR formatting complete: {successful}/{total} formatted, "
            f"{valid}/{successful} valid"
        )

        return JSONResponse({
            'status': 'success',
            'summary': summary,
            'bullets': formatted_bullets
        })

    except Exception as e:
        logger.error(f"Error in STAR formatting: {str(e)}")
        raise HTTPException(status_code=500, detail=f"STAR formatting failed: {str(e)}")


@router.post("/format-star/chunks")
async def format_star_from_chunks(
    chunks: List[Dict] = Body(...),
    validate: bool = Body(True, embed=True),
    strictness: str = Body("high", embed=True)
):
    """
    Format bullets from semantic chunks into STAR format.

    This endpoint works with pre-chunked resume data (from RAG pipeline).

    Args:
        chunks: List of semantic chunks with metadata
        validate: Whether to run validation (default: True)
        strictness: Validation strictness ('low', 'medium', 'high')

    Returns:
        Formatted bullets with validation results
    """
    try:
        # Initialize services
        formatter = STARFormatter()
        validator = STARValidator(strictness=strictness) if validate else None

        # Format bullets from chunks
        logger.info(f"Formatting bullets from {len(chunks)} chunks")
        formatted_bullets = formatter.format_chunks_to_star(chunks)

        # Validate if requested
        if validate and validator:
            logger.info("Validating formatted bullets")
            for bullet in formatted_bullets:
                if bullet['status'] == 'formatted':
                    validation = validator.validate_bullet(
                        original=bullet['original'],
                        star_formatted=bullet['star_formatted']
                    )
                    bullet['validation'] = validation

        # Calculate summary
        total = len(formatted_bullets)
        successful = sum(1 for b in formatted_bullets if b['status'] == 'formatted')
        failed = sum(1 for b in formatted_bullets if b['status'] == 'failed')

        if validate:
            valid = sum(
                1 for b in formatted_bullets
                if b.get('validation', {}).get('is_valid', False)
            )
            flagged = sum(
                1 for b in formatted_bullets
                if b.get('validation', {}).get('flags', [])
            )
        else:
            valid = successful
            flagged = 0

        summary = {
            'total_bullets': total,
            'successfully_formatted': successful,
            'failed': failed,
            'valid': valid,
            'flagged': flagged
        }

        return JSONResponse({
            'status': 'success',
            'summary': summary,
            'bullets': formatted_bullets
        })

    except Exception as e:
        logger.error(f"Error in STAR formatting: {str(e)}")
        raise HTTPException(status_code=500, detail=f"STAR formatting failed: {str(e)}")


@router.post("/approve-star-bullet")
async def approve_star_bullet(
    bullet_id: str = Body(..., embed=True),
    approved_version: str = Body(..., embed=True),
    metadata: Optional[Dict] = Body(None, embed=True)
):
    """
    Approve a STAR-formatted bullet for use in final resume.

    This endpoint stores approved bullets for later use in resume generation.

    Args:
        bullet_id: Unique identifier for the bullet
        approved_version: The approved STAR-formatted text
        metadata: Optional metadata (job_title, company, etc.)

    Returns:
        Confirmation of approval
    """
    try:
        # TODO: Implement storage of approved bullets
        # For now, just return success
        logger.info(f"Approved STAR bullet: {bullet_id}")

        return JSONResponse({
            'status': 'success',
            'message': 'Bullet approved successfully',
            'bullet_id': bullet_id
        })

    except Exception as e:
        logger.error(f"Error approving bullet: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")
