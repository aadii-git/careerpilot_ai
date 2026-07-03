"""
CareerPilot AI — Shared Utility Helpers

Common utility functions used across agents and services.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# JSON Utilities
# ─────────────────────────────────────────────────────────────────────────────

def safe_parse_json(text: str) -> Optional[Any]:
    """
    Safely parse a JSON string, stripping markdown fences if present.

    Returns:
        Parsed Python object, or None on failure.
    """
    if not text:
        return None
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse failed: %s | Text: %.200s", exc, text)
        return None


def extract_json_from_text(text: str) -> Optional[Any]:
    """
    Try to find and extract a JSON object or array embedded in text.

    Useful when the model wraps JSON in prose.
    """
    # Try finding JSON object
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        result = safe_parse_json(match.group())
        if result is not None:
            return result
    # Try finding JSON array
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        result = safe_parse_json(match.group())
        if result is not None:
            return result
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Text Utilities
# ─────────────────────────────────────────────────────────────────────────────

def truncate_text(text: str, max_chars: int = 2000, suffix: str = "...") -> str:
    """Truncate text to max_chars, appending suffix if truncated."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(suffix)] + suffix


def clean_text(text: str) -> str:
    """Remove excessive whitespace and normalize line endings."""
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def slugify(text: str) -> str:
    """Convert text to a URL/filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# Score Utilities
# ─────────────────────────────────────────────────────────────────────────────

def score_to_grade(score: float, max_score: float = 100.0) -> str:
    """Convert a numeric score to a letter grade."""
    percentage = (score / max_score) * 100 if max_score > 0 else 0
    if percentage >= 90:
        return "A"
    elif percentage >= 80:
        return "B"
    elif percentage >= 70:
        return "C"
    elif percentage >= 60:
        return "D"
    else:
        return "F"


def score_to_emoji(score: float, max_score: float = 10.0) -> str:
    """Return an emoji representing the score level."""
    percentage = (score / max_score) * 100 if max_score > 0 else 0
    if percentage >= 85:
        return "🌟"
    elif percentage >= 70:
        return "✅"
    elif percentage >= 50:
        return "⚠️"
    else:
        return "❌"


def format_score_display(score: float, max_score: float = 100.0) -> str:
    """Format score for display with percentage and grade."""
    pct = (score / max_score) * 100 if max_score > 0 else 0
    grade = score_to_grade(score, max_score)
    emoji = score_to_emoji(score, max_score)
    return f"{emoji} {pct:.1f}% (Grade: {grade})"


# ─────────────────────────────────────────────────────────────────────────────
# Date / Time Utilities
# ─────────────────────────────────────────────────────────────────────────────

def format_datetime(iso_string: str) -> str:
    """Format an ISO datetime string to a human-readable format."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%b %d, %Y at %I:%M %p")
    except Exception:
        return iso_string


def days_since(iso_string: str) -> int:
    """Return number of days since the given ISO datetime."""
    try:
        dt = datetime.fromisoformat(iso_string)
        delta = datetime.utcnow() - dt
        return delta.days
    except Exception:
        return 0


def now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.utcnow().isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# List / Dict Utilities
# ─────────────────────────────────────────────────────────────────────────────

def deduplicate(items: list) -> list:
    """Remove duplicates while preserving order."""
    seen: set = set()
    result = []
    for item in items:
        key = str(item).lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def merge_skill_lists(existing: list[str], new_items: list[str]) -> list[str]:
    """Merge two skill lists, deduplicating case-insensitively."""
    combined = existing + new_items
    return deduplicate(combined)


def status_color(status: str) -> str:
    """Return a CSS color string for a roadmap item status."""
    colors = {
        "completed": "#10b981",   # green
        "in_progress": "#f59e0b", # amber
        "pending": "#6b7280",     # gray
    }
    return colors.get(status, "#6b7280")


def difficulty_color(difficulty: str) -> str:
    """Return a color for difficulty level."""
    colors = {
        "Easy": "#10b981",
        "Medium": "#f59e0b",
        "Hard": "#ef4444",
    }
    return colors.get(difficulty, "#6b7280")
