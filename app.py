"""
CareerPilot AI — Main Streamlit Entry Point

Configures the multi-page app, initialises shared state,
and renders the home/welcome screen.
"""

from __future__ import annotations

import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import config
from config import APP_NAME, APP_VERSION, DB_PATH, DEFAULT_USER_ID

# ── Page Configuration ────────────────────────────────────────────────────────
if __name__ == "__main__":
    st.set_page_config(
        page_title=f"{APP_NAME}",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )

# ── Global CSS ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Root Variables ── */
:root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #111827;
    --bg-card: #1a2332;
    --bg-card-hover: #1e2a3d;
    --accent-primary: #6366f1;
    --accent-secondary: #8b5cf6;
    --accent-green: #10b981;
    --accent-amber: #f59e0b;
    --accent-red: #ef4444;
    --accent-blue: #3b82f6;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --border: #1e293b;
    --border-accent: #6366f1;
    --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    --gradient-green: linear-gradient(135deg, #10b981 0%, #059669 100%);
    --shadow-glow: 0 0 30px rgba(99, 102, 241, 0.15);
}

/* ── Global Reset ── */
* { font-family: 'Inter', sans-serif !important; }
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-primary) !important;
    color: var(--text-primary) !important;
}
[data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

/* ── Sidebar Nav ── */
[data-testid="stSidebarNav"] a {
    border-radius: 8px !important;
    margin: 2px 8px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stSidebarNav"] a:hover {
    background: rgba(99,102,241,0.15) !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: var(--gradient-primary) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--gradient-primary) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(99, 102, 241, 0.45) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    transition: border-color 0.2s ease !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent-primary) !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.2) !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1rem 1.2rem !important;
    transition: all 0.2s ease !important;
}
[data-testid="stMetric"]:hover {
    border-color: var(--accent-primary) !important;
    box-shadow: var(--shadow-glow) !important;
}
[data-testid="stMetricValue"] {
    color: var(--accent-primary) !important;
    font-weight: 700 !important;
    font-size: 1.8rem !important;
}
[data-testid="stMetricLabel"] { color: var(--text-secondary) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-card) !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    color: var(--text-secondary) !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.stTabs [aria-selected="true"] {
    background: var(--gradient-primary) !important;
    color: white !important;
}

/* ── Progress Bar ── */
.stProgress > div > div { background: var(--gradient-primary) !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: var(--bg-card) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-weight: 600 !important;
}

/* ── Info / Warning / Error boxes ── */
.stAlert { border-radius: 10px !important; }
[data-baseweb="notification"] { border-radius: 10px !important; }

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border-accent); border-radius: 3px; }

/* ── Card Component ── */
.cp-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.25s ease;
}
.cp-card:hover {
    border-color: var(--accent-primary);
    box-shadow: var(--shadow-glow);
    transform: translateY(-2px);
}

