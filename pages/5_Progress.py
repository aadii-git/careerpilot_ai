"""
CareerPilot AI — Progress Tracking Page

Rich analytics dashboard with Plotly charts:
- Quiz scores over time
- Interview scores over time
- Skill mastery heatmap
- Roadmap progress
- Learning streak calendar
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
from config import DB_PATH
from database.sqlite import DatabaseManager
from services.progress_service import ProgressService

# ── Page Setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Progress — CareerPilot AI", page_icon="📈", layout="wide")
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

# ── Load Data ─────────────────────────────────────────────────────────────────
_db = DatabaseManager(DB_PATH)
_ps = ProgressService(_db)
user_id = orch._user_id
ctx = orch.get_context()
summary = _ps.get_full_summary(user_id)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style="font-size:2rem; font-weight:800; margin-bottom:0.25rem;">📈 Progress Tracker</h1>
<p style="color:#64748b; margin-bottom:1.5rem;">
    Your complete learning journey — scores, streaks, skill mastery, and roadmap completion.
</p>
""", unsafe_allow_html=True)

# ── Top Summary Metrics ────────────────────────────────────────────────────────
m1, m2, m3, m4, m5, m6 = st.columns(6)
with m1:
    st.metric("🔥 Streak", f"{summary['streak']} days")
with m2:
    st.metric("✅ Lessons", summary.get("completed_lessons", 0))
with m3:
    st.metric("🧠 Avg Quiz", f"{summary.get('average_quiz_score', 0):.1f}%")
with m4:
    st.metric("🎤 Avg Interview", f"{summary.get('average_interview_score', 0):.1f}/10")
with m5:
    st.metric("🗺️ Roadmap", f"{summary.get('roadmap_percentage', 0):.0f}%")
with m6:
    st.metric("📝 Quiz Attempts", summary.get("total_quiz_attempts", 0))

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🧠 Quiz Performance",
    "🎤 Interview Scores",
    "🔬 Skill Mastery",
    "🗺️ Roadmap",
])

