"""
CareerPilot AI — Quiz Agent

Generates MCQ, short-answer, and coding questions at multiple difficulty levels.
Evaluates user answers using Gemini and stores results in SQLite.
"""

from __future__ import annotations

import logging
from typing import Optional

from database.models import QuizEvaluation, QuizQuestion, QuizResult
from database.sqlite import DatabaseManager
from services.gemini_service import GeminiService
from utils.helpers import now_iso
from utils.prompts import (
    QUIZ_AGENT_SYSTEM,
    quiz_evaluation_prompt,
    quiz_generation_prompt,
)

logger = logging.getLogger(__name__)


class QuizAgent:
    """
    Generates and evaluates quizzes using Gemini AI.

    Supports MCQ, Short Answer, and Coding questions at Easy/Medium/Hard
    difficulty. Evaluates answers, provides explanations, and persists scores.
    """

    def __init__(self, gemini: GeminiService, db: DatabaseManager) -> None:
        self._gemini = gemini
        self._db = db

    # ── Generation ────────────────────────────────────────────────────────────

    def generate_question(
        self,
        topic: str,
        question_type: str = "MCQ",
        difficulty: str = "Medium",
    ) -> QuizQuestion:
        """
        Generate a single quiz question.

        Args:
            topic: The topic to quiz on.
            question_type: 'MCQ', 'Short Answer', or 'Coding'.
            difficulty: 'Easy', 'Medium', or 'Hard'.

        Returns:
            QuizQuestion with question, options, answer, and explanation.
        """
        logger.info(
            "Generating %s %s question on '%s'", difficulty, question_type, topic
        )

        prompt = quiz_generation_prompt(
            topic=topic,
            question_type=question_type,
            difficulty=difficulty,
            num_questions=1,
        )

        data = self._gemini.generate_json(
            prompt, system_instruction=QUIZ_AGENT_SYSTEM
        )

        if not isinstance(data, dict):
            logger.error("Quiz generation failed — bad response type: %s", type(data))
            return self._fallback_question(topic, question_type, difficulty)

        return QuizQuestion(
            question_type=data.get("question_type") or question_type,
            difficulty=data.get("difficulty") or difficulty,
            question=data.get("question") or "Question unavailable. Please try again.",
            options=data.get("options") or None,
            correct_answer=data.get("correct_answer") or "",
            explanation=data.get("explanation") or "",
        )

    def generate_quiz(
        self,
        topic: str,
        question_type: str = "MCQ",
        difficulty: str = "Medium",
        num_questions: int = 5,
    ) -> list[QuizQuestion]:
        """
        Generate multiple questions for a quiz session.

        Args:
            topic: The topic to quiz on.
            question_type: Question format.
            difficulty: Difficulty level.
            num_questions: Number of questions to generate.

        Returns:
            List of QuizQuestion objects.
        """
        questions = []
        for i in range(num_questions):
            try:
                q = self.generate_question(topic, question_type, difficulty)
                questions.append(q)
            except Exception as exc:
                logger.warning("Failed to generate question %d: %s", i + 1, exc)

        return questions

    # ── Evaluation ────────────────────────────────────────────────────────────

    def evaluate_answer(
        self,
        user_id: int,
        topic: str,
        question: QuizQuestion,
        user_answer: str,
        save_result: bool = True,
    ) -> QuizEvaluation:
        """
        Evaluate a user's answer using Gemini and optionally save the result.

        Args:
            user_id: The user's database ID.
            topic: Topic being tested.
            question: The QuizQuestion being answered.
            user_answer: The user's response text.
            save_result: Whether to persist the result to SQLite.

        Returns:
            QuizEvaluation with score, feedback, and explanation.
        """
        logger.info(
            "Evaluating %s answer for topic '%s'", question.question_type, topic
        )

        prompt = quiz_evaluation_prompt(
            question=question.question,
            correct_answer=question.correct_answer,
            user_answer=user_answer,
            question_type=question.question_type,
            topic=topic,
        )

        data = self._gemini.generate_json(
            prompt, system_instruction=QUIZ_AGENT_SYSTEM
        )

        if not isinstance(data, dict):
            logger.error("Evaluation failed — bad response")
            return QuizEvaluation(
                score=0.0,
                is_correct=False,
                feedback="Evaluation failed. Please try again.",
                correct_answer=question.correct_answer,
                explanation=question.explanation,
            )

        score = float(data.get("score") or 0.0)
        evaluation = QuizEvaluation(
            score=score,
            is_correct=bool(data.get("is_correct") or False),
            feedback=data.get("feedback") or "",
            correct_answer=data.get("correct_answer") or question.correct_answer,
            explanation=data.get("explanation") or question.explanation,
        )

        if save_result:
            self._save_quiz_result(user_id, topic, question, score)

        return evaluation

    def run_quiz_session(
        self,
        user_id: int,
        topic: str,
        questions: list[QuizQuestion],
        answers: list[str],
    ) -> dict:
        """
        Evaluate a full quiz session (all questions at once).

        Args:
            user_id: The user's ID.
            topic: Topic being assessed.
            questions: List of generated questions.
            answers: Corresponding user answers.

        Returns:
            Summary dict with total_score, percentage, evaluations list.
        """
        evaluations = []
        total_score = 0.0

        for question, answer in zip(questions, answers):
            evaluation = self.evaluate_answer(
                user_id=user_id,
                topic=topic,
                question=question,
                user_answer=answer,
                save_result=True,
            )
            evaluations.append(evaluation)
            total_score += evaluation.score

        avg_score = total_score / len(questions) if questions else 0.0
        percentage = avg_score  # Already 0-100

        return {
            "topic": topic,
            "total_questions": len(questions),
            "average_score": round(avg_score, 1),
            "percentage": round(percentage, 1),
            "evaluations": evaluations,
            "passed": percentage >= 60.0,
        }

    # ── History ───────────────────────────────────────────────────────────────

    def get_topic_performance(self, user_id: int, topic: str) -> dict:
        """Return performance statistics for a specific topic."""
        results = self._db.get_quiz_results(user_id, limit=200)
        topic_results = [r for r in results if r.topic.lower() == topic.lower()]

        if not topic_results:
            return {"topic": topic, "attempts": 0, "average": 0.0, "best": 0.0, "trend": "no data"}

        scores = [r.score for r in topic_results]
        avg = sum(scores) / len(scores)
        best = max(scores)

        # Trend: compare last 3 vs first 3
        trend = "stable"
        if len(scores) >= 6:
            first_avg = sum(scores[-3:]) / 3
            last_avg = sum(scores[:3]) / 3
            if last_avg > first_avg + 5:
                trend = "improving"
            elif last_avg < first_avg - 5:
                trend = "declining"

        return {
            "topic": topic,
            "attempts": len(scores),
            "average": round(avg, 1),
            "best": round(best, 1),
            "trend": trend,
        }

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _save_quiz_result(
        self,
        user_id: int,
        topic: str,
        question: QuizQuestion,
        score: float,
    ) -> None:
        """Persist a quiz result to the database."""
        result = QuizResult(
            user_id=user_id,
            topic=topic,
            difficulty=question.difficulty,
            question_type=question.question_type,
            score=score,
            max_score=100.0,
            created_at=now_iso(),
        )
        self._db.save_quiz_result(result)

    def _fallback_question(
        self, topic: str, question_type: str, difficulty: str
    ) -> QuizQuestion:
        """Return a safe fallback question when generation fails."""
        return QuizQuestion(
            question_type=question_type,
            difficulty=difficulty,
            question=f"What is the most important concept in {topic}? (Generation failed — please retry)",
            options=None,
            correct_answer="Please retry — API unavailable",
            explanation="Question generation failed. Check your API key.",
        )
