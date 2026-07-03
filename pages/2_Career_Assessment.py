"""
CareerPilot AI — Career Assessment Page

Allows users to:
- Set their career goal and experience
- Upload a PDF resume
- Receive a full skill-gap analysis
- View generated learning roadmap
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
from app import init_session_state, get_orchestrator, render_sidebar
from config import CAREER_PATHS

# ── Page Setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Career Assessment — CareerPilot AI", page_icon="🎯", layout="wide")
init_session_state()
render_sidebar()

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#94a3b8"),
    margin=dict(l=20, r=20, t=40, b=20),
)

orch = get_orchestrator()
if not orch:
    st.error("⚠️ Could not connect to AI. Please check your GROQ_API_KEY in `.env`.")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style="font-size:2rem; font-weight:800; margin-bottom:0.25rem;">🎯 Career Assessment</h1>
<p style="color:#64748b; margin-bottom:2rem;">
    Tell us about your career goal and experience. Upload your resume for a personalized analysis.
</p>
""", unsafe_allow_html=True)

# ── Input Form ────────────────────────────────────────────────────────────────
with st.form("career_assessment_form"):
    col_l, col_r = st.columns([1, 1])

    with col_l:
        st.markdown("#### 🎯 Your Career Goal")
        career_goal_select = st.selectbox(
            "Select a career path",
            ["Custom..."] + CAREER_PATHS,
            help="Choose from common tech careers or enter a custom goal below.",
        )
        custom_goal = st.text_input(
            "Or type your custom career goal",
            placeholder="e.g., Machine Learning Research Scientist",
        )

        st.markdown("#### 📅 Current Experience")
        experience = st.text_area(
            "Describe your background",
            placeholder=(
                "e.g., 2 years as a data analyst. Familiar with Python, SQL, and Excel. "
                "Built some ML models in college. No professional ML experience yet."
            ),
            height=120,
        )

        st.markdown("#### 👤 Your Name")
        user_name = st.text_input("Display name", value=orch.get_user().name, placeholder="Your name")

    with col_r:
        st.markdown("#### 📄 Resume Upload (Optional)")
        uploaded_file = st.file_uploader(
            "Upload your resume (PDF)",
            type=["pdf"],
            help="We'll extract your skills, experience, and projects automatically.",
        )
        if uploaded_file:
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.3);
                 border-radius:10px; padding:0.75rem; margin-top:0.5rem;">
                ✅ <strong>{uploaded_file.name}</strong> uploaded ({uploaded_file.size:,} bytes)
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### ⚙️ Roadmap Settings")
        total_months = st.slider(
            "Roadmap duration (months)",
            min_value=3,
            max_value=12,
            value=6,
            step=1,
        )

        st.markdown("#### 📝 Notes")
        notes = st.text_area(
            "Anything else to consider?",
            placeholder="e.g., I can study 10 hours per week. I prefer hands-on projects.",
            height=80,
        )

    submitted = st.form_submit_button(
        "🚀 Analyze My Career & Generate Roadmap",
        use_container_width=True,
    )

