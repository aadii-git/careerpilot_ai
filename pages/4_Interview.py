"""
CareerPilot AI — Interview Practice Page

Conducts realistic mock interviews with AI question generation,
answer evaluation, scoring, and coaching feedback.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import plotly.graph_objects as go
from app import init_session_state, get_orchestrator, render_sidebar
from config import INTERVIEW_TYPES, INTERVIEW_SCORE_CATEGORIES

# ── Page Setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Interview Practice — CareerPilot AI", page_icon="🎤", layout="wide")
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
    st.error("⚠️ Could not connect to AI. Please check your GEMINI_API_KEY in `.env`.")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style="font-size:2rem; font-weight:800; margin-bottom:0.25rem;">🎤 Interview Practice</h1>
<p style="color:#64748b; margin-bottom:1.5rem;">
    Practice with an AI interviewer. Get scored on Communication, Technical Knowledge, Confidence & Problem Solving.
</p>
""", unsafe_allow_html=True)

# ── Interview Type Selection ──────────────────────────────────────────────────
col_type, col_tips = st.columns([2, 1])

with col_type:
    interview_type = st.selectbox(
        "🎯 Interview Type",
        INTERVIEW_TYPES,
        key="interview_type_select",
    )

with col_tips:
    if st.button("💡 Get Tips for This Type", use_container_width=True):
        with st.spinner("Loading tips..."):
            try:
                ctx = orch.get_context()
                tips = orch.interview.get_interview_tips(
                    interview_type=interview_type,
                    career_goal=ctx["career_goal"],
                )
                st.session_state[f"tips_{interview_type}"] = tips
            except Exception as e:
                st.error(f"Failed: {e}")

if f"tips_{interview_type}" in st.session_state:
    with st.expander(f"💡 Tips for {interview_type} Interview", expanded=True):
        st.markdown(st.session_state[f"tips_{interview_type}"])

st.markdown("---")

# ── Session Control ───────────────────────────────────────────────────────────
session_key = f"interview_session_{interview_type}"
if session_key not in st.session_state:
    st.session_state[session_key] = {
        "active": False,
        "questions_asked": [],
        "qa_history": [],  # [{question, answer, evaluation}]
        "opening": None,
        "current_question": None,
        "current_evaluation": None,
        "answer_submitted": False,
    }

session = st.session_state[session_key]

col_start, col_end = st.columns(2)
with col_start:
    if not session["active"]:
        if st.button(f"🚀 Start {interview_type} Interview", use_container_width=True):
            with st.spinner("Setting up your interview..."):
                try:
                    opening = orch.get_interview_opening(interview_type)
                    session["active"] = True
                    session["opening"] = opening
                    session["questions_asked"] = []
                    session["qa_history"] = []
                    session["current_question"] = None
                    session["answer_submitted"] = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start: {e}")

with col_end:
    if session["active"]:
        if st.button("🏁 End Session & See Results", use_container_width=True, type="secondary"):
            session["active"] = False
            st.rerun()

# ── Active Interview ──────────────────────────────────────────────────────────
if session["active"]:
    # Opening message
    if session["opening"]:
        st.markdown(f"""
        <div style="background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.3);
             border-radius:12px; padding:1rem 1.25rem; margin-bottom:1.5rem;">
            <strong>🤖 AI Interviewer:</strong><br>
            <span style="color:#94a3b8;">{session["opening"]}</span>
        </div>
        """, unsafe_allow_html=True)

    # Q&A History
    for qa in session["qa_history"]:
        st.markdown(f"""
        <div style="background:#1a2332; border-radius:12px; padding:1rem; margin-bottom:0.75rem;
             border-left:3px solid #6366f1;">
            <div style="font-size:0.75rem; color:#6366f1; font-weight:600; margin-bottom:0.4rem;">
                QUESTION {qa["num"]} — {interview_type.upper()}
            </div>
            <div style="font-weight:600; margin-bottom:0.5rem;">{qa["question"]}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="chat-user">
            <strong>Your Answer:</strong><br>
            {qa["answer"]}
        </div>
        """, unsafe_allow_html=True)

        if "evaluation" in qa and qa["evaluation"]:
            ev = qa["evaluation"]
            overall = ev.overall_score
            color = "#10b981" if overall >= 7 else ("#f59e0b" if overall >= 5 else "#ef4444")
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.05); border:1px solid rgba(16,185,129,0.2);
                 border-radius:10px; padding:1rem; margin:0.5rem 0 1rem 0;">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.75rem;">
                    <strong>📊 Score: <span style="color:{color};">{overall:.1f}/10</span></strong>
                    <div style="display:flex; gap:0.5rem;">
                        <span style="font-size:0.75rem; color:#94a3b8;">
                            💬 {ev.communication:.1f} | 🔧 {ev.technical_knowledge:.1f} |
                            😎 {ev.confidence:.1f} | 🧩 {ev.problem_solving:.1f}
                        </span>
                    </div>
                </div>
                <p style="color:#94a3b8; font-size:0.875rem; margin:0;">{ev.feedback[:300]}...</p>
            </div>
            """, unsafe_allow_html=True)

    # Current Question
    q_num = len(session["qa_history"]) + 1

    if not session["current_question"]:
        if st.button(f"➡️ Get Question #{q_num}", use_container_width=True):
            with st.spinner("Generating question..."):
                try:
                    q_data = orch.get_interview_question(
                        interview_type=interview_type,
                        previous_questions=session["questions_asked"],
                    )
                    session["current_question"] = q_data
                    session["answer_submitted"] = False
                    session["current_evaluation"] = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")
    else:
        q_data = session["current_question"]
        st.markdown(f"""
        <div style="background:#1a2332; border-radius:12px; padding:1.25rem; margin-bottom:1rem;
             border-left:3px solid #6366f1; border-top:1px solid #1e293b;">
            <div style="font-size:0.75rem; color:#6366f1; font-weight:600; margin-bottom:0.5rem;">
                QUESTION {q_num} — {interview_type.upper()} ⏱️ {q_data.get("time_limit_minutes", 5)} min
            </div>
            <div style="font-size:1.05rem; font-weight:600; line-height:1.6;">
                {q_data.get("question", "")}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if not session["answer_submitted"]:
            with st.form(f"answer_form_{q_num}"):
                answer = st.text_area(
                    "Your Answer",
                    placeholder="Type your answer here... Take your time, there's no rush.",
                    height=150,
                    key=f"answer_{q_num}",
                )
                submit_cols = st.columns(2)
                with submit_cols[0]:
                    submitted_answer = st.form_submit_button("✅ Submit Answer", use_container_width=True)
                with submit_cols[1]:
                    skip = st.form_submit_button("⏭️ Skip Question", use_container_width=True)

            if submitted_answer and answer.strip():
                with st.spinner("🤖 Evaluating your answer..."):
                    try:
                        evaluation = orch.evaluate_interview_answer(
                            interview_type=interview_type,
                            question=q_data["question"],
                            answer=answer,
                        )
                        session["qa_history"].append({
                            "num": q_num,
                            "question": q_data["question"],
                            "answer": answer,
                            "evaluation": evaluation,
                        })
                        session["questions_asked"].append(q_data["question"])
                        session["current_question"] = None
                        session["answer_submitted"] = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Evaluation failed: {e}")

            if skip:
                session["questions_asked"].append(q_data["question"])
                session["current_question"] = None
                session["answer_submitted"] = False
                st.rerun()

        # Sample Answer Reveal
        if session["answer_submitted"] or session["qa_history"]:
            with st.expander("👁️ See Model Answer"):
                with st.spinner("Generating sample answer..."):
                    sample = orch.get_sample_answer(
                        question=q_data["question"],
                        interview_type=interview_type,
                    )
                    st.markdown(sample)

