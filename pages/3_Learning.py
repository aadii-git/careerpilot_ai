"""
CareerPilot AI — Learning Page

Interactive lesson delivery with 8 stages, live Q&A with the AI tutor,
quiz integration, and progress tracking.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from app import init_session_state, get_orchestrator, render_sidebar
from config import LESSON_STAGES, DIFFICULTY_LEVELS, QUIZ_QUESTION_TYPES

# ── Page Setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Learning — CareerPilot AI", page_icon="📚", layout="wide")
init_session_state()
render_sidebar()

orch = get_orchestrator()
if not orch:
    st.error("⚠️ Could not connect to AI. Please check your GEMINI_API_KEY in `.env`.")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style="font-size:2rem; font-weight:800; margin-bottom:0.25rem;">📚 Learning Studio</h1>
<p style="color:#64748b; margin-bottom:1.5rem;">
    Your AI tutor teaches through structured, interactive lessons. Learn at your own pace.
</p>
""", unsafe_allow_html=True)

# ── Topic Selection ────────────────────────────────────────────────────────────
ctx = orch.get_context()
roadmap_topics = ctx.get("roadmap_topics", [])
completed_lessons = ctx.get("completed_lessons", [])

col_topic, col_settings = st.columns([2, 1])

with col_topic:
    if roadmap_topics:
        topic_options = roadmap_topics
        default_idx = 0
        # Try to suggest the current in-progress topic
        current_roadmap_item = orch.roadmap.get_current_topic(orch._user_id)
        if current_roadmap_item and current_roadmap_item.topic in topic_options:
            default_idx = topic_options.index(current_roadmap_item.topic)
        selected_topic = st.selectbox(
            "📖 Select a Topic to Study",
            topic_options,
            index=default_idx,
        )
    else:
        selected_topic = st.text_input(
            "📖 Enter a Topic to Study",
            placeholder="e.g., Python Decorators, Neural Networks, Docker",
        )
        if not selected_topic:
            st.info("💡 Complete your Career Assessment first to get a personalized topic list.")

with col_settings:
    user_level = st.selectbox(
        "🎓 Your Level",
        ["Beginner", "Intermediate", "Advanced"],
        index=1,
    )

if not selected_topic:
    st.stop()

# ── Stage Progress Bar ────────────────────────────────────────────────────────
progress_dict = orch.get_lesson_progress(selected_topic)
completed_stages = [s for s, done in progress_dict.items() if done]
completion_pct = len(completed_stages) / len(LESSON_STAGES)

st.markdown(f"""
<div style="margin:1rem 0; background:#1a2332; border-radius:12px; padding:1rem 1.25rem;">
    <div style="display:flex; justify-content:space-between; margin-bottom:0.75rem;">
        <span style="font-weight:600; font-size:0.9rem;">📖 {selected_topic}</span>
        <span style="color:#6366f1; font-weight:600;">{len(completed_stages)}/{len(LESSON_STAGES)} stages</span>
    </div>
    <div style="background:#0a0e1a; border-radius:6px; height:8px; overflow:hidden;">
        <div style="height:100%; width:{completion_pct*100:.0f}%;
             background:linear-gradient(90deg,#6366f1,#8b5cf6); border-radius:6px;
             transition:width 0.5s ease;"></div>
    </div>
    <div style="display:flex; gap:0.5rem; margin-top:0.75rem; flex-wrap:wrap;">
""" + "".join([
    f'<span style="font-size:0.7rem; padding:0.2rem 0.6rem; border-radius:20px; '
    f'background:{"rgba(99,102,241,0.2)" if s in completed_stages else "#1e293b"}; '
    f'color:{"#a5b4fc" if s in completed_stages else "#64748b"}; font-weight:500;">'
    f'{"✓ " if s in completed_stages else ""}{s}</span>'
    for s in LESSON_STAGES
]) + """
    </div>
</div>
""", unsafe_allow_html=True)

# ── Stage Selector ────────────────────────────────────────────────────────────
current_stage_auto = orch.learning.get_current_stage(orch._user_id, selected_topic)
stage_idx = LESSON_STAGES.index(current_stage_auto) if current_stage_auto in LESSON_STAGES else 0
selected_stage = st.selectbox(
    "📌 Lesson Stage",
    LESSON_STAGES,
    index=stage_idx,
    format_func=lambda s: f"{'✅ ' if s in completed_stages else '📍 '}{s}",
)

