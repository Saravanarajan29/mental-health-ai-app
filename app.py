import base64
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from core.emotion_classifier import classify_emotion_fast
from core.interview import (
    INTERVIEW_QUESTION_COUNT,
    handle_user_answer,
    interview_is_complete,
    normalize_interview_state,
    start_interview,
)
from core.pdf_generator import render_pdf
from core.record_store import build_feedback_record, build_screening_record, save_feedback_record, save_screening_record
from core.report_generator import compose_report_llm
from core.safety import CRISIS_SIGNPOSTING_MESSAGE
from core.state import ensure_session_state
from forms.bcqol_form import BCQOL_QUESTIONS, compute_bcqol_result
from forms.consent_form import build_anonymous_session_id, build_default_consent_state, consent_is_complete, render_consent_form
from forms.feedback_form import render_feedback_form
from forms.mmse_form import (
    MMSE_ACCESSIBILITY_FLAGS,
    MMSE_REGISTRATION_WORDS,
    MMSE_REMOTE_DISCLAIMER,
    MMSE_RESULT_DISCLAIMER,
    MMSE_SETTING_OPTIONS,
    MMSE_SHAPE_OPTIONS,
    MMSE_WORD_OPTIONS,
    build_default_mmse_state,
    calculate_mmse_result,
)


st.set_page_config(page_title="Mental Health AI App", page_icon=":speech_balloon:", layout="wide")

ASSESSMENT_STEP_TITLES = [
    "BC-QoL Form",
    "MMSE Start Consent",
    "MMSE Orientation",
    "MMSE Registration",
    "MMSE Attention",
    "MMSE Recall",
    "MMSE Language Tasks",
    "Review and Submit",
    "Results Summary",
]

session = ensure_session_state()
normalize_interview_state(session)
session.setdefault("session_id", build_anonymous_session_id())
session.setdefault("participant_id", session["session_id"])
session.setdefault("consent", build_default_consent_state())
if session.get("consent") is None:
    session["consent"] = build_default_consent_state()
session.setdefault("bcqol_responses", [3] * len(BCQOL_QUESTIONS))
if session.get("bcqol_responses") is None:
    session["bcqol_responses"] = [3] * len(BCQOL_QUESTIONS)
session.setdefault("mmse_result", None)
session.setdefault("stage_two_assessment", None)
session.setdefault("assessment_step", 0)
session.setdefault("screening_record_saved", False)
session.setdefault("feedback_submitted", False)
session.setdefault("research_save_result", None)
session.setdefault("feedback_save_result", None)
session.setdefault("feedback_ease_of_use", 3)
session.setdefault("feedback_question_clarity", 3)
session.setdefault("feedback_report_clarity", 3)
session.setdefault("feedback_comfort", 3)
session.setdefault("feedback_trust", 3)
session.setdefault("feedback_usefulness", 3)
session.setdefault("feedback_recommend", "")
session.setdefault("feedback_open_comment", "")
session.setdefault("feedback_open_comment_redacted", "")
session.setdefault("feedback_data_confirmation", False)
session.setdefault("feedback_completed_at_utc", "")
session.setdefault("screening_completed_at_utc", "")
session.setdefault("mmse_form_state", build_default_mmse_state())
if session.get("mmse_form_state") is None:
    session["mmse_form_state"] = build_default_mmse_state()
session["mmse_form_state"]["accessibility_support_required"] = bool(
    session["consent"].get("demographics", {}).get("accessibility_support_required")
)


