# CareerPilot AI 🚀

> **Your AI-powered career mentor** — Analyze skills, build roadmaps, learn interactively, practice interviews, and track your progress.

---

## Features

| Feature | Description |
|---------|-------------|
| 🎯 Career Assessment | Upload your resume and define your goal — get a full skill-gap report |
| 🗺️ Roadmap Generation | Month-by-month personalized learning plan that adapts to your progress |
| 📚 Interactive Learning | AI tutor teaches through analogies, code, exercises, and projects |
| 🧠 Adaptive Quizzes | MCQ, short-answer, and coding quizzes at Easy / Medium / Hard difficulty |
| 🎤 Mock Interviews | Behavioral, technical, system design & coding interviews with scoring |
| 📊 Progress Tracking | Plotly dashboards showing streaks, scores, and skill mastery |
| 💾 Persistent Memory | All sessions stored in SQLite — the AI remembers you |

---

## Tech Stack

- **AI**: Groq API (`meta-llama/llama-4-scout-17b-16e-instruct`)
- **UI**: Streamlit
- **Database**: SQLite
- **Data**: Pandas, Plotly
- **Models**: Pydantic v2
- **PDF**: PyMuPDF (fitz)
- **Config**: python-dotenv

---

## Quick Start

### 1. Clone / Download

```bash
git clone <repo-url>
cd careerpilot_ai
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Key

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

Get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/app/apikey).

### 4. Run the App

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Project Structure

```
careerpilot_ai/
├── app.py                    # Streamlit entry point
├── config.py                 # Global configuration
├── requirements.txt
├── .env.example
│
├── agents/
│   ├── orchestrator.py       # Master router & context manager
│   ├── career_agent.py       # Career analysis & gap detection
│   ├── learning_agent.py     # Interactive AI tutor
│   ├── interview_agent.py    # Mock interview engine
│   ├── roadmap_agent.py      # Learning roadmap generator
│   ├── quiz_agent.py         # Quiz generation & evaluation
│   └── memory_agent.py       # Session persistence
│
├── database/
│   ├── sqlite.py             # DB manager & CRUD
│   └── models.py             # Pydantic data models
│
├── services/
│   ├── gemini_service.py     # Centralized Gemini API wrapper
│   ├── resume_parser.py      # PDF parsing & analysis
│   └── progress_service.py   # Streak & score calculations
│
├── utils/
│   ├── prompts.py            # All prompt templates
│   └── helpers.py            # Shared utilities
│
└── pages/
    ├── 1_Dashboard.py
    ├── 2_Career_Assessment.py
    ├── 3_Learning.py
    ├── 4_Interview.py
    └── 5_Progress.py
```

---

## Agent Architecture

```
User Request
     │
     ▼
OrchestratorAgent ──► routes to ──► CareerAgent
                                    RoadmapAgent
                                    LearningAgent
                                    QuizAgent
                                    InterviewAgent
                                    MemoryAgent (always active)
```

The **Orchestrator** determines intent, delegates to the right agent, and combines results into a coherent response. The **Memory Agent** reads/writes context to SQLite before and after every interaction.

---

## Usage Guide

### Career Assessment
1. Navigate to **Career Assessment**
2. Enter your career goal (e.g., "AI Engineer")
3. Describe your current experience
4. Optionally upload your resume (PDF)
5. Click **Analyze** — receive a full gap report

### Learning
1. Navigate to **Learning**
2. Select a topic from your roadmap
3. Work through the 8-stage lesson (Overview → Resources)
4. Take the quiz and get instant AI feedback

### Interview Practice
1. Navigate to **Interview Practice**
2. Choose interview type (Behavioral / Technical / etc.)
3. Answer questions in the chat interface
4. Receive detailed scoring and improvement tips

### Progress
1. Navigate to **Progress**
2. View charts for quiz scores, roadmap completion, skill mastery, and interview scores

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | — | Your Google Gemini API key |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Model to use |
| `GEMINI_TEMPERATURE` | No | `0.7` | Generation temperature |
| `GEMINI_MAX_TOKENS` | No | `8192` | Max output tokens |
| `DB_PATH` | No | `careerpilot.db` | SQLite database path |

---

## License

MIT — Free to use, modify, and distribute.
