"""
CareerPilot AI — Dashboard Page

Displays a comprehensive overview of the user's progress:
career goal, roadmap, streak, scores, skills, and charts.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from app import init_session_state, get_orchestrator, render_sidebar

# ── Page Setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Dashboard — CareerPilot AI", page_icon="📊", layout="wide")
init_session_state()
render_sidebar()

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#94a3b8"),
    margin=dict(l=20, r=20, t=40, b=20),
)


# ── Load Data ─────────────────────────────────────────────────────────────────
orch = get_orchestrator()
if not orch:
    st.error("⚠️ Could not connect to AI. Please check your GROQ_API_KEY in `.env`.")
    st.stop()

with st.spinner("Loading your dashboard..."):
    data = orch.get_dashboard_data()

user = orch.get_user()
roadmap = data.get("roadmap", [])
ctx = data

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:2rem;">
    <h1 style="font-size:2rem; font-weight:800; margin:0;">
        👋 Welcome back, <span style="background:linear-gradient(135deg,#6366f1,#8b5cf6);
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;">{user.name}</span>!
    </h1>
    <p style="color:#64748b; margin:0.25rem 0 0 0; font-size:0.95rem;">
        Here's your career progress at a glance.
    </p>
</div>
""", unsafe_allow_html=True)

# ── Key Metrics ────────────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    streak = ctx.get("learning_streak", 0)
    st.metric("🔥 Streak", f"{streak} days", help="Consecutive days of activity")
with m2:
    avg_q = ctx.get("average_quiz_score", 0.0)
    st.metric("🧠 Avg Quiz Score", f"{avg_q:.1f}%")
with m3:
    avg_i = ctx.get("average_interview_score", 0.0)
    st.metric("🎤 Avg Interview Score", f"{avg_i:.1f}/10")
with m4:
    completed = ctx.get("completed_lessons", 0)
    st.metric("✅ Lessons Done", completed)
with m5:
    pct = ctx.get("roadmap_percentage", 0.0)
    st.metric("🗺️ Roadmap", f"{pct:.0f}%")

st.markdown("<br>", unsafe_allow_html=True)

