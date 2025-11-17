from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class JobDescription(BaseModel):
    text: str
    title: Optional[str] = None
    company: Optional[str] = None


class SkillMatch(BaseModel):
    matched: List[str] = Field(default_factory=list)
    missing: List[str] = Field(default_factory=list)
    transferable: List[str] = Field(default_factory=list)


class MatchAnalysis(BaseModel):
    overall_score: float = Field(ge=0, le=100, description="Overall compatibility score (0-100)")
    skills: SkillMatch
    experience_relevance: Dict[str, float] = Field(default_factory=dict)
    ats_score: float = Field(ge=0, le=100, description="ATS-friendliness score (0-100)")


class ImprovementSuggestion(BaseModel):
    section: str
    original: Optional[str] = None
    suggestion: str
    priority: str = Field(default="medium")  # low, medium, high


class ComparisonHighlight(BaseModel):
    requirement: str
    status: str  # matched, missing, partial
    resume_content: Optional[str] = None


class AnalysisResult(BaseModel):
    task_id: str
    match_analysis: Optional[MatchAnalysis] = None
    improvements: List[ImprovementSuggestion] = Field(default_factory=list)
    comparisons: List[ComparisonHighlight] = Field(default_factory=list)
    similar_resumes: List[Dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    result: Optional[AnalysisResult] = None
    error: Optional[str] = None
