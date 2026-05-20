from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from core.record_store import sanitize_free_text


LIKERT_OPTIONS = [1, 2, 3, 4, 5]


def render_feedback_form(session: dict) -> bool:
    st.markdown("### Research Feedback Form")
    st.write(
        "Your feedback helps evaluate the usability, clarity, and usefulness of this educational screening prototype for dissertation research. "
        "Please do not enter your name, email, phone number, address, or any identifying personal details."
    )

    if session.get("feedback_submitted"):
        st.success("Thank you. Your anonymous feedback has been stored with this session record.")
        return False

    session["feedback_ease_of_use"] = st.select_slider(
        "Ease of use",
        options=LIKERT_OPTIONS,
        value=int(session.get("feedback_ease_of_use") or 3),
        format_func=lambda value: {
            1: "1 - Very difficult",
            2: "2 - Difficult",
            3: "3 - Neutral",
            4: "4 - Easy",
            5: "5 - Very easy",
        }[value],
    )
    session["feedback_question_clarity"] = st.select_slider(
        "Question clarity",
        options=LIKERT_OPTIONS,
        value=int(session.get("feedback_question_clarity") or 3),
        format_func=lambda value: {
            1: "1 - Very unclear",
            2: "2 - Unclear",
            3: "3 - Neutral",
            4: "4 - Clear",
            5: "5 - Very clear",
        }[value],
    )
    session["feedback_report_clarity"] = st.select_slider(
        "Report clarity",
        options=LIKERT_OPTIONS,
        value=int(session.get("feedback_report_clarity") or 3),
        format_func=lambda value: {
            1: "1 - Very unclear",
            2: "2 - Unclear",
            3: "3 - Neutral",
            4: "4 - Clear",
            5: "5 - Very clear",
        }[value],
    )
    session["feedback_comfort"] = st.select_slider(
        "Comfort using the prototype",
        options=LIKERT_OPTIONS,
        value=int(session.get("feedback_comfort") or 3),
        format_func=lambda value: {
            1: "1 - Very uncomfortable",
            2: "2 - Uncomfortable",
            3: "3 - Neutral",
            4: "4 - Comfortable",
            5: "5 - Very comfortable",
        }[value],
    )
    session["feedback_trust"] = st.select_slider(
        "Trust as a preliminary support tool",
        options=LIKERT_OPTIONS,
        value=int(session.get("feedback_trust") or 3),
        format_func=lambda value: {
            1: "1 - Do not trust at all",
            2: "2 - Low trust",
            3: "3 - Neutral",
            4: "4 - Some trust",
            5: "5 - Trust as a preliminary support tool",
        }[value],
    )
    session["feedback_usefulness"] = st.select_slider(
        "Usefulness",
        options=LIKERT_OPTIONS,
        value=int(session.get("feedback_usefulness") or 3),
        format_func=lambda value: {
            1: "1 - Not useful",
            2: "2 - Slightly useful",
            3: "3 - Neutral",
            4: "4 - Useful",
            5: "5 - Very useful",
        }[value],
    )
    recommend_options = ["", "Yes", "No", "Not sure"]
    session["feedback_recommend"] = st.selectbox(
        "Would you recommend this prototype as a preliminary support tool?",
        recommend_options,
        index=recommend_options.index(session.get("feedback_recommend", ""))
        if session.get("feedback_recommend", "") in recommend_options
        else 0,
    )
    st.caption(
        "Please avoid identifiable or sensitive personal details. Comments will be stored for research evaluation only."
    )
    if not (session.get("consent") or {}).get("optional_items", {}).get("open_text_feedback_storage"):
        st.caption("Optional comment storage was not selected on the consent screen, so any comment entered here will not be saved.")
    comment = st.text_area(
        "Optional comment",
        value=session.get("feedback_open_comment", ""),
        max_chars=500,
        height=120,
    )
    session["feedback_open_comment"] = comment
    session["feedback_open_comment_redacted"] = sanitize_free_text(comment)
    session["feedback_data_confirmation"] = st.checkbox(
        "I confirm that my anonymous feedback can be stored with my screening scores for dissertation analysis.",
        value=bool(session.get("feedback_data_confirmation", False)),
    )

    submitted = st.button(
        "Submit anonymous feedback",
        type="primary",
        disabled=not session["feedback_data_confirmation"],
        use_container_width=True,
    )
    if submitted:
        session["feedback_submitted"] = True
        session["feedback_completed_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        st.success("Thank you. Your anonymous feedback has been submitted.")
        return True
    return False