# ── TAB 1: Quiz Performance ───────────────────────────────────────────────────
with tab1:
    quiz_df = _ps.get_quiz_score_over_time(user_id)

    if quiz_df.empty:
        st.markdown("""
        <div style="text-align:center; padding:3rem; background:#1a2332; border-radius:16px;">
            <div style="font-size:3rem; margin-bottom:1rem;">🧠</div>
            <h3 style="color:#94a3b8;">No quiz data yet</h3>
            <p style="color:#64748b;">Complete some quizzes in the Learning section to see your progress.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Line chart: scores over time
        fig_quiz = go.Figure()
        topics = quiz_df["topic"].unique()
        colors = px.colors.qualitative.Set2

        for i, topic in enumerate(topics):
            topic_df = quiz_df[quiz_df["topic"] == topic].sort_values("date")
            fig_quiz.add_trace(go.Scatter(
                x=topic_df["date"],
                y=topic_df["score"],
                mode="lines+markers",
                name=topic,
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=7),
                hovertemplate=f"<b>{topic}</b><br>Date: %{{x}}<br>Score: %{{y:.1f}}%<extra></extra>",
            ))

        fig_quiz.add_hline(y=60, line_dash="dot", line_color="#ef4444",
                           annotation_text="Pass threshold (60%)", annotation_position="right")
        fig_quiz.add_hline(y=80, line_dash="dot", line_color="#10b981",
                           annotation_text="Mastery (80%)", annotation_position="right")

        fig_quiz.update_layout(
            **PLOT_LAYOUT,
            title=dict(text="Quiz Scores Over Time", font=dict(color="#f1f5f9", size=16)),
            xaxis=dict(title="Date", gridcolor="#1e293b"),
            yaxis=dict(title="Score (%)", range=[0, 105], gridcolor="#1e293b"),
            legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1e293b"),
            height=350,
        )
        st.plotly_chart(fig_quiz, use_container_width=True, config={"displayModeBar": False})

        # Per-topic breakdown
        col_breakdown, col_diff = st.columns(2)

        with col_breakdown:
            # Bar chart: avg score per topic
            topic_avgs = quiz_df.groupby("topic")["score"].mean().reset_index()
            topic_avgs.columns = ["topic", "avg_score"]
            topic_avgs = topic_avgs.sort_values("avg_score", ascending=True)

            fig_bar = go.Figure(go.Bar(
                x=topic_avgs["avg_score"],
                y=topic_avgs["topic"],
                orientation="h",
                marker=dict(
                    color=topic_avgs["avg_score"],
                    colorscale=[[0, "#ef4444"], [0.6, "#f59e0b"], [1, "#10b981"]],
                    showscale=False,
                ),
                hovertemplate="<b>%{y}</b>: %{x:.1f}%<extra></extra>",
            ))
            fig_bar.update_layout(
                **PLOT_LAYOUT,
                title=dict(text="Average Score by Topic", font=dict(color="#f1f5f9")),
                xaxis=dict(title="Avg Score (%)", range=[0, 105], gridcolor="#1e293b"),
                yaxis=dict(gridcolor="#1e293b"),
                height=300,
            )
            st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

        with col_diff:
            # Pie chart: difficulty distribution
            diff_counts = quiz_df["difficulty"].value_counts().reset_index()
            diff_counts.columns = ["difficulty", "count"]
            fig_pie = go.Figure(go.Pie(
                labels=diff_counts["difficulty"],
                values=diff_counts["count"],
                hole=0.5,
                marker=dict(colors=["#10b981", "#f59e0b", "#ef4444"]),
                textfont=dict(color="#f1f5f9"),
            ))
            fig_pie.update_layout(
                **PLOT_LAYOUT,
                title=dict(text="Questions by Difficulty", font=dict(color="#f1f5f9")),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                height=300,
            )
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

# ── TAB 2: Interview Scores ───────────────────────────────────────────────────
with tab2:
    interview_df = _ps.get_interview_scores_over_time(user_id)

    if interview_df.empty:
        st.markdown("""
        <div style="text-align:center; padding:3rem; background:#1a2332; border-radius:16px;">
            <div style="font-size:3rem; margin-bottom:1rem;">🎤</div>
            <h3 style="color:#94a3b8;">No interview data yet</h3>
            <p style="color:#64748b;">Practice mock interviews to see your improvement over time.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Overall score trend
        fig_interview = go.Figure()
        fig_interview.add_trace(go.Scatter(
            x=interview_df["date"],
            y=interview_df["overall_score"],
            mode="lines+markers",
            name="Overall Score",
            line=dict(color="#6366f1", width=3),
            marker=dict(size=8),
            fill="tozeroy",
            fillcolor="rgba(99,102,241,0.1)",
        ))

        for col, color, name in [
            ("communication", "#10b981", "Communication"),
            ("technical_knowledge", "#f59e0b", "Technical"),
            ("confidence", "#8b5cf6", "Confidence"),
            ("problem_solving", "#3b82f6", "Problem Solving"),
        ]:
            if col in interview_df.columns:
                fig_interview.add_trace(go.Scatter(
                    x=interview_df["date"],
                    y=interview_df[col],
                    mode="lines",
                    name=name,
                    line=dict(color=color, width=1.5, dash="dot"),
                    visible="legendonly",
                ))

        fig_interview.update_layout(
            **PLOT_LAYOUT,
            title=dict(text="Interview Scores Over Time", font=dict(color="#f1f5f9", size=16)),
            xaxis=dict(title="Date", gridcolor="#1e293b"),
            yaxis=dict(title="Score (/10)", range=[0, 10.5], gridcolor="#1e293b"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            height=350,
        )
        st.plotly_chart(fig_interview, use_container_width=True, config={"displayModeBar": False})

        # By interview type
        if "interview_type" in interview_df.columns:
            type_avgs = interview_df.groupby("interview_type")["overall_score"].mean().reset_index()
            fig_type = go.Figure(go.Bar(
                x=type_avgs["interview_type"],
                y=type_avgs["overall_score"],
                marker=dict(
                    color=type_avgs["overall_score"],
                    colorscale=[[0, "#ef4444"], [0.5, "#f59e0b"], [1, "#10b981"]],
                    showscale=False,
                ),
                text=type_avgs["overall_score"].round(1),
                textposition="outside",
                textfont=dict(color="#f1f5f9"),
            ))
            fig_type.update_layout(
                **PLOT_LAYOUT,
                title=dict(text="Avg Score by Interview Type", font=dict(color="#f1f5f9")),
                xaxis=dict(gridcolor="#1e293b"),
                yaxis=dict(title="Avg Score (/10)", range=[0, 11], gridcolor="#1e293b"),
                height=280,
            )
            st.plotly_chart(fig_type, use_container_width=True, config={"displayModeBar": False})

# ── TAB 3: Skill Mastery ──────────────────────────────────────────────────────
with tab3:
    mastery = _ps.get_skill_mastery(user_id)

    if not mastery:
        st.markdown("""
        <div style="text-align:center; padding:3rem; background:#1a2332; border-radius:16px;">
            <div style="font-size:3rem; margin-bottom:1rem;">🔬</div>
            <h3 style="color:#94a3b8;">No skill data yet</h3>
            <p style="color:#64748b;">Complete quizzes across different topics to build your skill profile.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Horizontal bar chart for mastery
        sorted_mastery = dict(sorted(mastery.items(), key=lambda x: x[1], reverse=True))
        topics = list(sorted_mastery.keys())
        scores = list(sorted_mastery.values())
        colors_mastery = ["#10b981" if s >= 80 else "#f59e0b" if s >= 60 else "#ef4444" for s in scores]

        col_chart, col_legend = st.columns([3, 1])
        with col_chart:
            fig_mastery = go.Figure(go.Bar(
                x=scores,
                y=topics,
                orientation="h",
                marker=dict(color=colors_mastery),
                text=[f"{s:.0f}%" for s in scores],
                textposition="outside",
                textfont=dict(color="#f1f5f9"),
                hovertemplate="<b>%{y}</b>: %{x:.1f}%<extra></extra>",
            ))
            fig_mastery.add_vline(x=60, line_dash="dot", line_color="#f59e0b",
                                  annotation_text="60% threshold")
            fig_mastery.add_vline(x=80, line_dash="dot", line_color="#10b981",
                                  annotation_text="80% mastery")
            fig_mastery.update_layout(
                **PLOT_LAYOUT,
                title=dict(text="Skill Mastery (Quiz Average)", font=dict(color="#f1f5f9", size=16)),
                xaxis=dict(title="Score (%)", range=[0, 115], gridcolor="#1e293b"),
                yaxis=dict(gridcolor="#1e293b"),
                height=max(300, len(topics) * 40),
            )
            st.plotly_chart(fig_mastery, use_container_width=True, config={"displayModeBar": False})

        with col_legend:
            st.markdown("""
            <div style="background:#1a2332; border-radius:12px; padding:1rem; margin-top:2rem;">
                <div style="margin-bottom:0.75rem;">
                    <span style="color:#10b981; font-size:1.2rem;">●</span>
                    <strong style="font-size:0.875rem;"> Mastery ≥ 80%</strong>
                </div>
                <div style="margin-bottom:0.75rem;">
                    <span style="color:#f59e0b; font-size:1.2rem;">●</span>
                    <strong style="font-size:0.875rem;"> Passing ≥ 60%</strong>
                </div>
                <div>
                    <span style="color:#ef4444; font-size:1.2rem;">●</span>
                    <strong style="font-size:0.875rem;"> Needs Work &lt; 60%</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            weak = _ps.get_weak_topics(user_id)
            strong = _ps.get_strong_topics(user_id)
            st.markdown(f"**💪 Strong ({len(strong)}):** " + ", ".join(strong[:3]) if strong else "")
            st.markdown(f"**⚠️ Focus ({len(weak)}):** " + ", ".join(weak[:3]) if weak else "")

# ── TAB 4: Roadmap Progress ───────────────────────────────────────────────────
with tab4:
    roadmap = _db.get_roadmap(user_id)

    if not roadmap:
        st.markdown("""
        <div style="text-align:center; padding:3rem; background:#1a2332; border-radius:16px;">
            <div style="font-size:3rem; margin-bottom:1rem;">🗺️</div>
            <h3 style="color:#94a3b8;">No roadmap yet</h3>
            <p style="color:#64748b;">Complete your Career Assessment to generate a learning roadmap.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        roadmap_df = _ps.get_roadmap_progress_data(roadmap)

        # Donut chart of status distribution
        col_donut, col_detail = st.columns([1, 2])
        with col_donut:
            status_counts = roadmap_df["status"].value_counts()
            fig_donut = go.Figure(go.Pie(
                labels=[s.replace("_", " ").title() for s in status_counts.index],
                values=status_counts.values,
                hole=0.6,
                marker=dict(colors=["#10b981", "#f59e0b", "#334155"]),
                textfont=dict(color="#f1f5f9"),
            ))
            total = len(roadmap)
            completed_count = sum(1 for r in roadmap if r.status == "completed")
            fig_donut.update_layout(
                **PLOT_LAYOUT,
                title=dict(text="Roadmap Status", font=dict(color="#f1f5f9")),
                annotations=[dict(
                    text=f"<b>{completed_count}/{total}</b>",
                    x=0.5, y=0.5, font_size=20, font_color="#6366f1",
                    showarrow=False,
                )],
                showlegend=True,
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                height=300,
            )
            st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

        with col_detail:
            # Month-by-month timeline
            month_fig = go.Figure()
            status_styles = {
                "completed": dict(color="#10b981", symbol="circle"),
                "in_progress": dict(color="#f59e0b", symbol="square"),
                "pending": dict(color="#334155", symbol="circle-open"),
            }
            for status, style in status_styles.items():
                mask = roadmap_df[roadmap_df["status"] == status]
                if not mask.empty:
                    month_fig.add_trace(go.Scatter(
                        x=mask["month"],
                        y=[1] * len(mask),
                        mode="markers+text",
                        marker=dict(size=20, color=style["color"], symbol=style["symbol"],
                                    line=dict(color=style["color"], width=2)),
                        text=mask["topic"],
                        textposition="top center",
                        textfont=dict(size=10, color="#94a3b8"),
                        name=status.replace("_", " ").title(),
                        hovertemplate="<b>%{text}</b><br>Month %{x}<extra></extra>",
                    ))

            month_fig.update_layout(
                **PLOT_LAYOUT,
                title=dict(text="Month-by-Month Timeline", font=dict(color="#f1f5f9")),
                xaxis=dict(title="Month", gridcolor="#1e293b", dtick=1),
                yaxis=dict(visible=False),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
                height=300,
            )
            st.plotly_chart(month_fig, use_container_width=True, config={"displayModeBar": False})

        # Detailed table
        with st.expander("📋 Full Roadmap Detail"):
            for item in roadmap:
                status_icon = {"completed": "✅", "in_progress": "⚡", "pending": "⏳"}.get(item.status, "⏳")
                status_color = {"completed": "#10b981", "in_progress": "#f59e0b", "pending": "#64748b"}.get(item.status, "#64748b")
                st.markdown(f"""
                <div style="display:flex; align-items:flex-start; gap:1rem; padding:0.75rem;
                     border-bottom:1px solid #1e293b; border-radius:8px; margin-bottom:0.25rem;">
                    <span style="font-size:1.1rem; min-width:20px;">{status_icon}</span>
                    <span style="color:#64748b; font-size:0.8rem; min-width:70px;">Month {item.month}</span>
                    <div style="flex:1;">
                        <div style="font-weight:600;">{item.topic}</div>
                        <div style="font-size:0.8rem; color:#64748b;">{item.description or ''}</div>
                    </div>
                    <span style="font-size:0.75rem; color:{status_color}; font-weight:600; white-space:nowrap;">
                        {item.status.replace("_", " ").upper()}
                    </span>
                </div>
                """, unsafe_allow_html=True)

# ── AI Progress Summary ───────────────────────────────────────────────────────
st.markdown("---")
with st.expander("🤖 Get AI Progress Summary"):
    if st.button("Generate Personalized Summary", key="gen_summary"):
        with st.spinner("Analyzing your learning journey..."):
            try:
                from utils.prompts import session_summary_prompt
                mastery_data = _ps.get_skill_mastery(user_id)
                weak = _ps.get_weak_topics(user_id)
                strong = _ps.get_strong_topics(user_id)
                completed_lessons = _db.get_completed_lessons(user_id)

                prompt = session_summary_prompt(
                    career_goal=ctx.get("career_goal", "Your career goal"),
                    completed_lessons=completed_lessons,
                    quiz_scores=mastery_data,
                    weak_topics=weak,
                    strong_topics=strong,
                )
                summary_text = orch._gemini.generate_text(prompt)
                st.markdown(f"""
                <div class="cp-card">
                    {summary_text}
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Failed to generate summary: {e}")