# ── Process Submission ────────────────────────────────────────────────────────
if submitted:
    # Resolve career goal
    final_goal = custom_goal.strip() if career_goal_select == "Custom..." else career_goal_select
    if custom_goal.strip():
        final_goal = custom_goal.strip()

    if not final_goal:
        st.error("Please select or enter a career goal.")
        st.stop()
    if not experience.strip():
        st.error("Please describe your current experience.")
        st.stop()

    # Update name
    if user_name.strip():
        orch.memory.update_name(user_name.strip())
    if notes.strip():
        orch.memory.save_note(notes.strip())

    with st.spinner("🤖 Analyzing your career profile... This may take 30-60 seconds."):
        try:
            pdf_bytes = uploaded_file.read() if uploaded_file else None
            results = orch.run_career_analysis(
                career_goal=final_goal,
                experience=experience,
                pdf_bytes=pdf_bytes,
            )
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    report = results["report"]
    roadmap = results["roadmap"]
    resume_analysis = results.get("resume_analysis")

    st.success("✅ Analysis complete! Here's your personalized career report.")

    # ── Resume Extraction Results ─────────────────────────────────────────
    if resume_analysis:
        with st.expander("📄 Resume Analysis", expanded=True):
            r1, r2, r3 = st.columns(3)
            with r1:
                st.markdown("**🔧 Extracted Skills**")
                for skill in resume_analysis.skills[:10]:
                    st.markdown(f"• {skill}")
            with r2:
                st.markdown("**📚 Education**")
                for edu in resume_analysis.education[:5]:
                    st.markdown(f"• {edu}")
                st.markdown("**🏆 Certifications**")
                for cert in resume_analysis.certifications[:5]:
                    st.markdown(f"• {cert}")
            with r3:
                st.markdown("**💼 Experience**")
                st.markdown(f"~{resume_analysis.experience_years or '?'} years")
                st.markdown(resume_analysis.experience_summary)

    # ── Career Report ─────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"""
    <h2 style="font-size:1.5rem; font-weight:700;">📋 Career Analysis: {report.career_goal}</h2>
    <p style="color:#94a3b8; margin-bottom:1.5rem;">{report.summary}</p>
    """, unsafe_allow_html=True)

    # Readiness Gauge
    col_gauge, col_skills = st.columns([1, 2])
    with col_gauge:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=report.readiness_percentage,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Career Readiness", "font": {"color": "#94a3b8", "size": 14}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#64748b"},
                "bar": {"color": "#6366f1"},
                "bgcolor": "#1a2332",
                "bordercolor": "#1e293b",
                "steps": [
                    {"range": [0, 40], "color": "rgba(239,68,68,0.2)"},
                    {"range": [40, 70], "color": "rgba(245,158,11,0.2)"},
                    {"range": [70, 100], "color": "rgba(16,185,129,0.2)"},
                ],
                "threshold": {
                    "line": {"color": "#10b981", "width": 2},
                    "thickness": 0.75,
                    "value": report.readiness_percentage,
                },
            },
        ))
        fig_gauge.update_layout(**PLOT_LAYOUT, height=220)
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

    with col_skills:
        skill_tab1, skill_tab2 = st.tabs(["✅ Current Skills", "🎯 Missing Skills"])
        with skill_tab1:
            cols = st.columns(2)
            for i, skill in enumerate(report.current_skills):
                with cols[i % 2]:
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0;
                         border-bottom:1px solid #1e293b;">
                        <span style="color:#10b981;">✅</span>
                        <span style="font-size:0.875rem;">{skill}</span>
                    </div>""", unsafe_allow_html=True)
        with skill_tab2:
            cols = st.columns(2)
            for i, skill in enumerate(report.missing_skills):
                with cols[i % 2]:
                    st.markdown(f"""
                    <div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0;
                         border-bottom:1px solid #1e293b;">
                        <span style="color:#ef4444;">❌</span>
                        <span style="font-size:0.875rem;">{skill}</span>
                    </div>""", unsafe_allow_html=True)

    # Recommended Projects
    st.markdown("#### 🚀 Recommended Projects")
    proj_cols = st.columns(min(len(report.recommended_projects), 3))
    for i, project in enumerate(report.recommended_projects[:3]):
        with proj_cols[i]:
            st.markdown(f"""
            <div class="cp-card">
                <div style="font-size:1.5rem; margin-bottom:0.5rem;">💡</div>
                <div style="font-size:0.875rem; color:#f1f5f9;">{project}</div>
            </div>""", unsafe_allow_html=True)

    # ── Roadmap Preview ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 🗺️ Your Personalized Roadmap")
    st.markdown(f"<p style='color:#94a3b8;'>{roadmap.summary}</p>", unsafe_allow_html=True)

    roadmap_items = orch._db.get_roadmap(orch._user_id)
    if roadmap_items:
        # Timeline display
        for item in roadmap_items:
            status_color = {"completed": "#10b981", "in_progress": "#f59e0b", "pending": "#6366f1"}.get(item.status, "#6366f1")
            st.markdown(f"""
            <div style="display:flex; gap:1rem; padding:0.75rem; margin-bottom:0.5rem;
                 background:#1a2332; border-radius:10px; border-left:3px solid {status_color};">
                <div style="font-size:1.1rem; font-weight:800; color:{status_color}; min-width:70px;">
                    Month {item.month}
                </div>
                <div>
                    <div style="font-weight:600;">{item.topic}</div>
                    <div style="font-size:0.8rem; color:#64748b; margin-top:0.15rem;">{item.description or ''}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📚 Start Learning →", use_container_width=True):
            st.switch_page("pages/3_Learning.py")
    with c2:
        if st.button("📊 View Dashboard →", use_container_width=True):
            st.switch_page("pages/1_Dashboard.py")

# ── If no analysis done yet, show user's current profile ─────────────────────
else:
    user_profile = orch.get_user()
    if user_profile.career_goal:
        st.markdown("---")
        st.markdown(f"""
        <div class="cp-card">
            <h3 style="margin:0 0 0.75rem 0;">📋 Your Current Profile</h3>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1rem;">
                <div>
                    <div style="font-size:0.75rem; color:#6366f1; font-weight:600; text-transform:uppercase;">Career Goal</div>
                    <div style="font-weight:600; margin-top:0.25rem;">{user_profile.career_goal}</div>
                </div>
                <div>
                    <div style="font-size:0.75rem; color:#6366f1; font-weight:600; text-transform:uppercase;">Streak</div>
                    <div style="font-weight:600; margin-top:0.25rem;">🔥 {user_profile.learning_streak} days</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