# ── Career Goal Banner ────────────────────────────────────────────────────────
goal = ctx.get("career_goal", "Not set yet")
st.markdown(f"""
<div class="cp-card" style="background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.1));
     border-color: rgba(99,102,241,0.4); display:flex; align-items:center; gap:1.5rem;">
    <div style="font-size:3rem;">🎯</div>
    <div>
        <div style="font-size:0.8rem; color:#6366f1; font-weight:600; text-transform:uppercase; letter-spacing:0.05em;">
            Career Goal
        </div>
        <div style="font-size:1.4rem; font-weight:700; margin:0.25rem 0;">{goal}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Roadmap Progress ──────────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("### 🗺️ Learning Roadmap")

    if roadmap:
        # Status bar chart
        months = [item.month for item in roadmap]
        topics = [item.topic for item in roadmap]
        statuses = [item.status for item in roadmap]

        color_map = {
            "completed": "#10b981",
            "in_progress": "#f59e0b",
            "pending": "#334155",
        }
        colors = [color_map.get(s, "#334155") for s in statuses]

        fig = go.Figure()
        for status, color in color_map.items():
            mask = [i for i, s in enumerate(statuses) if s == status]
            if mask:
                fig.add_trace(go.Bar(
                    x=[months[i] for i in mask],
                    y=[1] * len(mask),
                    name=status.replace("_", " ").title(),
                    marker_color=color,
                    text=[topics[i] for i in mask],
                    textposition="inside",
                    hovertemplate="<b>%{text}</b><br>Month %{x}<extra></extra>",
                ))

        fig.update_layout(
            **PLOT_LAYOUT,
            barmode="stack",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(title="Month", gridcolor="#1e293b"),
            yaxis=dict(showticklabels=False, gridcolor="#1e293b"),
            height=220,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Roadmap table
        with st.expander("📋 View Full Roadmap"):
            for item in roadmap:
                status_icon = {"completed": "✅", "in_progress": "⚡", "pending": "⏳"}.get(item.status, "⏳")
                status_color = {"completed": "#10b981", "in_progress": "#f59e0b", "pending": "#64748b"}.get(item.status, "#64748b")
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:0.75rem; padding:0.5rem 0;
                     border-bottom:1px solid #1e293b;">
                    <span style="font-size:1.2rem;">{status_icon}</span>
                    <span style="font-size:0.8rem; color:#64748b; width:60px;">Month {item.month}</span>
                    <span style="font-weight:600; flex:1;">{item.topic}</span>
                    <span style="font-size:0.75rem; color:{status_color}; font-weight:600;">
                        {item.status.replace("_", " ").upper()}
                    </span>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("🗺️ No roadmap yet. Complete your **Career Assessment** to generate one!")
        if st.button("Go to Career Assessment →"):
            st.switch_page("pages/2_Career_Assessment.py")

with col_right:
    # Skills Radar
    st.markdown("### 🔬 Skill Areas")
    mastery = ctx.get("skill_mastery", {}) if "skill_mastery" in ctx else {}

    from services.progress_service import ProgressService
    from database.sqlite import DatabaseManager
    from config import DB_PATH
    _db = DatabaseManager(DB_PATH)
    _ps = ProgressService(_db)
    mastery = _ps.get_skill_mastery(ctx.get("user_id", 1))

    if mastery:
        categories = list(mastery.keys())[:8]
        values = [mastery[c] for c in categories]

        fig_radar = go.Figure(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor="rgba(99,102,241,0.2)",
            line=dict(color="#6366f1", width=2),
            marker=dict(size=6, color="#6366f1"),
        ))
        fig_radar.update_layout(
            **PLOT_LAYOUT,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1e293b", color="#64748b"),
                angularaxis=dict(gridcolor="#1e293b", color="#94a3b8"),
            ),
            showlegend=False,
            height=280,
        )
        st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown("""
        <div class="cp-card" style="text-align:center; padding:2rem;">
            <div style="font-size:2rem;">🔬</div>
            <p style="color:#64748b; margin:0.5rem 0 0 0; font-size:0.875rem;">
                Complete quizzes to see skill mastery
            </p>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ── Bottom Row: Strong & Weak Skills ─────────────────────────────────────────
col_s, col_w = st.columns(2)

with col_s:
    st.markdown("### 💪 Strong Skills")
    strong = ctx.get("strong_topics", [])
    if strong:
        for skill in strong[:6]:
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:0.5rem; padding:0.4rem 0;">
                <span style="color:#10b981; font-size:1rem;">✅</span>
                <span style="font-size:0.9rem;">{skill}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<p style='color:#64748b; font-size:0.875rem;'>Complete your assessment to identify strengths.</p>", unsafe_allow_html=True)

with col_w:
    st.markdown("### 🎯 Areas to Improve")
    weak = ctx.get("weak_topics", [])
    if weak:
        for skill in weak[:6]:
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:0.5rem; padding:0.4rem 0;">
                <span style="color:#f59e0b; font-size:1rem;">⚠️</span>
                <span style="font-size:0.9rem;">{skill}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("<p style='color:#64748b; font-size:0.875rem;'>No weak areas identified yet. Keep learning!</p>", unsafe_allow_html=True)

# ── Quick Actions ─────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### ⚡ Quick Actions")
qa1, qa2, qa3, qa4 = st.columns(4)
with qa1:
    if st.button("📝 Continue Learning", use_container_width=True):
        st.switch_page("pages/3_Learning.py")
with qa2:
    if st.button("🎤 Practice Interview", use_container_width=True):
        st.switch_page("pages/4_Interview.py")
with qa3:
    if st.button("📈 View Progress", use_container_width=True):
        st.switch_page("pages/5_Progress.py")
with qa4:
    if st.button("🎯 Update Assessment", use_container_width=True):
        st.switch_page("pages/2_Career_Assessment.py")
