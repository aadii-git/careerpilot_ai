"""
CareerPilot AI — Centralized Configuration
Loads all settings from environment variables and defines app-wide constants.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# ─── Load .env ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("careerpilot")

# ─── Groq ─────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_DEFAULT: str = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_TEMPERATURE: float = float(os.getenv("GROQ_TEMPERATURE", "0.7"))
GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "8192"))
# Preserve old Gemini vars for backward compatibility (optional)
GEMINI_API_KEY: str = GROQ_API_KEY
GEMINI_MODEL_DEFAULT: str = GROQ_MODEL_DEFAULT
GEMINI_TEMPERATURE: float = GROQ_TEMPERATURE
GEMINI_MAX_TOKENS: int = GROQ_MAX_TOKENS

# ─── Database ───────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", str(BASE_DIR / "careerpilot.db"))

# ─── Application ────────────────────────────────────────────────────────────
APP_NAME: str = "CareerPilot AI"
APP_VERSION: str = "1.0.0"
APP_DESCRIPTION: str = "Your AI-powered career mentor"
DEFAULT_USER_ID: int = 1

# ─── Learning ────────────────────────────────────────────────────────────────
DIFFICULTY_LEVELS: list[str] = ["Easy", "Medium", "Hard"]
QUIZ_QUESTION_TYPES: list[str] = ["MCQ", "Short Answer", "Coding"]
LESSON_STAGES: list[str] = [
    "Overview",
    "Real-World Analogy",
    "Code Example",
    "Practice Task",
    "Mini Project",
    "Quiz",
    "Reflection",
    "Resources",
]

# ─── Career Domains ──────────────────────────────────────────────────────────
CAREER_PATHS: list[str] = [
    "AI/ML Engineer",
    "Data Scientist",
    "Data Engineer",
    "Backend Engineer",
    "Frontend Engineer",
    "Full Stack Developer",
    "DevOps / MLOps Engineer",
    "Cybersecurity Analyst",
    "Cloud Architect",
    "Product Manager",
]

# ─── Interview Types ─────────────────────────────────────────────────────────
INTERVIEW_TYPES: list[str] = [
    "Behavioral",
    "Technical",
    "Resume-Based",
    "Coding",
    "System Design",
]

# ─── Score Categories ────────────────────────────────────────────────────────
INTERVIEW_SCORE_CATEGORIES: list[str] = [
    "Communication",
    "Technical Knowledge",
    "Confidence",
    "Problem Solving",
]
