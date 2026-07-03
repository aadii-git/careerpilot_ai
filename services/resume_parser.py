"""
CareerPilot AI — Resume Parser Service

Extracts text from uploaded PDF resumes using PyMuPDF,
then uses Gemini to analyze skills, experience, education,
certifications, and generates a skill-gap report.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ResumeAnalysis(BaseModel):
    """Structured output of resume analysis."""

    skills: list[str] = []
    experience_years: Optional[float] = None
    experience_summary: str = ""
    education: list[str] = []
    certifications: list[str] = []
    projects: list[str] = []
    raw_text: str = ""
    analysis_summary: str = ""


class ResumeParser:
    """
    Parses PDF resumes and uses Gemini to extract structured information.

    Usage:
        parser = ResumeParser(gemini_service)
        analysis = parser.parse_pdf_bytes(pdf_bytes, career_goal="AI Engineer")
    """

    def __init__(self, gemini_service: "GeminiService") -> None:  # type: ignore[name-defined]
        self._gemini = gemini_service

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract raw text from PDF bytes using PyMuPDF."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_parts: list[str] = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts).strip()
        except ImportError:
            logger.error("PyMuPDF not installed. Run: pip install PyMuPDF")
            raise
        except Exception as exc:
            logger.error("Failed to extract PDF text: %s", exc)
            raise RuntimeError(f"PDF extraction failed: {exc}") from exc

    def analyze_resume(
        self,
        resume_text: str,
        career_goal: Optional[str] = None,
    ) -> ResumeAnalysis:
        """
        Use Gemini to analyze resume text and extract structured info.

        Args:
            resume_text: Raw text extracted from the PDF.
            career_goal: The user's target role for gap analysis context.

        Returns:
            ResumeAnalysis with all extracted fields.
        """
        goal_context = f"The user's career goal is: {career_goal}." if career_goal else ""

        prompt = f"""
Analyze the following resume text and extract structured information.
{goal_context}

RESUME TEXT:
{resume_text[:4000]}

Return a JSON object with exactly these keys:
{{
  "skills": ["skill1", "skill2", ...],
  "experience_years": <number or null>,
  "experience_summary": "<1-2 sentence summary>",
  "education": ["degree/institution", ...],
  "certifications": ["cert1", ...],
  "projects": ["project title: brief description", ...],
  "analysis_summary": "<3-4 sentence professional analysis of the resume>"
}}

Be precise. Extract only what is explicitly stated in the resume.
"""
        data = self._gemini.generate_json(prompt)

        if not isinstance(data, dict):
            logger.warning("Resume analysis returned non-dict: %s", type(data))
            return ResumeAnalysis(
                skills=[],
                experience_years=None,
                experience_summary="Could not parse resume.",
                education=[],
                certifications=[],
                projects=[],
                raw_text=resume_text,
                analysis_summary="Analysis failed. Please try again.",
            )

        return ResumeAnalysis(
            skills=data.get("skills") or [],
            experience_years=data.get("experience_years"),
            experience_summary=data.get("experience_summary") or "",
            education=data.get("education") or [],
            certifications=data.get("certifications") or [],
            projects=data.get("projects") or [],
            raw_text=resume_text,
            analysis_summary=data.get("analysis_summary") or "",
        )

    def parse_pdf_bytes(
        self,
        pdf_bytes: bytes,
        career_goal: Optional[str] = None,
    ) -> ResumeAnalysis:
        """
        Full pipeline: extract PDF text → analyze with Gemini.

        Args:
            pdf_bytes: Raw bytes of the uploaded PDF.
            career_goal: Optional target role for contextual analysis.

        Returns:
            ResumeAnalysis model.
        """
        logger.info("Parsing resume PDF (%d bytes)", len(pdf_bytes))
        text = self.extract_text_from_pdf(pdf_bytes)
        if not text:
            raise ValueError("No text could be extracted from the PDF.")
        return self.analyze_resume(text, career_goal=career_goal)

    def generate_skill_gap_report(
        self,
        analysis: ResumeAnalysis,
        career_goal: str,
        target_skills: list[str],
    ) -> dict[str, list[str]]:
        """
        Compare extracted resume skills against target role requirements.

        Returns:
            Dict with keys: 'present', 'missing', 'recommended_to_learn'
        """
        present = [s for s in target_skills if
                   any(s.lower() in skill.lower() for skill in analysis.skills)]
        missing = [s for s in target_skills if s not in present]

        prompt = f"""
Given:
- Career Goal: {career_goal}
- Skills the person HAS: {analysis.skills}
- Skills they are MISSING for the role: {missing}

Suggest 5 specific technologies or skills they should learn next, prioritized by impact.
Return JSON: {{"recommended_to_learn": ["skill1", "skill2", ...]}}
"""
        recs = self._gemini.generate_json(prompt)
        recommended = recs.get("recommended_to_learn", missing[:5]) if isinstance(recs, dict) else missing[:5]

        return {
            "present": present,
            "missing": missing,
            "recommended_to_learn": recommended,
        }
