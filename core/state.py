from datetime import datetime, timezone

import streamlit as st

from forms.consent_form import build_anonymous_session_id, build_default_consent_state
from forms.mmse_form import build_default_mmse_state


def build_default_session() -> dict:
    session_id = build_anonymous_session_id()
    return {
        "session_id": session_id,
        "participant_id": session_id,
        "consent": build_default_consent_state(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "interview_started": False,
        "interview_generation_source": "",
        "interview_generation_note": "",
        "questions": [],
        "answers": [],
        "current_index": 0,
        "safety_stop": False,
        "emotion_result": None,
        "bcqol_result": None,
        "mmse_result": None,
        "stage_two_assessment": None,
        "assessment_step": 0,
        "mmse_form_state": build_default_mmse_state(),
        "report_json": None,
        "pdf_bytes": None,
        "screening_record_saved": False,
        "feedback_submitted": False,
        "research_save_result": None,
        "feedback_save_result": None,
        "feedback_ease_of_use": 3,
        "feedback_question_clarity": 3,
        "feedback_report_clarity": 3,
        "feedback_comfort": 3,
        "feedback_trust": 3,
        "feedback_usefulness": 3,
        "feedback_recommend": "",
        "feedback_open_comment": "",
        "feedback_open_comment_redacted": "",
        "feedback_data_confirmation": False,
        "feedback_completed_at_utc": "",
        "screening_completed_at_utc": "",
    }


def ensure_session_state() -> dict:
    if "session" not in st.session_state:
        st.session_state.session = build_default_session()
    return st.session_state.session