st.markdown("<br>", unsafe_allow_html=True)

# ── Lesson Tabs ───────────────────────────────────────────────────────────────
tab_lesson, tab_chat, tab_quiz = st.tabs(["📖 Lesson Content", "💬 Ask the Tutor", "🧠 Quiz"])

# ── TAB 1: Lesson Content ─────────────────────────────────────────────────────
with tab_lesson:
    generate_col, action_col = st.columns([3, 1])
    with generate_col:
        generate_btn = st.button(
            f"🎓 Generate: {selected_stage}",
            use_container_width=True,
            key="gen_lesson",
        )
    with action_col:
        mark_done_btn = st.button(
            "✅ Mark Complete",
            use_container_width=True,
            key="mark_done",
        )

    if mark_done_btn:
        orch.complete_lesson_stage(selected_topic, selected_stage)
        st.success(f"✅ '{selected_stage}' marked as complete!")
        st.rerun()

    if generate_btn:
        with st.spinner(f"✨ Generating {selected_stage} for {selected_topic}..."):
            try:
                content = orch.start_lesson(
                    topic=selected_topic,
                    stage=selected_stage,
                    user_level=user_level.lower(),
                )
                st.session_state[f"lesson_content_{selected_topic}_{selected_stage}"] = content
            except Exception as e:
                st.error(f"Failed to generate lesson: {e}")

    # Display content
    content_key = f"lesson_content_{selected_topic}_{selected_stage}"
    if content_key in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state[content_key])

        # Auto-complete if content generated
        if mark_done_btn or (generate_btn and content_key in st.session_state):
            pass
    else:
        st.markdown("""
        <div style="text-align:center; padding:3rem; background:#1a2332; border-radius:16px;
             border:1px dashed #334155;">
            <div style="font-size:3rem; margin-bottom:1rem;">📖</div>
            <h3 style="color:#94a3b8; font-weight:600;">Click "Generate" to start this lesson stage</h3>
            <p style="color:#64748b;">
                The AI tutor will create personalized content just for you.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ── TAB 2: Ask the Tutor ──────────────────────────────────────────────────────
with tab_chat:
    # Display chat history
    chat_key = f"lesson_chat_{selected_topic}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    history = st.session_state[chat_key]

    if history:
        for msg in history:
            if msg["role"] == "user":
                st.markdown(f"""
                <div class="chat-user">
                    <strong>You</strong><br>{msg["content"]}
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-ai">
                    <strong>🤖 AI Tutor</strong><br>{msg["content"]}
                </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding:2rem; color:#64748b;">
            <div style="font-size:2rem; margin-bottom:0.5rem;">💬</div>
            Ask the AI tutor anything about <strong>{}</strong>!
        </div>
        """.format(selected_topic), unsafe_allow_html=True)

    # Input
    with st.form("tutor_chat_form", clear_on_submit=True):
        user_q = st.text_input(
            "Ask a question...",
            placeholder=f"e.g., Can you explain {selected_topic} with a different example?",
            label_visibility="collapsed",
        )
        send = st.form_submit_button("Send 📨", use_container_width=True)

    if send and user_q.strip():
        with st.spinner("🤔 Thinking..."):
            try:
                # Convert history format for Gemini
                gemini_history = [
                    {"role": "user" if m["role"] == "user" else "model", "content": m["content"]}
                    for m in history[-10:]
                ]
                response = orch.chat_with_tutor(
                    topic=selected_topic,
                    stage=selected_stage,
                    user_message=user_q,
                    history=gemini_history,
                    user_level=user_level.lower(),
                )
                history.append({"role": "user", "content": user_q})
                history.append({"role": "model", "content": response})
                st.session_state[chat_key] = history
                st.rerun()
            except Exception as e:
                st.error(f"Chat failed: {e}")

    if history:
        if st.button("🗑️ Clear Chat", key="clear_chat"):
            st.session_state[chat_key] = []
            st.rerun()

# ── TAB 3: Quiz ───────────────────────────────────────────────────────────────
with tab_quiz:
    q_col, settings_col = st.columns([3, 1])
    with settings_col:
        q_type = st.selectbox("Question Type", QUIZ_QUESTION_TYPES, key="q_type_select")
        q_diff = st.selectbox("Difficulty", DIFFICULTY_LEVELS, index=1, key="q_diff_select")

    with q_col:
        gen_q_btn = st.button("🎲 Generate Quiz Question", use_container_width=True, key="gen_quiz")

    if gen_q_btn:
        with st.spinner("🧠 Generating question..."):
            try:
                question = orch.generate_quiz_question(selected_topic, q_type, q_diff)
                st.session_state.quiz_question = question
                st.session_state.quiz_answer_submitted = False
                st.session_state.quiz_evaluation = None
            except Exception as e:
                st.error(f"Failed to generate question: {e}")

    if st.session_state.get("quiz_question"):
        q = st.session_state.quiz_question
        st.markdown("---")
        st.markdown(f"""
        <div style="background:#1a2332; border-radius:12px; padding:1.25rem; margin-bottom:1rem;
             border-left:3px solid #6366f1;">
            <div style="font-size:0.75rem; color:#6366f1; font-weight:600; margin-bottom:0.5rem;">
                {q.difficulty.upper()} — {q.question_type}
            </div>
            <div style="font-size:1rem; font-weight:500; line-height:1.6;">{q.question}</div>
        </div>
        """, unsafe_allow_html=True)

        if q.options and q.question_type == "MCQ":
            user_answer = st.radio(
                "Choose your answer:",
                q.options,
                key="mcq_answer",
                disabled=st.session_state.quiz_answer_submitted,
            )
        else:
            user_answer = st.text_area(
                "Your Answer:",
                key="open_answer",
                height=120,
                disabled=st.session_state.quiz_answer_submitted,
            )

        if not st.session_state.quiz_answer_submitted:
            if st.button("✅ Submit Answer", use_container_width=True, key="submit_quiz"):
                if not user_answer or not str(user_answer).strip():
                    st.warning("Please provide an answer.")
                else:
                    with st.spinner("Evaluating..."):
                        try:
                            evaluation = orch.evaluate_quiz_answer(
                                topic=selected_topic,
                                question=q,
                                user_answer=str(user_answer),
                            )
                            st.session_state.quiz_evaluation = evaluation
                            st.session_state.quiz_answer_submitted = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Evaluation failed: {e}")

        if st.session_state.get("quiz_evaluation"):
            ev = st.session_state.quiz_evaluation
            score_color = "#10b981" if ev.score >= 70 else ("#f59e0b" if ev.score >= 40 else "#ef4444")
            result_emoji = "🌟" if ev.is_correct else "❌"

            st.markdown(f"""
            <div style="background:rgba({'16,185,129' if ev.is_correct else '239,68,68'},0.1);
                 border:1px solid rgba({'16,185,129' if ev.is_correct else '239,68,68'},0.3);
                 border-radius:12px; padding:1.25rem; margin-top:1rem;">
                <div style="display:flex; align-items:center; gap:1rem; margin-bottom:0.75rem;">
                    <span style="font-size:2rem;">{result_emoji}</span>
                    <div>
                        <div style="font-size:1.5rem; font-weight:800; color:{score_color};">
                            {ev.score:.0f}/100
                        </div>
                        <div style="color:#94a3b8; font-size:0.875rem;">
                            {"Correct!" if ev.is_correct else "Incorrect"}
                        </div>
                    </div>
                </div>
                <p style="color:#94a3b8; margin:0 0 0.5rem 0;"><strong>Feedback:</strong> {ev.feedback}</p>
                <p style="color:#64748b; margin:0; font-size:0.875rem;">
                    <strong>Correct Answer:</strong> {ev.correct_answer}
                </p>
                <p style="color:#64748b; margin:0.5rem 0 0 0; font-size:0.875rem;">
                    <strong>Explanation:</strong> {ev.explanation}
                </p>
            </div>
            """, unsafe_allow_html=True)

# ── Next Lesson Recommendation ────────────────────────────────────────────────
st.markdown("---")
with st.expander("🎯 What Should I Study Next?"):
    if st.button("Get AI Recommendation", key="get_rec"):
        with st.spinner("Thinking..."):
            try:
                rec = orch.get_next_topic_recommendation()
                st.markdown(f"""
                **Next Topic:** `{rec.get('next_topic', 'N/A')}`

                **Why:** {rec.get('reason', '')}

                **Estimated Time:** ~{rec.get('estimated_hours', '?')} hours

                **Prerequisites:** {rec.get('prerequisite_check', 'None')}
                """)
            except Exception as e:
                st.error(f"Failed: {e}")
