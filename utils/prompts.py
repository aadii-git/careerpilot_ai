"""
CareerPilot AI — Centralized Prompt Templates

All system instructions and prompt-building functions are defined here.
No raw prompt strings should appear in agent files.
"""

from __future__ import annotations

from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# System Instructions (persistent, role-defining)
# ─────────────────────────────────────────────────────────────────────────────

ORCHESTRATOR_SYSTEM = """
You are CareerPilot AI, an expert AI career mentor.
You have deep expertise in technology careers, learning paths, and professional development.
You are encouraging, precise, and adaptive to the user's level.
Always be concise but thorough. Never give generic advice — tailor everything to the user's context.
""".strip()

CAREER_AGENT_SYSTEM = """
You are an expert Career Coach with 20+ years of experience in the tech industry.
You specialize in helping people transition into AI/ML, software engineering, and data roles.
Analyze careers objectively. Be honest about gaps. Be motivating about possibilities.
Always provide concrete, actionable recommendations.
""".strip()

LEARNING_AGENT_SYSTEM = """
You are a world-class interactive AI tutor.
You teach complex technical concepts through structured lessons:
1. Overview → 2. Real-World Analogy → 3. Code Example → 4. Practice Task →
5. Mini Project → 6. Quiz → 7. Reflection → 8. Resources
Never overwhelm the student. Teach one concept at a time.
Use clear language and practical examples. Adapt to the student's level.
""".strip()

ROADMAP_AGENT_SYSTEM = """
You are an expert Learning Path Architect specializing in tech career roadmaps.
You create personalized, month-by-month learning plans that are realistic and progressive.
Consider the user's current skills, career goal, and available time.
Ensure each month builds on the previous one. Prioritize high-impact skills.
""".strip()

QUIZ_AGENT_SYSTEM = """
You are a technical assessment expert.
Generate challenging but fair quiz questions. Evaluate answers rigorously.
Provide detailed explanations for every answer — both correct and incorrect ones.
Be encouraging but accurate in scoring.
""".strip()

INTERVIEW_AGENT_SYSTEM = """
You are a senior technical interviewer with experience at top tech companies.
Conduct realistic mock interviews. Ask one question at a time. Listen carefully.
Score honestly and provide specific, actionable feedback.
Help candidates improve their interview skills through practice.
""".strip()

MEMORY_AGENT_SYSTEM = """
You help summarize and contextualize a user's learning history.
Extract key insights: what they know, what they struggle with, their progress.
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Career Agent Prompts
# ─────────────────────────────────────────────────────────────────────────────

def career_analysis_prompt(
    career_goal: str,
    experience: str,
    resume_skills: Optional[list[str]] = None,
) -> str:
    skills_section = ""
    if resume_skills:
        skills_section = f"\nExtracted Resume Skills: {', '.join(resume_skills)}"

    return f"""
Perform a comprehensive career analysis for this user.

Career Goal: {career_goal}
Current Experience: {experience}{skills_section}

Return a JSON object with exactly this structure:
{{
  "career_goal": "{career_goal}",
  "current_skills": ["skill1", "skill2", ...],
  "missing_skills": ["skill1", "skill2", ...],
  "readiness_percentage": <0-100>,
  "recommended_projects": ["project1: description", ...],
  "career_paths": ["path1", "path2", ...],
  "summary": "<3-4 sentence personalized career analysis>"
}}

Be specific and honest. List at least 5 current skills and 5 missing skills.
Readiness should reflect how prepared they are for their goal right now.
""".strip()


def skill_gap_report_prompt(current_skills: list[str], career_goal: str) -> str:
    return f"""
Given these current skills: {', '.join(current_skills)}
Career goal: {career_goal}

Create a detailed skill gap analysis. Be specific about what's missing and why it matters.
Return JSON:
{{
  "critical_gaps": ["skill: why it matters", ...],
  "nice_to_have": ["skill: benefit", ...],
  "timeline_estimate": "<realistic timeframe to be job-ready>",
  "immediate_actions": ["action1", "action2", "action3"]
}}
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Roadmap Agent Prompts
# ─────────────────────────────────────────────────────────────────────────────

