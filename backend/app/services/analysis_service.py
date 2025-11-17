from app.utils.pdf_parser import PDFParser
from app.services.vector_store import VectorStore
from app.services.llm_service import LLMService
from app.models.schemas import AnalysisResult, MatchAnalysis, SkillMatch, ImprovementSuggestion, ComparisonHighlight
from typing import Dict
import logging

logger = logging.getLogger(__name__)


def analyze_resume(
    resume_path: str,
    job_description: str,
    job_title: str = None
) -> Dict:
    """
    Analyze a resume against a job description.
    """
    try:
        logger.info("Starting resume analysis")

        # Step 1: Extract text from PDF
        logger.info("Extracting text from PDF")
        pdf_parser = PDFParser()
        resume_text = pdf_parser.extract_text(resume_path)

        if not resume_text:
            raise ValueError("Could not extract text from PDF")

        # Step 2: Search for similar resumes
        logger.info("Searching similar resumes")
        vector_store = VectorStore()
        similar_resumes = vector_store.search_similar_resumes(
            query_text=job_description,
            n_results=5
        )

        # Step 3: Analyze match using LLM
        logger.info("Analyzing resume match")
        llm_service = LLMService()
        match_analysis = llm_service.analyze_resume_match(
            resume_text=resume_text,
            job_description=job_description,
            similar_resumes=similar_resumes
        )

        # Step 4: Generate improvement suggestions
        logger.info("Generating improvement suggestions")
        improvements = llm_service.generate_improvements(
            resume_text=resume_text,
            job_description=job_description,
            analysis=match_analysis
        )

        # Step 5: Compare requirements
        logger.info("Comparing requirements")
        comparisons = llm_service.compare_requirements(
            resume_text=resume_text,
            job_description=job_description
        )

        # Step 6: Store resume in vector DB for future comparisons
        logger.info("Storing resume for future use")
        vector_store.add_resume(
            resume_text=resume_text,
            metadata={
                "job_title": job_title or "Unknown",
                "filename": resume_path.split("/")[-1]
            }
        )

        # Build result
        result = {
            "match_analysis": {
                "overall_score": match_analysis.get("overall_score", 0),
                "skills": {
                    "matched": match_analysis.get("matched_skills", []),
                    "missing": match_analysis.get("missing_skills", []),
                    "transferable": []  # TODO: Can be enhanced
                },
                "experience_relevance": {},  # TODO: Can be enhanced
                "ats_score": match_analysis.get("ats_score", 0)
            },
            "improvements": improvements,
            "comparisons": comparisons,
            "similar_resumes": [
                {
                    "id": sr["id"],
                    "similarity": 1 - sr.get("distance", 0) if sr.get("distance") is not None else 0,
                    "metadata": sr.get("metadata", {})
                }
                for sr in similar_resumes[:3]  # Top 3
            ]
        }

        logger.info("Resume analysis completed successfully")
        return result

    except Exception as e:
        logger.error(f"Error in analyze_resume: {str(e)}")
        raise