/* ── Hero Gradient Text ── */
.gradient-text {
    background: var(--gradient-primary);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ── Badge ── */
.cp-badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}
.badge-green { background: rgba(16,185,129,0.15); color: #10b981; }
.badge-amber { background: rgba(245,158,11,0.15); color: #f59e0b; }
.badge-purple { background: rgba(99,102,241,0.15); color: #6366f1; }
.badge-red { background: rgba(239,68,68,0.15); color: #ef4444; }

/* ── Chat Messages ── */
.chat-user {
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 12px 12px 4px 12px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    margin-left: 2rem;
}
.chat-ai {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px 12px 12px 4px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    margin-right: 2rem;
}
</style>
    """, unsafe_allow_html=True)


# ── Session State Initialisation ──────────────────────────────────────────────

def init_session_state() -> None:
    """Initialise all required session state variables."""
    defaults = {
        "orchestrator": None,
        "user_id": DEFAULT_USER_ID,
        "api_key_valid": False,
        "current_topic": None,
        "current_stage": "Overview",
        "lesson_chat_history": [],
        "interview_chat_history": [],
        "interview_type": "Technical",
        "interview_questions_asked": [],
        "quiz_question": None,
        "quiz_answer_submitted": False,
        "quiz_evaluation": None,
        "current_interview_question": None,
        "interview_answer_submitted": False,
        "interview_evaluation": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_orchestrator():
    """Get or create the orchestrator (cached in session state)."""
    if st.session_state.orchestrator is None:
        try:
            from agents.orchestrator import OrchestratorAgent
            st.session_state.orchestrator = OrchestratorAgent(
                db_path=DB_PATH,
                user_id=st.session_state.user_id,
            )
            st.session_state.api_key_valid = True
        except ValueError as e:
            st.session_state.api_key_valid = False
            return None
        except Exception as e:
            st.session_state.api_key_valid = False
            return None
    return st.session_state.orchestrator


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    """Render the sidebar with logo, user info, and navigation."""
    with st.sidebar:
        # Logo & Brand
        st.markdown("""
        <div style="text-align:center; padding: 1.5rem 0 1rem 0;">
            <div style="font-size: 3rem; margin-bottom: 0.25rem;">🚀</div>
            <h1 style="font-size:1.4rem; font-weight:800; margin:0; 
                background: linear-gradient(135deg, #6366f1, #8b5cf6);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                CareerPilot AI
            </h1>
            <p style="font-size:0.75rem; color:#64748b; margin:0.25rem 0 0 0;">
                Your AI Career Mentor
            </p>
        </div>
        <hr style="margin: 0.75rem 0; border-color: #1e293b;">
        """, unsafe_allow_html=True)

        # User Stats (quick view)
        orch = get_orchestrator()
        if orch:
            try:
                ctx = orch.get_context()
                user = orch.get_user()
                st.markdown(f"""
                <div style="padding: 0.75rem; background: #1a2332; border-radius: 12px; margin-bottom: 1rem;">
                    <div style="font-weight:700; font-size:0.95rem;">👤 {user.name}</div>
                    <div style="font-size:0.8rem; color:#94a3b8; margin-top:0.25rem;">
                        🎯 {ctx.get('career_goal', 'Goal not set')}
                    </div>
                    <div style="font-size:0.8rem; color:#10b981; margin-top:0.25rem;">
                        🔥 {ctx.get('learning_streak', 0)} day streak
                    </div>
                </div>
                """, unsafe_allow_html=True)
            except Exception:
                pass

        # API key integrated via .env; no UI warning needed

        st.markdown(f"""
        <div style="position:fixed; bottom:1rem; left:0; right:0; text-align:center;
             font-size:0.7rem; color:#334155;">
            {APP_NAME} v{APP_VERSION}
        </div>
        """, unsafe_allow_html=True)


# ── Main Home Page ────────────────────────────────────────────────────────────
if __name__ == "__main__":

    init_session_state()
    render_sidebar()

    # Hero Section
    st.markdown("""
    <div style="text-align:center; padding: 3rem 0 2rem 0;">
        <div style="font-size:4rem; margin-bottom:1rem;">🚀</div>
        <h1 style="font-size:3rem; font-weight:800; margin:0; line-height:1.2;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #3b82f6 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            CareerPilot AI
        </h1>
        <p style="font-size:1.2rem; color:#94a3b8; margin:1rem 0 0.5rem 0; font-weight:400;">
            Your personal AI-powered career mentor
        </p>
        <p style="font-size:0.95rem; color:#64748b; max-width:600px; margin:0 auto;">
            Analyze your skills, build a personalized learning roadmap, practice with an AI tutor,
            ace mock interviews, and track your journey to your dream career.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # API key is provided via .env; proceeding without UI check
    # Feature Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="cp-card" style="text-align:center;">
            <div style="font-size:2.5rem; margin-bottom:0.75rem;">🎯</div>
            <h3 style="font-weight:700; margin:0 0 0.5rem 0; color:#6366f1;">Career Assessment</h3>
            <p style="color:#94a3b8; font-size:0.875rem; margin:0;">
                Upload your resume, set your career goal, and get a detailed skill-gap analysis.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="cp-card" style="text-align:center;">
            <div style="font-size:2.5rem; margin-bottom:0.75rem;">📚</div>
            <h3 style="font-weight:700; margin:0 0 0.5rem 0; color:#8b5cf6;">Interactive Learning</h3>
            <p style="color:#94a3b8; font-size:0.875rem; margin:0;">
                AI tutor teaches with analogies, code examples, exercises, and quizzes.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="cp-card" style="text-align:center;">
            <div style="font-size:2.5rem; margin-bottom:0.75rem;">🎤</div>
            <h3 style="font-weight:700; margin:0 0 0.5rem 0; color:#3b82f6;">Mock Interviews</h3>
            <p style="color:#94a3b8; font-size:0.875rem; margin:0;">
                Practice behavioral, technical, and system design interviews with AI scoring.
            </p>
        </div>
        """, unsafe_allow_html=True)

    col4, col5, col6 = st.columns(3)
    with col4:
        st.markdown("""
        <div class="cp-card" style="text-align:center;">
            <div style="font-size:2.5rem; margin-bottom:0.75rem;">🗺️</div>
            <h3 style="font-weight:700; margin:0 0 0.5rem 0; color:#10b981;">Smart Roadmap</h3>
            <p style="color:#94a3b8; font-size:0.875rem; margin:0;">
                Month-by-month learning plan that adapts to your quiz performance.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown("""
        <div class="cp-card" style="text-align:center;">
            <div style="font-size:2.5rem; margin-bottom:0.75rem;">🧠</div>
            <h3 style="font-weight:700; margin:0 0 0.5rem 0; color:#f59e0b;">Adaptive Quizzes</h3>
            <p style="color:#94a3b8; font-size:0.875rem; margin:0;">
                MCQ, short answer, and coding challenges at Easy/Medium/Hard levels.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown("""
        <div class="cp-card" style="text-align:center;">
            <div style="font-size:2.5rem; margin-bottom:0.75rem;">📊</div>
            <h3 style="font-weight:700; margin:0 0 0.5rem 0; color:#ef4444;">Progress Tracking</h3>
            <p style="color:#94a3b8; font-size:0.875rem; margin:0;">
                Plotly dashboards: streaks, scores, skill mastery, and roadmap progress.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Quick Start CTA
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align:center; padding:2rem; background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.1));
         border: 1px solid rgba(99,102,241,0.3); border-radius:20px; margin: 1rem 0;">
        <h2 style="margin:0 0 0.75rem 0; font-weight:700;">Ready to Pilot Your Career? 🚀</h2>
        <p style="color:#94a3b8; margin:0 0 1.5rem 0;">
            Start with Career Assessment to get your personalized roadmap.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🎯 Start Career Assessment →", use_container_width=True):
            st.switch_page("pages/2_Career_Assessment.py")