def roadmap_generation_prompt(
    career_goal: str,
    current_skills: list[str],
    missing_skills: list[str],
    completed_topics: Optional[list[str]] = None,
    total_months: int = 6,
) -> str:
    completed_ctx = ""
    if completed_topics:
        completed_ctx = f"\nAlready completed: {', '.join(completed_topics)}"

    return f"""
Create a {total_months}-month personalized learning roadmap.

Career Goal: {career_goal}
Current Skills: {', '.join(current_skills) if current_skills else 'Beginner'}
Skills to Learn: {', '.join(missing_skills) if missing_skills else 'See career goal'}{completed_ctx}

Return a JSON object:
{{
  "career_goal": "{career_goal}",
  "total_months": {total_months},
  "items": [
    {{
      "month": 1,
      "topic": "Topic Name",
      "description": "What they will learn and why",
      "key_skills": ["skill1", "skill2"],
      "resources": ["resource1", "resource2"],
      "project": "Mini project to build"
    }},
    ...
  ],
  "summary": "<overview of the roadmap strategy>"
}}

Ensure the roadmap is progressive (each month builds on the last).
Include 1-3 topics per month. Make it realistic for someone learning part-time (10-15 hrs/week).
""".strip()


def adapt_roadmap_prompt(
    original_roadmap: list[dict],
    quiz_scores: dict[str, float],
    completed_topics: list[str],
) -> str:
    return f"""
Adapt this existing learning roadmap based on the user's performance.

Original Roadmap: {original_roadmap}
Quiz Scores by Topic: {quiz_scores}
Completed Topics: {completed_topics}

Rules:
- If quiz score < 60% for a topic, add extra practice time
- If quiz score > 85%, user can advance faster
- Don't remove completed topics

Return the FULL updated roadmap in the same JSON format as before.
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Learning Agent Prompts
# ─────────────────────────────────────────────────────────────────────────────

def lesson_stage_prompt(
    topic: str,
    stage: str,
    user_level: str = "intermediate",
    previous_content: Optional[str] = None,
) -> str:
    context = ""
    if previous_content:
        context = f"\nPrevious content covered:\n{previous_content[:500]}\n"

    stage_instructions = {
        "Overview": "Provide a clear, engaging overview of the topic. What is it? Why does it matter? What will the student learn?",
        "Real-World Analogy": "Explain the topic using a relatable real-world analogy. Make it memorable and intuitive.",
        "Code Example": "Provide a practical, working code example with line-by-line explanations. Use Python unless otherwise specified.",
        "Practice Task": "Give the student a hands-on practice task they can complete in 15-30 minutes. Be specific about what to build/do.",
        "Mini Project": "Assign a mini-project that ties everything together. Provide clear requirements and success criteria.",
        "Quiz": "This stage is handled by the Quiz Agent. Generate a 3-question quiz on this topic.",
        "Reflection": "Guide the student to reflect: What did they learn? How does it connect to their career goal? What questions remain?",
        "Resources": "Provide 5 curated resources: 2 official docs, 2 tutorials/courses (free), 1 book or deep-dive article.",
    }

    instruction = stage_instructions.get(stage, "Teach this stage of the lesson.")

    return f"""
You are teaching: {topic}
Current Stage: {stage}
Student Level: {user_level}
{context}

{instruction}

Be engaging, practical, and appropriately detailed for a {user_level} learner.
Format with clear headers and sections. Use markdown for code blocks.
""".strip()


def next_lesson_recommendation_prompt(
    completed_topics: list[str],
    quiz_scores: dict[str, float],
    career_goal: str,
    roadmap_topics: list[str],
) -> str:
    return f"""
Based on the student's progress, recommend the next best topic to study.

Career Goal: {career_goal}
Completed Topics: {completed_topics}
Quiz Scores: {quiz_scores}
Roadmap Topics: {roadmap_topics}

Choose the most appropriate next topic considering:
1. Logical progression (prerequisites first)
2. Weak areas (re-study if score < 60%)
3. Career alignment

Return JSON:
{{
  "next_topic": "topic name",
  "reason": "why this topic is recommended now",
  "estimated_hours": <number>,
  "prerequisite_check": "any prerequisites the student should review first"
}}
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Quiz Agent Prompts
# ─────────────────────────────────────────────────────────────────────────────

def quiz_generation_prompt(
    topic: str,
    question_type: str,
    difficulty: str,
    num_questions: int = 1,
) -> str:
    type_instructions = {
        "MCQ": """Generate a multiple-choice question with exactly 4 options (A, B, C, D).
Clearly indicate the correct answer.""",
        "Short Answer": """Generate a short-answer question that requires a 2-5 sentence response.
Provide a model answer.""",
        "Coding": """Generate a coding challenge appropriate for the difficulty level.
Include: problem statement, example input/output, constraints, and solution.""",
    }

    instruction = type_instructions.get(question_type, type_instructions["MCQ"])

    return f"""
Generate {num_questions} {difficulty} {question_type} question(s) on: {topic}

{instruction}

Return JSON:
{{
  "question_type": "{question_type}",
  "difficulty": "{difficulty}",
  "question": "the question text",
  "options": ["A. opt1", "B. opt2", "C. opt3", "D. opt4"],
  "correct_answer": "the correct answer",
  "explanation": "detailed explanation of why this is correct"
}}

For Short Answer or Coding, set options to null.
Make the question challenging but fair for {difficulty} level.
""".strip()