# ── Session Results ───────────────────────────────────────────────────────────
elif session["qa_history"]:
    st.markdown("### 📊 Session Results")

    scores = {
        "Communication": [],
        "Technical Knowledge": [],
        "Confidence": [],
        "Problem Solving": [],
        "Overall": [],
    }

    for qa in session["qa_history"]:
        if "evaluation" in qa and qa["evaluation"]:
            ev = qa["evaluation"]
            scores["Communication"].append(ev.communication)
            scores["Technical Knowledge"].append(ev.technical_knowledge)
            scores["Confidence"].append(ev.confidence)
            scores["Problem Solving"].append(ev.problem_solving)
            scores["Overall"].append(ev.overall_score)

    if scores["Overall"]:
        avg_scores = {k: round(sum(v) / len(v), 1) for k, v in scores.items() if v}

        # Score Cards
        s1, s2, s3, s4, s5 = st.columns(5)
        cols = [s1, s2, s3, s4, s5]
        for i, (label, score) in enumerate(avg_scores.items()):
            with cols[i]:
                color = "#10b981" if score >= 7 else ("#f59e0b" if score >= 5 else "#ef4444")
                st.markdown(f"""
                <div style="text-align:center; background:#1a2332; border-radius:12px; padding:1rem;
                     border:1px solid #1e293b;">
                    <div style="font-size:1.75rem; font-weight:800; color:{color};">{score}</div>
                    <div style="font-size:0.75rem; color:#94a3b8; margin-top:0.25rem;">{label}</div>
                </div>""", unsafe_allow_html=True)

        # Radar Chart
        st.markdown("<br>", unsafe_allow_html=True)
        categories = ["Communication", "Technical Knowledge", "Confidence", "Problem Solving"]
        values = [avg_scores.get(c, 0) for c in categories]

        fig = go.Figure(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor="rgba(99,102,241,0.2)",
            line=dict(color="#6366f1", width=2),
            marker=dict(size=8, color="#6366f1"),
        ))
        fig.update_layout(
            **PLOT_LAYOUT,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 10], gridcolor="#1e293b", color="#64748b"),
                angularaxis=dict(gridcolor="#1e293b", color="#94a3b8"),
            ),
            title=dict(text="Interview Performance", font=dict(color="#f1f5f9")),
            showlegend=False,
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Detailed feedback per question
    with st.expander("📋 Detailed Q&A Review"):
        for qa in session["qa_history"]:
            st.markdown(f"**Q: {qa['question']}**")
            st.markdown(f"*A: {qa['answer'][:200]}...*" if len(qa['answer']) > 200 else f"*A: {qa['answer']}*")
            if "evaluation" in qa and qa["evaluation"]:
                ev = qa["evaluation"]
                st.markdown(f"**Score:** {ev.overall_score:.1f}/10 | **Feedback:** {ev.feedback[:200]}")
                if ev.improvements:
                    st.markdown(f"**Improve:** {', '.join(ev.improvements[:2])}")
            st.markdown("---")

    if st.button("🔄 Start New Session", use_container_width=True):
        st.session_state[session_key] = {
            "active": False,
            "questions_asked": [],
            "qa_history": [],
            "opening": None,
            "current_question": None,
            "current_evaluation": None,
            "answer_submitted": False,
        }
        st.rerun()
