"""
LLM-as-Judge Evaluation Module
Uses an LLM to evaluate RAG pipeline quality through structured prompts.
"""

import logging
import json
import re
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMJudge:
    """
    Uses a local LLM (via Ollama) as a judge to evaluate:
    1. Retrieval Relevance: Do retrieved chunks match job requirements?
    2. Coverage: Are all key requirements addressed?
    3. Quality: Is the output professional and compelling?
    """

    RELEVANCE_PROMPT = """You are an expert evaluator of resume matching systems. Evaluate how relevant the retrieved resume chunks are to the job description.

Job Description:
{job_description}

Retrieved Resume Chunks:
{chunks}

Evaluate on a scale of 1-5:
1 = Not relevant at all
2 = Slightly relevant
3 = Moderately relevant
4 = Mostly relevant
5 = Highly relevant

Provide your evaluation as JSON:
{{
    "relevance_score": <1-5>,
    "reasoning": "Brief explanation of the score",
    "matching_points": ["point 1", "point 2"],
    "missing_points": ["point 1", "point 2"]
}}"""

    COVERAGE_PROMPT = """You are an expert evaluator. Assess how well the retrieved chunks cover the job requirements.

Job Description:
{job_description}

Retrieved Resume Chunks:
{chunks}

Evaluate coverage on a scale of 1-5:
1 = Almost no requirements covered
2 = Few requirements covered
3 = Half of requirements covered
4 = Most requirements covered
5 = All or nearly all requirements covered

Provide your evaluation as JSON:
{{
    "coverage_score": <1-5>,
    "reasoning": "Brief explanation",
    "covered_requirements": ["req 1", "req 2"],
    "missing_requirements": ["req 1", "req 2"]
}}"""

    QUALITY_PROMPT = """You are an expert evaluator. Assess the quality of the generated resume content.

Generated Resume Content:
{generated_content}

Job Description Context:
{job_description}

Evaluate quality on a scale of 1-5:
1 = Poor quality, unprofessional
2 = Below average quality
3 = Average quality
4 = Good quality
5 = Excellent quality, highly professional

Provide your evaluation as JSON:
{{
    "quality_score": <1-5>,
    "reasoning": "Brief explanation",
    "strengths": ["strength 1", "strength 2"],
    "areas_for_improvement": ["area 1", "area 2"]
}}"""

    def __init__(self, llm=None, db_path: str = "./evaluation_results/llm_judge.db"):
        """
        Initialize LLM Judge.

        Args:
            llm: Optional LLM instance
            db_path: Path to SQLite database for storing results
        """
        self.llm = llm or Ollama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model
        )

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for storing evaluation results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evaluation_type TEXT NOT NULL,
                job_description TEXT,
                chunks TEXT,
                generated_content TEXT,
                relevance_score REAL,
                coverage_score REAL,
                quality_score REAL,
                reasoning TEXT,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def evaluate_relevance(
        self,
        job_description: str,
        retrieved_chunks: List[str]
    ) -> Dict:
        """
        Evaluate relevance of retrieved chunks to job description.

        Args:
            job_description: The job description text
            retrieved_chunks: List of retrieved resume chunks

        Returns:
            Evaluation result with score and reasoning
        """
        try:
            chunks_text = "\n\n---\n\n".join(
                [f"Chunk {i+1}:\n{chunk}" for i, chunk in enumerate(retrieved_chunks)]
            )

            prompt = PromptTemplate(
                input_variables=["job_description", "chunks"],
                template=self.RELEVANCE_PROMPT
            )

            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(
                job_description=job_description,
                chunks=chunks_text
            )

            # Parse JSON response
            result = self._parse_json_response(response)

            if not result:
                result = {
                    "relevance_score": 3,
                    "reasoning": "Could not parse LLM response",
                    "matching_points": [],
                    "missing_points": []
                }

            # Store in database
            self._store_evaluation(
                evaluation_type="relevance",
                job_description=job_description,
                chunks=chunks_text,
                relevance_score=result.get("relevance_score"),
                reasoning=json.dumps(result),
                metadata=json.dumps({"num_chunks": len(retrieved_chunks)})
            )

            logger.info(f"Relevance evaluation: {result.get('relevance_score')}/5")

            return {
                "success": True,
                "evaluation": result,
                "type": "relevance"
            }

        except Exception as e:
            logger.error(f"Error in relevance evaluation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def evaluate_coverage(
        self,
        job_description: str,
        retrieved_chunks: List[str]
    ) -> Dict:
        """
        Evaluate how well retrieved chunks cover job requirements.

        Args:
            job_description: The job description text
            retrieved_chunks: List of retrieved resume chunks

        Returns:
            Evaluation result with coverage score
        """
        try:
            chunks_text = "\n\n---\n\n".join(
                [f"Chunk {i+1}:\n{chunk}" for i, chunk in enumerate(retrieved_chunks)]
            )

            prompt = PromptTemplate(
                input_variables=["job_description", "chunks"],
                template=self.COVERAGE_PROMPT
            )

            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(
                job_description=job_description,
                chunks=chunks_text
            )

            result = self._parse_json_response(response)

            if not result:
                result = {
                    "coverage_score": 3,
                    "reasoning": "Could not parse LLM response",
                    "covered_requirements": [],
                    "missing_requirements": []
                }

            # Store in database
            self._store_evaluation(
                evaluation_type="coverage",
                job_description=job_description,
                chunks=chunks_text,
                coverage_score=result.get("coverage_score"),
                reasoning=json.dumps(result),
                metadata=json.dumps({"num_chunks": len(retrieved_chunks)})
            )

            logger.info(f"Coverage evaluation: {result.get('coverage_score')}/5")

            return {
                "success": True,
                "evaluation": result,
                "type": "coverage"
            }

        except Exception as e:
            logger.error(f"Error in coverage evaluation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def evaluate_quality(
        self,
        generated_content: str,
        job_description: str
    ) -> Dict:
        """
        Evaluate quality of generated resume content.

        Args:
            generated_content: The generated resume content
            job_description: Job description for context

        Returns:
            Evaluation result with quality score
        """
        try:
            prompt = PromptTemplate(
                input_variables=["generated_content", "job_description"],
                template=self.QUALITY_PROMPT
            )

            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(
                generated_content=generated_content,
                job_description=job_description
            )

            result = self._parse_json_response(response)

            if not result:
                result = {
                    "quality_score": 3,
                    "reasoning": "Could not parse LLM response",
                    "strengths": [],
                    "areas_for_improvement": []
                }

            # Store in database
            self._store_evaluation(
                evaluation_type="quality",
                job_description=job_description,
                generated_content=generated_content,
                quality_score=result.get("quality_score"),
                reasoning=json.dumps(result)
            )

            logger.info(f"Quality evaluation: {result.get('quality_score')}/5")

            return {
                "success": True,
                "evaluation": result,
                "type": "quality"
            }

        except Exception as e:
            logger.error(f"Error in quality evaluation: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def evaluate_complete_pipeline(
        self,
        job_description: str,
        retrieved_chunks: List[str],
        generated_content: str
    ) -> Dict:
        """
        Evaluate complete RAG pipeline (retrieval + generation).

        Args:
            job_description: Job description
            retrieved_chunks: Retrieved resume chunks
            generated_content: Generated resume content

        Returns:
            Complete evaluation with all scores
        """
        relevance_eval = self.evaluate_relevance(job_description, retrieved_chunks)
        coverage_eval = self.evaluate_coverage(job_description, retrieved_chunks)
        quality_eval = self.evaluate_quality(generated_content, job_description)

        # Calculate overall score (average)
        scores = []
        if relevance_eval.get("success"):
            scores.append(relevance_eval["evaluation"].get("relevance_score", 0))
        if coverage_eval.get("success"):
            scores.append(coverage_eval["evaluation"].get("coverage_score", 0))
        if quality_eval.get("success"):
            scores.append(quality_eval["evaluation"].get("quality_score", 0))

        overall_score = sum(scores) / len(scores) if scores else 0

        return {
            "success": True,
            "overall_score": overall_score,
            "relevance": relevance_eval,
            "coverage": coverage_eval,
            "quality": quality_eval,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _parse_json_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from LLM response."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        return None

    def _store_evaluation(
        self,
        evaluation_type: str,
        job_description: str = None,
        chunks: str = None,
        generated_content: str = None,
        relevance_score: float = None,
        coverage_score: float = None,
        quality_score: float = None,
        reasoning: str = None,
        metadata: str = None
    ):
        """Store evaluation in SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO evaluations (
                evaluation_type, job_description, chunks, generated_content,
                relevance_score, coverage_score, quality_score, reasoning, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            evaluation_type, job_description, chunks, generated_content,
            relevance_score, coverage_score, quality_score, reasoning, metadata
        ))

        conn.commit()
        conn.close()

    def get_evaluation_stats(
        self,
        evaluation_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict:
        """
        Get statistics from stored evaluations.

        Args:
            evaluation_type: Filter by type (relevance, coverage, quality)
            limit: Maximum number of records to analyze

        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        where_clause = f"WHERE evaluation_type = '{evaluation_type}'" if evaluation_type else ""

        cursor.execute(f"""
            SELECT
                evaluation_type,
                AVG(relevance_score) as avg_relevance,
                AVG(coverage_score) as avg_coverage,
                AVG(quality_score) as avg_quality,
                COUNT(*) as count
            FROM evaluations
            {where_clause}
            GROUP BY evaluation_type
            LIMIT ?
        """, (limit,))

        results = cursor.fetchall()
        conn.close()

        stats = {}
        for row in results:
            eval_type = row[0]
            stats[eval_type] = {
                "avg_relevance": row[1],
                "avg_coverage": row[2],
                "avg_quality": row[3],
                "count": row[4]
            }

        return stats

    def get_recent_evaluations(self, limit: int = 10) -> List[Dict]:
        """
        Get recent evaluations.

        Args:
            limit: Number of records to return

        Returns:
            List of recent evaluations
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                evaluation_type, relevance_score, coverage_score, quality_score,
                reasoning, timestamp
            FROM evaluations
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        results = cursor.fetchall()
        conn.close()

        evaluations = []
        for row in results:
            evaluations.append({
                "type": row[0],
                "relevance_score": row[1],
                "coverage_score": row[2],
                "quality_score": row[3],
                "reasoning": row[4],
                "timestamp": row[5]
            })

        return evaluations


# Global judge instance
llm_judge = LLMJudge()