def quiz_evaluation_prompt(
    question: str,
    correct_answer: str,
    user_answer: str,
    question_type: str,
    topic: str,
) -> str:
    return f"""
Evaluate this quiz answer for the topic: {topic}

Question: {question}
Question Type: {question_type}
Correct Answer: {correct_answer}
User's Answer: {user_answer}

Return JSON:
{{
  "score": <0-100>,
  "is_correct": <true or false>,
  "feedback": "specific feedback on the user's answer",
  "correct_answer": "{correct_answer}",
  "explanation": "detailed explanation of the correct answer and why the user's answer was right/wrong"
}}

For MCQ: 100 if correct, 0 if wrong.
For Short Answer / Coding: partial credit (0, 25, 50, 75, 100) based on accuracy and completeness.
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Interview Agent Prompts
# ─────────────────────────────────────────────────────────────────────────────

def interview_question_prompt(
    interview_type: str,
    career_goal: str,
    previous_questions: Optional[list[str]] = None,
    resume_summary: Optional[str] = None,
) -> str:
    prev_ctx = ""
    if previous_questions:
        prev_ctx = f"\nAvoid repeating these questions: {previous_questions[-5:]}"

    resume_ctx = ""
    if resume_summary and interview_type == "Resume-Based":
        resume_ctx = f"\nResume context: {resume_summary}"

    type_focus = {
        "Behavioral": "Use the STAR method context. Ask about past experiences, teamwork, conflict, leadership.",
        "Technical": f"Ask technical questions relevant to {career_goal}. Focus on core concepts and problem-solving.",
        "Resume-Based": "Ask about specific projects, technologies, or experiences mentioned in the resume.",
        "Coding": f"Give a coding problem appropriate for a {career_goal} role. Start with easy-medium difficulty.",
        "System Design": f"Ask a system design question relevant to {career_goal}. Focus on scalability and trade-offs.",
    }

    focus = type_focus.get(interview_type, type_focus["Technical"])

    return f"""
You are conducting a {interview_type} interview for a {career_goal} position.
{focus}{prev_ctx}{resume_ctx}

Generate ONE interview question. Make it realistic and appropriately challenging.

Return JSON:
{{
  "question": "the interview question",
  "question_type": "{interview_type}",
  "expected_topics": ["topic1", "topic2", "topic3"],
  "time_limit_minutes": <suggested time to answer>
}}
""".strip()


def interview_evaluation_prompt(
    question: str,
    answer: str,
    interview_type: str,
    career_goal: str,
) -> str:
    return f"""
Evaluate this interview answer for a {career_goal} position.

Interview Type: {interview_type}
Question: {question}
Candidate's Answer: {answer}

Score each dimension from 0.0 to 10.0:

Return JSON:
{{
  "communication": <0.0-10.0>,
  "technical_knowledge": <0.0-10.0>,
  "confidence": <0.0-10.0>,
  "problem_solving": <0.0-10.0>,
  "overall_score": <0.0-10.0>,
  "strengths": ["strength1", "strength2", "strength3"],
  "improvements": ["area1", "area2", "area3"],
  "feedback": "2-3 paragraph detailed feedback on the answer"
}}

Be honest and specific. The goal is to help the candidate improve.
For Behavioral questions, weight communication and confidence higher.
For Technical/Coding, weight technical_knowledge and problem_solving higher.
""".strip()


# ─────────────────────────────────────────────────────────────────────────────
# Memory / Context Prompts
# ─────────────────────────────────────────────────────────────────────────────

def session_summary_prompt(
    career_goal: str,
    completed_lessons: list[str],
    quiz_scores: dict[str, float],
    weak_topics: list[str],
    strong_topics: list[str],
) -> str:
    return f"""
Summarize this user's learning journey and provide personalized recommendations.

Career Goal: {career_goal}
Completed Lessons: {completed_lessons}
Quiz Scores by Topic: {quiz_scores}
Weak Topics (< 60%): {weak_topics}
Strong Topics (> 80%): {strong_topics}

Write a motivating, personalized 3-paragraph summary that:
1. Celebrates their progress
2. Identifies areas for improvement
3. Recommends their next 3 learning actions

Be specific and encouraging.
""".strip()