def _inject_responsive_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --bg: #f6f9f5;
            --bg-2: #edf6f2;
            --surface: #ffffff;
            --surface-soft: #f0f7f4;
            --ink: #122b2d;
            --muted: #617476;
            --line: #d8e6df;
            --teal: #1f8a7a;
            --teal-dark: #11645b;
            --leaf: #76b889;
            --peach: #f1b88f;
            --rose: #d97b73;
            --sun: #e5a93d;
            --sky: #75a7c8;
            --shadow: 0 18px 46px rgba(18, 43, 45, 0.12);
            --soft-shadow: 0 10px 28px rgba(18, 43, 45, 0.08);
        }

        html,
        body,
        [data-testid="stAppViewContainer"] {
            overflow-x: hidden;
            background: var(--bg);
            color: var(--ink);
            font-family: "Inter", "Aptos", "Segoe UI", system-ui, sans-serif;
        }

        [data-testid="stHeader"] {
            background: transparent;
            backdrop-filter: none;
        }

        [data-testid="stSidebar"] {
            background: #e9f3ef;
            border-right: 1px solid var(--line);
        }

        .block-container {
            width: 100%;
            max-width: 1220px;
            padding: 0 1rem 2.2rem;
        }

        h1 {
            color: var(--ink);
            font-family: "Fraunces", Georgia, serif;
            font-size: clamp(3.2rem, 8vw, 7rem);
            line-height: 0.98;
            letter-spacing: 0;
            margin: 0 0 0.45rem;
        }

        h2,
        h3,
        h4 {
            color: var(--ink);
            letter-spacing: 0;
            font-family: "Inter", "Aptos", "Segoe UI", system-ui, sans-serif;
        }

        p,
        li,
        label,
        [data-testid="stMarkdownContainer"] {
            color: var(--ink);
        }

        .stCaption,
        [data-testid="stCaptionContainer"],
        small {
            color: var(--muted) !important;
        }

        .assessment-container {
            width: 100%;
            max-width: 960px;
            margin: 0 auto;
            padding: 0 16px 10px;
        }

        .assessment-card,
        div[data-testid="stForm"],
        div[data-testid="stExpander"] {
            width: 100%;
            border-radius: 10px;
            box-sizing: border-box;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.88);
            box-shadow: var(--soft-shadow);
        }

        div[data-testid="stExpander"] {
            overflow: hidden;
        }

        div[data-testid="stExpander"] summary {
            color: var(--ink);
            font-weight: 700;
            background: rgba(240, 247, 244, 0.82);
            min-height: 46px;
        }

        [data-testid="stTabs"] [role="tablist"] {
            gap: 10px;
            border-bottom: 1px solid var(--line);
            overflow-x: auto;
            padding-top: 0.4rem;
        }

        [data-testid="stTabs"] [role="tab"] {
            border-radius: 999px;
            padding: 10px 18px;
            min-height: 44px;
            color: var(--teal-dark);
            background: rgba(255, 255, 255, 0.62);
            border: 1px solid rgba(31, 138, 122, 0.26);
        }

        [data-testid="stTabs"] [aria-selected="true"] {
            color: #ffffff;
            background: var(--teal);
            border: 1px solid var(--teal);
            font-weight: 700;
            box-shadow: var(--soft-shadow);
        }

        [data-testid="stTabs"] [aria-selected="true"] p {
            color: #ffffff !important;
        }

        [data-testid="stTabs"] [role="tab"]::after,
        [data-testid="stTabs"] [aria-selected="true"]::after {
            background-color: transparent !important;
            border-color: transparent !important;
        }

        [data-testid="stTabs"] [data-baseweb="tab-highlight"],
        [data-testid="stTabs"] [role="tablist"] > div:last-child,
        .st-ek.st-cj.st-fx.st-fy.st-fz.st-g0.st-g7.st-g2 {
            background: transparent !important;
            background-color: transparent !important;
            border-color: transparent !important;
            box-shadow: none !important;
        }

        .st-g4.st-c1.st-g1 {
            height: auto !important;
            min-height: 0 !important;
            background: transparent !important;
            background-color: transparent !important;
        }

        .flow-note {
            font-family: "Inter", "Aptos", "Segoe UI", system-ui, sans-serif;
            color: var(--ink);
        }

        .flow-note code {
            font-family: "Inter", "Aptos", "Segoe UI", system-ui, sans-serif;
            font-weight: 700;
            color: var(--teal-dark);
            background: transparent;
            padding: 0;
        }

        .app-hero {
            position: relative;
            overflow: hidden;
            border: 0;
            border-radius: 0;
            padding: 0;
            margin: -0.65rem 0 -0.35rem;
            background: transparent;
            box-shadow: none;
        }

        .hero-kicker {
            display: none;
            align-items: center;
            min-height: 32px;
            padding: 6px 12px;
            border-radius: 999px;
            background: #ffffff;
            color: var(--teal-dark);
            border: 1px solid var(--line);
            font-weight: 800;
            font-size: 0.84rem;
            margin-bottom: 16px;
        }

        .hero-copy {
            max-width: 820px;
            color: var(--muted);
            font-size: clamp(1rem, 2vw, 1.22rem);
            line-height: 1.5;
            margin: 0.45rem 0 0.42rem;
        }

        .hero-accent {
            font-family: "Inter", "Aptos", "Segoe UI", system-ui, sans-serif;
            font-weight: 800;
            color: var(--teal-dark);
            letter-spacing: 0;
            text-shadow: 0 10px 24px rgba(31, 138, 122, 0.12);
        }

        .hero-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin: 0;
        }

        .hero-chip {
            min-height: 30px;
            display: inline-flex;
            align-items: center;
            padding: 5px 10px;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.82);
            color: var(--ink);
            font-weight: 700;
            font-size: 0.82rem;
        }

        .hero-chip:nth-child(2) {
            border-color: rgba(241, 184, 143, 0.55);
            background: rgba(255, 246, 237, 0.88);
        }

        .hero-chip:nth-child(3) {
            border-color: rgba(117, 167, 200, 0.48);
            background: rgba(239, 247, 252, 0.88);
        }

        .hero-chip:nth-child(4) {
            border-color: rgba(217, 123, 115, 0.38);
            background: rgba(255, 241, 239, 0.84);
        }

        .mmse-naming-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 20px;
            margin: 1rem 0;
        }

        .object-card {
            width: 100%;
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 20px;
            box-sizing: border-box;
            background:
                linear-gradient(180deg, #ffffff, #fbfdfc);
            box-shadow: var(--shadow);
        }

        .object-card img {
            width: 100%;
            max-width: 220px;
            height: auto;
            object-fit: contain;
            display: block;
            margin: 0 auto 16px auto;
        }

        .fallback-symbol {
            min-height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 4rem;
            font-weight: 700;
            color: var(--teal-dark);
        }

        .desktop-progress {
            display: block;
            padding: 12px 14px;
            margin: 0.75rem 0;
            border: 1px solid var(--line);
            border-radius: 999px;
            color: var(--muted);
            background: rgba(255, 255, 255, 0.76);
            box-shadow: 0 8px 22px rgba(25, 50, 60, 0.06);
            font-size: 0.92rem;
            white-space: normal;
        }

        .mobile-progress {
            display: none;
        }

        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stNumberInput"] input {
            width: 100%;
            min-height: 44px;
            font-size: 16px;
            box-sizing: border-box;
            border-radius: 8px;
            border: 1px solid var(--line);
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            caret-color: #000000 !important;
            background: #ffffff !important;
            opacity: 1 !important;
        }

        div[data-testid="stTextInput"] input:disabled,
        div[data-testid="stTextInput"] input[disabled] {
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            opacity: 1 !important;
            background: var(--bg) !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus,
        div[data-testid="stNumberInput"] input:focus {
            border-color: var(--teal);
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            caret-color: #000000 !important;
            box-shadow: 0 0 0 3px rgba(33, 124, 117, 0.24);
            background: #ffffff !important;
        }

        button,
        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button,
        div[data-testid="stFormSubmitButton"] button {
            width: 100%;
            min-height: 44px;
            border-radius: 999px;
            border: 1px solid var(--teal);
            background: var(--teal);
            color: #ffffff;
            font-weight: 700;
            box-sizing: border-box;
            transition: transform 120ms ease, background 120ms ease, border-color 120ms ease;
        }

        button:hover,
        div[data-testid="stButton"] button:hover,
        div[data-testid="stDownloadButton"] button:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
            background: var(--teal-dark);
            border-color: var(--teal-dark);
            color: #ffffff;
            transform: translateY(-1px);
        }

        button:disabled,
        div[data-testid="stButton"] button:disabled {
            background: #c7d5d0;
            border-color: #c7d5d0;
            color: #6a7b82;
            transform: none;
        }

        div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-top: 5px solid var(--teal);
            border-radius: 12px;
            padding: 12px 14px;
            box-shadow: 0 8px 22px rgba(25, 50, 60, 0.06);
        }

        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] div,
        div[data-testid="stMetric"] p {
            color: #000000 !important;
        }

        .assessment-info div[data-testid="stExpander"] {
            border: 0;
            background: transparent;
            box-shadow: none;
        }

        .assessment-info div[data-testid="stExpander"] summary {
            background: transparent;
            border: 0;
            padding-left: 0;
        }

        div[data-testid="stAlert"] {
            border-radius: 10px;
            border: 1px solid var(--line);
        }

        div[data-baseweb="select"] > div {
            min-height: 44px;
            border-radius: 8px;
            border: 1px solid var(--line) !important;
            background-color: var(--bg) !important;
            color: var(--ink) !important;
            box-shadow: 0 6px 18px rgba(18, 43, 45, 0.05);
        }

        div[data-baseweb="select"] span,
        div[data-baseweb="select"] div,
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] div,
        ul[role="listbox"],
        li[role="option"] {
            color: var(--ink) !important;
            background-color: var(--bg) !important;
            opacity: 1 !important;
        }

        li[role="option"]:hover,
        li[aria-selected="true"] {
            background-color: var(--teal-dark) !important;
            color: #ffffff !important;
        }

        div[data-baseweb="select"] svg {
            color: var(--teal-dark) !important;
            fill: var(--teal-dark) !important;
            opacity: 1 !important;
            width: 22px !important;
            height: 22px !important;
        }

        div[data-baseweb="select"]:hover > div {
            border-color: var(--teal) !important;
            background-color: #ffffff !important;
        }

        div[data-baseweb="select"]:hover svg {
            color: var(--sun) !important;
            fill: var(--sun) !important;
        }

        .consent-copy {
            color: var(--ink);
            line-height: 1.72;
            font-size: 1rem;
        }

        .consent-copy h3 {
            font-family: "Fraunces", Georgia, serif;
            font-size: 1.45rem;
            margin: 0 0 0.75rem;
        }

        .participant-section {
            padding: 0;
            border-radius: 12px;
            border: 0;
            background: transparent;
            box-shadow: none;
            margin-top: -0.65rem;
        }

        .consent-page h1,
        .consent-page h3 {
            font-family: "Fraunces", Georgia, serif;
            color: var(--ink);
            margin-top: 0.2rem;
            margin-bottom: 0.35rem;
        }

        .participant-title {
            font-family: "Inter", "Aptos", "Segoe UI", system-ui, sans-serif;
            color: var(--ink);
            font-size: 1.45rem;
            font-weight: 700;
            line-height: 1.2;
            margin: 0.25rem 0 0.45rem;
        }

        .element-container {
            margin-bottom: 0.45rem;
        }

        div[data-testid="stSlider"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 12px;
            padding: 12px 14px 4px;
            margin-bottom: 12px;
            box-shadow: 0 8px 20px rgba(18, 43, 45, 0.04);
        }

        div[data-testid="stProgress"] > div > div {
            background-color: var(--teal);
        }

        [data-testid="stHorizontalBlock"] {
            gap: 1rem;
        }

        img {
            max-width: 100%;
        }

        @media (max-width: 768px) {
            .block-container {
                padding: 0 0.75rem 1.6rem;
            }
            .mmse-naming-grid {
                grid-template-columns: 1fr;
            }
            .assessment-card {
                padding: 16px;
            }
            .desktop-progress {
                display: none;
            }
            .mobile-progress {
                display: block;
                font-weight: 700;
                margin: 0.5rem 0;
                padding: 10px 12px;
                border-radius: 8px;
                color: var(--teal-dark);
                background: var(--surface-soft);
                border: 1px solid var(--line);
            }
            div[data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
            }

            h1 {
                font-size: clamp(2.8rem, 14vw, 4.4rem);
            }

            .app-hero {
                border-radius: 0;
            }

            .hero-chips {
                gap: 6px;
            }

            .hero-chip {
                width: auto;
                justify-content: center;
            }

            [data-testid="stTabs"] [role="tab"] {
                min-width: max-content;
                padding: 9px 12px;
            }
        }

        @media (max-width: 480px) {
            .block-container,
            .assessment-container {
                padding: 12px;
            }
            .assessment-card,
            .object-card {
                padding: 14px;
                border-radius: 8px;
            }
            .object-card img {
                max-width: 180px;
            }

            div[data-testid="stMetric"] {
                padding: 10px 12px;
            }

            .app-hero {
                padding: 0;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


_inject_responsive_css()


def _svg_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def _render_reading_copy(title: str | None, body: str) -> None:
    paragraphs = "".join(f"<p>{line.strip()}</p>" for line in body.splitlines() if line.strip())
    heading = f"<h3>{title}</h3>" if title else ""
    st.markdown(
        f"""
        <div class="consent-copy">
            {heading}
            {paragraphs}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_answers_text() -> str:
    return "\n".join(
        f"Q{i + 1}: {question}\nA{i + 1}: {answer}"
        for i, (question, answer) in enumerate(zip(session["questions"], session["answers"]))
    )


def _run_emotion_analysis_if_ready() -> None:
    if session["emotion_result"] is not None:
        return
    if not session["answers"]:
        return
    if not interview_is_complete(session):
        return
    session["emotion_result"] = classify_emotion_fast(_build_answers_text())


def _render_transcript() -> None:
    normalize_interview_state(session)
    if not session["questions"]:
        return
    st.subheader("Interview Transcript")
    for index, question in enumerate(session["questions"]):
        st.markdown(f"**Q{index + 1}.** {question}")
        if index < len(session["answers"]):
            st.write(session["answers"][index])


def _risk_flags() -> dict:
    return (session.get("emotion_result") or {}).get("risk_flags", {})


def _clear_report_outputs() -> None:
    session["report_json"] = None
    session["pdf_bytes"] = None


def _save_screening_record_update() -> None:
    record = build_screening_record(session)
    session["research_save_result"] = save_screening_record(record)
    session["screening_record_saved"] = bool(session["research_save_result"].get("local_success"))


def _save_screening_record_once_if_ready(report_ready: bool) -> None:
    if not report_ready or session.get("screening_record_saved"):
        return
    _save_screening_record_update()


def _render_research_save_status() -> None:
    result = session.get("research_save_result")
    if not result:
        return
    st.markdown("### Research Record Status")
    if result.get("local_success") or result.get("google_success"):
        st.success("Record saved successfully.")
    else:
        st.warning("The record could not be saved. Please review the storage settings and try again.")


def _has_results_to_review() -> bool:
    return any(
        [
            session.get("emotion_result") is not None,
            session.get("bcqol_result") is not None,
            session.get("mmse_result") is not None,
            session.get("report_json") is not None,
        ]
    )


def _render_feedback_section(report_ready: bool) -> None:
    st.divider()
    if not _has_results_to_review():
        st.markdown("### Research Feedback Form")
        st.info("Complete at least one result section before submitting dissertation feedback.")
        return

    _render_research_save_status()
    st.info(
        "These results are preliminary educational screening indicators only. They are not a diagnosis, clinical advice, or a replacement for professional support."
    )
    if not report_ready:
        st.caption(
            "You can still submit usability feedback now. The full screening row will be updated again after BC-QoL, MMSE, and report outputs are complete."
        )
    if render_feedback_form(session):
        feedback_record = build_feedback_record(session)
        session["feedback_open_comment_redacted"] = feedback_record.get("feedback_open_comment_redacted", "")
        session["feedback_save_result"] = save_feedback_record(feedback_record)
        session["research_save_result"] = session["feedback_save_result"]
        _render_research_save_status()


def _build_stage_two_assessment() -> dict | None:
    if session.get("bcqol_result") is None or session.get("mmse_result") is None:
        return None
    return {
        "bcqol": {
            "score": session["bcqol_result"]["score_total"],
            "interpretation": session["bcqol_result"]["interpretation"],
            "key_domains": session["bcqol_result"]["key_domains"],
        },
        "mmse": {
            "score": session["mmse_result"]["total_score"],
            "max_score": session["mmse_result"]["max_score"],
            "interpretation": session["mmse_result"]["interpretation"],
            "domain_scores": session["mmse_result"]["domain_scores"],
            "language_naming": session["mmse_result"]["language_naming"],
            "risk_flag": session["mmse_result"]["risk_flag"],
            "review_flags": session["mmse_result"]["review_flags"],
            "weak_areas": session["mmse_result"]["weak_areas"],
        },
    }


def _render_emotion_summary(result: dict) -> None:
    st.markdown("### Emotion Classification")
    note = result.get("generation_note") or result.get("confidence_note", "")
    st.success(note or "Heuristic emotional summary has been generated.")

    primary_col, confidence_col = st.columns(2)
    with primary_col:
        st.metric("Primary Emotion", result.get("emotion_label", "unknown").replace("_", " ").title())
    with confidence_col:
        top_probability = max(result.get("emotion_probs", {}).values(), default=0.0)
        st.metric("Top Probability", f"{top_probability * 100:.1f}%")

    st.write(result.get("summary", ""))
    st.markdown("#### Emotion Distribution")
    for label, probability in sorted(
        result.get("emotion_probs", {}).items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        st.caption(f"{label.title()}: {probability * 100:.1f}%")
        st.progress(float(probability))

    flags = result.get("risk_flags", {})
    flag_col1, flag_col2, flag_col3 = st.columns(3)
    flag_col1.metric("High Distress", "Yes" if flags.get("high_distress") else "No")
    flag_col2.metric("Self-Harm Ideation", "Yes" if flags.get("self_harm_ideation") else "No")
    flag_col3.metric("Needs Human Follow-up", "Yes" if flags.get("needs_human_followup") else "No")


def _render_bcqol_summary(result: dict) -> None:
    st.markdown("### BC-QoL Score")
    st.metric("Normalized Score", f"{result.get('score_total', 0):.0f} / 100")
    st.progress(float(result.get("score_total", 0)) / 100)
    st.caption(
        f"Questionnaire total: {result.get('raw_total', 0)} out of {result.get('max_possible_score', 0)}"
    )
    st.write(result.get("interpretation", ""))
    st.caption("Key domains: " + ", ".join(result.get("key_domains", [])))


def _render_mmse_summary(result: dict) -> None:
    st.markdown("### MMSE Score")
    score_col1, score_col2, score_col3 = st.columns(3)
    score_col1.metric("MMSE Total", f"{result.get('total_score', 0)}/{result.get('max_score', 30)}")
    score_col2.metric("Interpretation", result.get("interpretation", "N/A"))
    score_col3.metric("Cognitive Risk Flag", "Yes" if result.get("risk_flag") else "No")
    st.write(result.get("interpretation_detail", {}).get("message", ""))
    st.caption("Weak areas: " + (", ".join(result.get("weak_areas", [])) or "No major weak area flagged"))
    if result.get("review_flags"):
        st.warning("Review flags: " + ", ".join(result["review_flags"]))

    st.markdown("#### Domain Scores")
    domain_scores = result.get("domain_scores", {})
    domain_cols = st.columns(3)
    domain_cols[0].metric("Orientation", f"{domain_scores.get('orientation_time', 0) + domain_scores.get('orientation_place', 0)}/10")
    domain_cols[1].metric("Attention", f"{domain_scores.get('attention_calculation', 0)}/5")
    domain_cols[2].metric("Language", f"{domain_scores.get('language', 0)}/9")
    st.caption(
        "Detailed domains: "
        f"time {domain_scores.get('orientation_time', 0)}/5, "
        f"place {domain_scores.get('orientation_place', 0)}/5, "
        f"registration {domain_scores.get('registration', 0)}/3, "
        f"recall {domain_scores.get('recall', 0)}/3"
    )
    naming = result.get("language_naming", {})
    if naming:
        method = str(naming.get("method", "unknown")).replace("_", " ")
        st.caption(f"Object naming method used: {method}; score {naming.get('score', 0)}/2")
    st.markdown('<div class="assessment-info">', unsafe_allow_html=True)
    with st.expander("Read MMSE result note", expanded=False):
        _render_reading_copy("MMSE Result Note", MMSE_RESULT_DISCLAIMER)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_report_summary(report_json: dict) -> None:
    st.markdown("### Screening Report")
    note = report_json.get("generation_note", "")
    st.success(note or "Screening report has been generated.")

    st.markdown(f"#### {report_json.get('headline', 'Screening Summary Report')}")
    scores = report_json.get("scores", {})
    score_cols = st.columns(3)
    score_cols[0].metric("Emotion Label", str(scores.get("emotion_label", "unknown")).replace("_", " ").title())
    bcqol_score = scores.get("bcqol_score_total")
    mmse_score = scores.get("mmse_score_total")
    score_cols[1].metric("BC-QoL Score", f"{bcqol_score:.0f}/100" if isinstance(bcqol_score, (int, float)) else "N/A")
    score_cols[2].metric("MMSE Score", f"{mmse_score}/30" if isinstance(mmse_score, int) else "N/A")

    sections = report_json.get("sections", {})
    st.markdown("#### Emotional Summary")
    st.write(sections.get("emotional_summary", ""))
    st.markdown("#### Cognitive Summary")
    st.write(sections.get("cognitive_summary", ""))
    st.markdown("#### Combined Insights")
    st.write(sections.get("combined_insights", ""))
    st.markdown("#### Next Steps")
    st.write(sections.get("next_steps", ""))
    st.info(report_json.get("disclaimer", ""))
    st.caption(report_json.get("signposting", ""))


def _get_step_validation_messages(step: int, mmse_state: dict) -> list[str]:
    messages: list[str] = []
    if step == 1 and not mmse_state.get("consent"):
        messages.append("Please confirm the MMSE start consent before continuing.")
    elif step == 2:
        orientation_time = mmse_state["orientationTime"]
        orientation_place = mmse_state["orientationPlace"]
        for field in ["year", "season", "date", "day", "month"]:
            if not str(orientation_time.get(field, "")).strip():
                messages.append("Please complete all orientation-to-time questions.")
                break
        for field in ["country", "city", "region", "setting", "floorOrContext"]:
            if not str(orientation_place.get(field, "")).strip():
                messages.append("Please complete all orientation-to-place questions.")
                break
    elif step == 3:
        if any(not str(word).strip() for word in mmse_state["registration"]["userWords"]):
            messages.append("Please complete the registration words before continuing.")
    elif step == 4:
        attention = mmse_state["attention"]
        if attention["method"] == "serial_7s":
            if any(not str(answer).strip() for answer in attention["serialAnswers"]):
                messages.append("Please complete all Serial 7s answers.")
        elif not str(attention["worldBackward"]).strip():
            messages.append("Please enter WORLD backwards before continuing.")
    elif step == 5:
        if any(not str(word).strip() for word in mmse_state["recall"]["userWords"]):
            messages.append("Please complete the delayed recall section.")
    elif step == 6:
        language = mmse_state["language"]
        naming = language["naming"]
        if naming.get("method") == "character_recognition_fallback":
            if any(not str(naming.get(field, "")).strip() for field in ["fallbackItem1", "fallbackItem2"]):
                messages.append("Please complete the fallback recognition tasks.")
        elif any(not str(naming.get(field, "")).strip() for field in ["pencil", "watch"]):
            messages.append("Please complete the object naming tasks.")
        if not str(language["repetition"]).strip():
            messages.append("Please complete the sentence repetition task.")
        sequence = language["threeStageCommand"].get("sequence", [])
        if len(sequence) < 3 or any(not str(action).strip() for action in sequence):
            messages.append("Please complete the three-stage command ordering task.")
        if not language["readAndObey"]:
            messages.append("Please confirm the read-and-obey task.")
        if not str(language["writtenSentence"]).strip():
            messages.append("Please write a sentence before continuing.")
        if not str(language["copyDesignAnswer"]).strip():
            messages.append("Please complete the copy design task.")
    return messages


def _render_assessment_wizard() -> None:
    st.subheader("Second-Stage Structured Clinical Assessment")
    st.markdown('<div class="assessment-info">', unsafe_allow_html=True)
    with st.expander("Read MMSE remote screening information", expanded=False):
        _render_reading_copy("MMSE Remote Screening Information", MMSE_REMOTE_DISCLAIMER)
    st.markdown("</div>", unsafe_allow_html=True)

    current_step = session["assessment_step"]
    mmse_state = session["mmse_form_state"]
    progress = current_step / (len(ASSESSMENT_STEP_TITLES) - 1)
    st.markdown(
        f"""
        <div class="desktop-progress">{" &rarr; ".join(ASSESSMENT_STEP_TITLES)}</div>
        <div class="mobile-progress">Step {current_step + 1} of {len(ASSESSMENT_STEP_TITLES)}</div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(progress, text=f"Step {current_step + 1} of {len(ASSESSMENT_STEP_TITLES)}: {ASSESSMENT_STEP_TITLES[current_step]}")

    if current_step == 0:
        st.markdown("### BC-QoL Assessment")
        st.caption("Each question uses a 1-5 Likert scale.")
        for index, question in enumerate(BCQOL_QUESTIONS):
            session["bcqol_responses"][index] = st.slider(
                question,
                min_value=1,
                max_value=5,
                value=int(session["bcqol_responses"][index]),
                key=f"bcqol_response_{index}",
            )

    elif current_step == 1:
        st.markdown("### MMSE Start Confirmation")
        st.markdown('<div class="assessment-info">', unsafe_allow_html=True)
        with st.expander("Read MMSE start information", expanded=False):
            _render_reading_copy(
                "MMSE Start Confirmation",
                (
                    "The next section is the MMSE-style cognitive screening form.\n"
                    "It is remote, preliminary, and not a diagnosis.\n"
                    "Please continue only if you are ready to complete the cognitive screening tasks."
                ),
            )
        st.markdown("</div>", unsafe_allow_html=True)
        mmse_state["consent"] = st.checkbox(
            "I understand and agree to start the MMSE screening section.",
            value=bool(mmse_state.get("consent", False)),
            key="mmse_start_consent",
        )
        st.caption("Optional flags help interpret MMSE results more cautiously.")
        flag_cols = st.columns(2)
        flag_labels = {
            "language_limitation": "Language barrier or English difficulty",
            "vision_issue": "Vision issue affected completion",
            "hearing_issue": "Hearing issue affected completion",
            "typing_difficulty": "Typing or motor difficulty affected completion",
        }
        for index, (flag_name, label) in enumerate(flag_labels.items()):
            mmse_state["accessibility_flags"][flag_name] = flag_cols[index % 2].checkbox(
                label,
                value=mmse_state["accessibility_flags"].get(flag_name, False),
                key=f"accessibility_{flag_name}",
            )

    elif current_step == 2:
        st.markdown("### MMSE Orientation")
        time_col, place_col = st.columns(2)
        with time_col:
            st.markdown("#### Orientation to Time")
            orientation_time = mmse_state["orientationTime"]
            orientation_time["year"] = st.text_input("What year is it?", value=str(orientation_time["year"]))
            orientation_time["season"] = st.selectbox(
                "What season is it?",
                ["", "Winter", "Spring", "Summer", "Autumn"],
                index=["", "Winter", "Spring", "Summer", "Autumn"].index(orientation_time["season"]) if orientation_time["season"] in {"", "Winter", "Spring", "Summer", "Autumn"} else 0,
            )
            orientation_time["date"] = st.text_input("What date is it?", value=str(orientation_time["date"]))
            orientation_time["day"] = st.selectbox(
                "What day of the week is it?",
                ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                index=["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(orientation_time["day"]) if orientation_time["day"] in {"", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"} else 0,
            )
            orientation_time["month"] = st.selectbox(
                "What month is it?",
                ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
                index=["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"].index(orientation_time["month"]) if orientation_time["month"] in {"", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"} else 0,
            )
        with place_col:
            st.markdown("#### Orientation to Place")
            orientation_place = mmse_state["orientationPlace"]
            orientation_place["country"] = st.text_input("Which country are you in?", value=orientation_place["country"])
            orientation_place["city"] = st.text_input("Which city or town are you in?", value=orientation_place["city"])
            orientation_place["region"] = st.text_input("Which region, county, or state are you in?", value=orientation_place["region"])
            orientation_place["setting"] = st.selectbox(
                "Where are you completing this assessment?",
                [""] + MMSE_SETTING_OPTIONS,
                index=([""] + MMSE_SETTING_OPTIONS).index(orientation_place["setting"]) if orientation_place["setting"] in MMSE_SETTING_OPTIONS else 0,
            )
            floor_label = "Which floor or room/context are you in?"
            orientation_place["floorOrContext"] = st.text_input(floor_label, value=orientation_place["floorOrContext"])

    elif current_step == 3:
        st.markdown("### MMSE Registration")
        st.markdown('<div class="assessment-info">', unsafe_allow_html=True)
        with st.expander("Read MMSE registration instructions", expanded=False):
            _render_reading_copy(
                "MMSE Registration Instructions",
                "Please remember these three words for later: " + ", ".join(MMSE_REGISTRATION_WORDS),
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.caption("Only the first attempt counts for scoring.")
        for index in range(3):
            mmse_state["registration"]["userWords"][index] = st.selectbox(
                f"Immediate recall word {index + 1}",
                [""] + MMSE_WORD_OPTIONS,
                index=([""] + MMSE_WORD_OPTIONS).index(mmse_state["registration"]["userWords"][index]) if mmse_state["registration"]["userWords"][index] in MMSE_WORD_OPTIONS else 0,
                key=f"registration_word_{index}",
            )

    elif current_step == 4:
        st.markdown("### MMSE Attention and Calculation")
        attention = mmse_state["attention"]
        attention["method"] = st.radio(
            "Choose the attention task",
            options=["serial_7s", "world_backward"],
            format_func=lambda value: "Serial 7s" if value == "serial_7s" else "WORLD backwards",
            index=0 if attention["method"] == "serial_7s" else 1,
        )
        if attention["method"] == "serial_7s":
            st.caption("Subtract 7 from 100 five times.")
            for index in range(5):
                attention["serialAnswers"][index] = st.text_input(
                    f"Answer {index + 1}",
                    value=str(attention["serialAnswers"][index]),
                    key=f"serial_7_{index}",
                )
        else:
            st.caption("Spell WORLD backwards.")
            attention["worldBackward"] = st.text_input(
                "WORLD backwards",
                value=attention["worldBackward"],
            )

    elif current_step == 5:
        st.markdown("### MMSE Delayed Recall")
        st.caption("What were the three words shown earlier?")
        for index in range(3):
            mmse_state["recall"]["userWords"][index] = st.selectbox(
                f"Delayed recall word {index + 1}",
                [""] + MMSE_WORD_OPTIONS,
                index=([""] + MMSE_WORD_OPTIONS).index(mmse_state["recall"]["userWords"][index]) if mmse_state["recall"]["userWords"][index] in MMSE_WORD_OPTIONS else 0,
                key=f"recall_word_{index}",
            )

    elif current_step == 6:
        st.markdown("### MMSE Language Tasks")
        language = mmse_state["language"]
        naming = language.setdefault("naming", {})
        naming.setdefault("method", "image_object_naming")
        naming.setdefault("pencil", "")
        naming.setdefault("watch", "")
        naming.setdefault("fallbackItem1", "")
        naming.setdefault("fallbackItem2", "")
        use_fallback = st.checkbox(
            "Images did not load or are not accessible; use character recognition fallback.",
            value=naming.get("method") == "character_recognition_fallback",
        )
        naming["method"] = "character_recognition_fallback" if use_fallback else "image_object_naming"

        if naming["method"] == "character_recognition_fallback":
            st.warning("Fallback mode will be marked for review because standard object images were not used.")
            st.markdown(
                """
                <div class="mmse-naming-grid">
                  <div class="object-card"><div class="fallback-symbol" aria-label="Character A">A</div></div>
                  <div class="object-card"><div class="fallback-symbol" aria-label="Character 7">7</div></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            fallback_col1, fallback_col2 = st.columns(2)
            naming["fallbackItem1"] = fallback_col1.text_input(
                "Type the character shown above",
                value=naming["fallbackItem1"],
                key="mmse_fallback_item_1",
            )
            naming["fallbackItem2"] = fallback_col2.text_input(
                "Type the character shown above",
                value=naming["fallbackItem2"],
                key="mmse_fallback_item_2",
            )
        else:
            asset_dir = Path(__file__).parent / "public" / "assets" / "mmse"
            name_col1, name_col2 = st.columns(2)
            with name_col1:
                st.markdown(
                    f"""
                    <div class="object-card">
                      <img src="{_svg_data_uri(asset_dir / "pencil.svg")}" alt="Pencil object for MMSE naming task" />
                      <p>Name the object shown below.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                naming["pencil"] = st.text_input(
                    "Name this object",
                    value=naming["pencil"],
                    key="mmse_pencil_answer",
                    placeholder="Type the object name",
                )
            with name_col2:
                st.markdown(
                    f"""
                    <div class="object-card">
                      <img src="{_svg_data_uri(asset_dir / "watch.svg")}" alt="Watch object for MMSE naming task" />
                      <p>Name the object shown below.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                naming["watch"] = st.text_input(
                    "Name this object",
                    value=naming["watch"],
                    key="mmse_watch_answer",
                    placeholder="Type the object name",
                )
        language["repetition"] = st.text_input(
            'Repeat this sentence: "No ifs, ands, or buts"',
            value=language["repetition"],
        )
        st.markdown("#### Three-Stage Command")
        st.caption("Select the three actions in the same order as the instruction. This replaces the earlier drag task.")
        command = language["threeStageCommand"]
        command.setdefault("sequence", ["", "", ""])
        action_options = [
            "",
            "Take the paper in your right hand",
            "Fold the paper in half",
            "Place the paper on the table",
            "Put the paper in your pocket",
            "Tear the paper",
        ]
        st.info("Instruction: Take the paper in your right hand, fold it in half, and place it on the table.")
        for index in range(3):
            command["sequence"][index] = st.selectbox(
                f"Action {index + 1}",
                action_options,
                index=action_options.index(command["sequence"][index])
                if command["sequence"][index] in action_options
                else 0,
                key=f"mmse_command_sequence_{index}",
            )
        st.markdown("#### Read and Obey")
        st.markdown("**CLOSE YOUR EYES**")
        language["readAndObey"] = st.checkbox("I have done this", value=language["readAndObey"])
        st.markdown("#### Write a Sentence")
        language["writtenSentence"] = st.text_area(
            "Write one complete sentence about anything.",
            value=language["writtenSentence"],
            height=120,
        )
        st.markdown("#### Copy Design")
        asset_dir = Path(__file__).parent / "public" / "assets" / "mmse"
        st.markdown(
            f"""
            <div class="object-card">
              <img src="{_svg_data_uri(asset_dir / "overlapping_pentagons.svg")}" alt="Two overlapping pentagons for MMSE copy design task" />
              <p>Target design: identify the matching copied shape.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        language["copyDesignAnswer"] = st.radio(
            "Select the design that best matches the target copied shape.",
            options=MMSE_SHAPE_OPTIONS,
            index=MMSE_SHAPE_OPTIONS.index(language["copyDesignAnswer"]) if language["copyDesignAnswer"] in MMSE_SHAPE_OPTIONS else 0,
        )

    elif current_step == 7:
        st.markdown("### Review and Submit")
        bcqol_preview = compute_bcqol_result(session["bcqol_responses"])
        st.markdown("#### BC-QoL Preview")
        st.write(f"Score preview: {bcqol_preview['score_total']:.0f}/100")
        st.caption("Interpretation: " + bcqol_preview["interpretation"])
        st.markdown("#### MMSE Completion Review")
        validation_messages = _get_step_validation_messages(1, mmse_state)
        validation_messages += _get_step_validation_messages(2, mmse_state)
        validation_messages += _get_step_validation_messages(3, mmse_state)
        validation_messages += _get_step_validation_messages(4, mmse_state)
        validation_messages += _get_step_validation_messages(5, mmse_state)
        validation_messages += _get_step_validation_messages(6, mmse_state)
        if validation_messages:
            for message in sorted(set(validation_messages)):
                st.warning(message)
        else:
            st.success("All sections look complete.")
        if st.button("Submit Stage Two Assessment", type="primary", use_container_width=True):
            session["bcqol_result"] = compute_bcqol_result(session["bcqol_responses"])
            mmse_result = calculate_mmse_result(session["mmse_form_state"])
            if not mmse_result.get("success"):
                st.error(mmse_result.get("error", "MMSE validation failed."))
                if mmse_result.get("missing_fields"):
                    st.caption("Missing fields: " + ", ".join(mmse_result["missing_fields"]))
            else:
                session["mmse_result"] = mmse_result
                session["stage_two_assessment"] = _build_stage_two_assessment()
                session["screening_completed_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                session["screening_record_saved"] = False
                _clear_report_outputs()
                session["assessment_step"] = 8
                st.rerun()

    elif current_step == 8:
        st.markdown("### Structured Assessment Results")
        if session["bcqol_result"] is None or session["mmse_result"] is None:
            st.warning("Complete the BC-QoL and MMSE sections to generate results.")
        else:
            left_col, right_col = st.columns(2)
            with left_col:
                _render_bcqol_summary(session["bcqol_result"])
            with right_col:
                _render_mmse_summary(session["mmse_result"])
            st.info(MMSE_RESULT_DISCLAIMER)

    nav_left, nav_right = st.columns(2)
    with nav_left:
        if current_step > 0 and st.button("Back", use_container_width=True):
            session["assessment_step"] -= 1
            st.rerun()
    with nav_right:
        if current_step < 7 and st.button("Next", use_container_width=True):
            validation_messages = _get_step_validation_messages(current_step, mmse_state)
            if validation_messages:
                for message in validation_messages:
                    st.warning(message)
            else:
                session["assessment_step"] += 1
                st.rerun()


st.markdown(
    f"""
    <section class="app-hero">
        <h1>Always <span class="hero-accent">Calm</span>, Always <span class="hero-accent">Clear</span>.</h1>
        <p class="hero-copy">
            A guided mental health screening prototype that listens first, keeps the process simple,
            and turns interview, BC-QoL, and MMSE responses into a careful screening summary.
        </p>
        <div class="hero-chips">
            <span class="hero-chip">Chatbot interview</span>
            <span class="hero-chip">BC-QoL</span>
            <span class="hero-chip">MMSE</span>
            <span class="hero-chip">Screening report</span>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

if not (session["consent"].get("is_consented") and consent_is_complete(session["consent"])):
    render_consent_form(session)
    st.stop()

tab1, tab2, tab3 = st.tabs(
    [
        "Chatbot Interview",
        "Clinical Forms",
        "Results and Report",
    ]
)

with tab1:
    st.subheader("Chatbot Interview")
    session["participant_id"] = session["session_id"]

    if st.button("Start Interview", type="primary", use_container_width=True):
        start_interview(session)
        st.rerun()

    if not session.get("interview_started", False):
        st.info("Click Start Interview to begin the screening flow.")
    else:
        normalize_interview_state(session)
        current_question_index = len(session["answers"])
        if (
            current_question_index < min(len(session["questions"]), INTERVIEW_QUESTION_COUNT)
            and not interview_is_complete(session)
        ):
            st.markdown(f"### Question {current_question_index + 1} of {INTERVIEW_QUESTION_COUNT}")
            st.write(session["questions"][current_question_index])
            with st.form(f"interview_answer_form_{current_question_index}"):
                answer = st.text_area("Your answer", height=140, key=f"answer_text_{current_question_index}")
                submitted = st.form_submit_button("Submit Answer")
                if submitted:
                    if not answer.strip():
                        st.warning("Please enter an answer before continuing.")
                    else:
                        with st.spinner("Preparing the next question..."):
                            result = handle_user_answer(session, answer)
                        if result["status"] in {"completed", "safety_stop"}:
                            _run_emotion_analysis_if_ready()
                        st.rerun()

        _render_transcript()
        if session.get("interview_generation_note"):
            st.caption(session["interview_generation_note"])

        if interview_is_complete(session):
            _run_emotion_analysis_if_ready()
            st.success("Interview complete. You can continue to the Clinical Forms or Results tab.")

        if session["safety_stop"]:
            st.error(CRISIS_SIGNPOSTING_MESSAGE)

with tab2:
    _render_assessment_wizard()

with tab3:
    st.subheader("Results and Report")
    st.metric("Consent confirmed", "Yes" if session["consent"].get("is_consented") else "No")

    if session["emotion_result"] is None and interview_is_complete(session):
        _run_emotion_analysis_if_ready()

    if session["emotion_result"] is None:
        st.info("Complete the interview to generate emotion classification.")
    else:
        _render_emotion_summary(session["emotion_result"])

    if _risk_flags().get("self_harm_ideation"):
        st.warning(CRISIS_SIGNPOSTING_MESSAGE)

    report_ready = (
        session["emotion_result"] is not None
        and session["bcqol_result"] is not None
        and session["mmse_result"] is not None
        and session["stage_two_assessment"] is not None
    )
    _save_screening_record_once_if_ready(report_ready)
    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("Generate Emotion Analysis", disabled=not interview_is_complete(session), use_container_width=True):
            with st.spinner("Generating emotional summary..."):
                session["emotion_result"] = classify_emotion_fast(_build_answers_text())
            _clear_report_outputs()
            st.rerun()
    with action_col2:
        if not report_ready:
            st.caption("Complete the interview, BC-QoL, and MMSE sections before generating the final report.")
        if st.button("Generate Screening Report", disabled=not report_ready, use_container_width=True):
            session["report_json"] = compose_report_llm(
                emotion_result=session["emotion_result"],
                bcqol_result=session["bcqol_result"],
                mmse_result=session["mmse_result"],
                stage_two_assessment=session["stage_two_assessment"],
                meta={
                    "session_id": session["session_id"],
                    "consent": session["consent"],
                    "created_utc": session["created_utc"],
                    "question_count": len(session["questions"]),
                },
            )
            _save_screening_record_update()
            st.success("Screening report has been generated for review.")

    if session["report_json"] is not None:
        _render_report_summary(session["report_json"])
        if st.button("Create PDF Download", use_container_width=True):
            session["pdf_bytes"] = render_pdf(session["report_json"])
            _save_screening_record_update()
            st.success("PDF ready to download.")

    if session.get("pdf_bytes") is not None:
        st.download_button(
            "Download PDF Report",
            data=session["pdf_bytes"],
            file_name=f"{session['session_id']}_screening_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    _render_feedback_section(report_ready)
