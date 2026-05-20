import re

import requests

from config.settings import get_settings
from core.prompts import QUESTION_SYSTEM_PROMPT, build_question_prompt
from core.safety import contains_imminent_risk


INTERVIEW_QUESTION_COUNT = 5
INTENT_SEQUENCE = [
    "impact_on_life",
    "duration_intensity",
    "coping_support",
    "gentle_safety_check",
]
OPENING_QUESTION = "Tell me about yourself or your current situation."
QUESTION_BANK = {
    "impact_on_life": {
        "sleep": "You mentioned sleep being difficult; how has that been affecting your mood, energy, or concentration during the day?",
        "work": "You mentioned pressure around work or study; how has this been affecting your focus, motivation, or daily responsibilities?",
        "family": "You mentioned relationships or feeling alone; how has this been affecting the way you connect with people close to you?",
        "health": "You mentioned physical symptoms or health worries; how has that been connected with your mood or day-to-day routine?",
        "default": "From what you shared, how has this been affecting your daily routine, responsibilities, or relationships?",
    },
    "duration_intensity": {
        "sleep": "Since sleep has been part of this, when did the difficulty begin, and has it been improving, worsening, or staying the same?",
        "work": "Thinking about the pressure you described, how long has it been affecting your productivity or focus, and how intense does it feel now?",
        "family": "With the relationship changes you mentioned, how long have you noticed this pattern, and has it been getting easier or harder?",
        "health": "With the physical or emotional symptoms you described, how often do they appear in a usual week, and how strong do they feel?",
        "default": "How long has this been going on for you, and has it recently felt lighter, heavier, or about the same?",
    },
    "coping_support": {
        "sleep": "Given how sleep is affecting you, what have you tried so far to rest better, and has anything helped even a little?",
        "work": "When responsibilities feel difficult, what helps you manage the pressure, and is there anyone you can realistically lean on?",
        "family": "When connection feels difficult, who or what helps you feel supported, understood, or a little less alone?",
        "health": "When your body or emotions feel unsettled, what usually helps you calm down or feel more grounded?",
        "default": "When this feels difficult, what helps you cope even slightly, and what support feels available to you right now?",
    },
    "gentle_safety_check": {
        "sleep": "When the tiredness or distress has felt at its worst, have you felt unsafe, at risk of harm, or in need of urgent support?",
        "work": "When the pressure has felt highest, have you felt unsafe, at risk of harm, or like you needed urgent support?",
        "family": "When loneliness or conflict has felt strongest, have you felt unsafe, at risk of harm, or in need of urgent support?",
        "health": "When the symptoms have felt overwhelming, have you felt unsafe, at risk of harm, or in need of urgent support?",
        "default": "When things have felt most difficult, have you felt unsafe, at risk of harm, or in need of urgent support recently?",
    },
}
KEYWORD_GROUPS = {
    "sleep": {"sleep", "insomnia", "tired", "fatigue", "night", "rest"},
    "work": {"work", "job", "study", "college", "university", "deadline", "focus", "concentrate"},
    "family": {"family", "friend", "relationship", "alone", "lonely", "partner", "social"},
    "health": {"pain", "body", "heart", "breath", "panic", "appetite", "headache", "health"},
}


def start_interview(session: dict) -> None:
    session_id = session.get("session_id", session.get("participant_id", "anonymous_session"))
    participant_id = session.get("participant_id", session_id)
    created_utc = session.get("created_utc", "")
    consent = session.get("consent")
    consent_excel_path = session.get("consent_excel_path")
    mmse_form_state = session.get("mmse_form_state")
    bcqol_responses = session.get("bcqol_responses")
    assessment_step = session.get("assessment_step", 0)
    research_state = {
        key: session.get(key)
        for key in [
            "screening_record_saved",
            "feedback_submitted",
            "research_save_result",
            "feedback_save_result",
            "feedback_ease_of_use",
            "feedback_question_clarity",
            "feedback_report_clarity",
            "feedback_comfort",
            "feedback_trust",
            "feedback_usefulness",
            "feedback_recommend",
            "feedback_open_comment",
            "feedback_open_comment_redacted",
            "feedback_data_confirmation",
            "feedback_completed_at_utc",
            "screening_completed_at_utc",
        ]
        if key in session
    }
    session.clear()
    session.update(
        {
            "session_id": session_id,
            "participant_id": participant_id,
            "consent": consent,
            "consent_excel_path": consent_excel_path,
            "created_utc": created_utc,
            "interview_started": True,
            "interview_generation_source": "",
            "interview_generation_note": "",
            "questions": [OPENING_QUESTION],
            "answers": [],
            "current_index": 0,
            "safety_stop": False,
            "emotion_result": None,
            "bcqol_responses": bcqol_responses,
            "bcqol_result": None,
            "mmse_form_state": mmse_form_state,
            "mmse_result": None,
            "stage_two_assessment": None,
            "assessment_step": assessment_step,
            "report_json": None,
            "pdf_bytes": None,
        }
    )
    session.update(research_state)


def normalize_interview_state(session: dict) -> None:
    session["interview_started"] = bool(session.get("interview_started", False))
    session["questions"] = session.get("questions", [])[:INTERVIEW_QUESTION_COUNT]
    session["answers"] = session.get("answers", [])[:INTERVIEW_QUESTION_COUNT]
    session["safety_stop"] = bool(session.get("safety_stop", False))
    if session["safety_stop"]:
        session["current_index"] = min(len(session["answers"]), max(len(session["questions"]) - 1, 0))
        return
    if len(session["answers"]) >= INTERVIEW_QUESTION_COUNT:
        session["questions"] = session["questions"][:INTERVIEW_QUESTION_COUNT]
    elif len(session["questions"]) > len(session["answers"]) + 1:
        session["questions"] = session["questions"][: len(session["answers"]) + 1]
    session["current_index"] = min(len(session["answers"]), max(len(session["questions"]) - 1, 0))
    if not session["questions"] and session["answers"]:
        session["interview_started"] = True
    if not session["interview_started"]:
        session["questions"] = []
        session["answers"] = []
        session["current_index"] = 0


def get_intent_for_turn(index: int) -> str:
    if 0 <= index < len(INTENT_SEQUENCE):
        return INTENT_SEQUENCE[index]
    return INTENT_SEQUENCE[-1]


def interview_is_complete(session: dict) -> bool:
    normalize_interview_state(session)
    if not session.get("interview_started", False):
        return False
    return len(session.get("answers", [])) >= INTERVIEW_QUESTION_COUNT


def _conversation_summary(session: dict) -> str:
    pairs = list(zip(session["questions"], session["answers"]))
    recent_pairs = pairs[-3:]
    return "\n".join(
        f"Question: {question}\nAnswer: {answer}"
        for question, answer in recent_pairs
    )


def _answer_theme(answer: str) -> str:
    lowered = answer.lower()
    scores = {
        theme: sum(1 for token in tokens if token in lowered)
        for theme, tokens in KEYWORD_GROUPS.items()
    }
    best_theme, best_score = max(scores.items(), key=lambda item: item[1])
    return best_theme if best_score > 0 else "default"


def _adaptive_question(intent: str, answer: str, previous_questions: list[str]) -> str:
    bank = QUESTION_BANK[intent]
    theme = _answer_theme(answer)
    candidates = [
        bank.get(theme, bank["default"]),
        bank["default"],
        *[question for key, question in bank.items() if key not in {theme, "default"}],
    ]
    previous = {question.strip().lower() for question in previous_questions}
    for question in candidates:
        if question.strip().lower() not in previous:
            return question
    return f"{bank['default']} Please answer with the most important detail for you right now."


def _clean_generated_question(raw_text: str) -> str:
    text = str(raw_text or "").strip()
    text = text.removeprefix("```").removesuffix("```").strip()
    text = re.sub(r"^(Question\s*:\s*)", "", text, flags=re.IGNORECASE).strip()
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not first_line:
        return ""
    if first_line.upper() in {"SAFETY_STOP", "END_INTERVIEW"}:
        return first_line.upper()
    if "?" in first_line:
        first_line = first_line[: first_line.index("?") + 1]
    if not first_line.endswith("?"):
        first_line = first_line.rstrip(".") + "?"
    return first_line[:240]


def _is_substantive_question(question: str) -> bool:
    if not question or question in {"SAFETY_STOP", "END_INTERVIEW"}:
        return True
    words = re.findall(r"[A-Za-z']+", question)
    lowered = question.strip().lower()
    weak_questions = {
        "why?",
        "how?",
        "how so?",
        "what happened?",
        "tell me more?",
        "can you elaborate?",
        "what about it?",
        "how are you?",
        "are you okay?",
    }
    if lowered in weak_questions:
        return False
    if len(words) < 12:
        return False
    return question.endswith("?")


def generate_gemini_follow_up(session: dict, intent: str, last_answer: str) -> str | None:
    settings = get_settings()
    if not settings.gemini_api_key:
        return None
    if contains_imminent_risk(last_answer):
        return "SAFETY_STOP"

    try:
        prompt = build_question_prompt(
            intent=intent,
            summary=_conversation_summary(session),
            last_answer=last_answer,
            follow_up_index=len(session.get("answers", [])),
            previous_questions=session.get("questions", []),
        )
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent"
        )
        response = requests.post(
            endpoint,
            params={"key": settings.gemini_api_key},
            json={
                "systemInstruction": {
                    "parts": [{"text": QUESTION_SYSTEM_PROMPT}],
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.55,
                    "topP": 0.9,
                    "maxOutputTokens": 120,
                },
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        parts = (
            payload.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        raw_text = " ".join(str(part.get("text", "")) for part in parts)
        question = _clean_generated_question(raw_text)
        if question in {"SAFETY_STOP", "END_INTERVIEW"}:
            return question
        previous = {item.strip().lower() for item in session.get("questions", [])}
        if question and question.strip().lower() not in previous and _is_substantive_question(question):
            session["interview_generation_source"] = "adaptive"
            session["interview_generation_note"] = "The next interview question has been prepared based on the previous response."
            return question
        session["interview_generation_source"] = "fallback"
        session["interview_generation_note"] = "A suitable follow-up question has been prepared."
    except Exception:
        session["interview_generation_source"] = "fallback"
        session["interview_generation_note"] = "A suitable follow-up question has been prepared."
    return None


def handle_user_answer(session: dict, answer: str) -> dict:
    normalize_interview_state(session)
    if not session.get("interview_started", False):
        return {"status": "not_started", "next_question": None}
    if interview_is_complete(session):
        return {"status": "completed", "next_question": None}

    cleaned_answer = answer.strip()
    session["answers"].append(cleaned_answer)
    session["current_index"] = len(session["answers"]) - 1

    if len(session["answers"]) >= INTERVIEW_QUESTION_COUNT:
        normalize_interview_state(session)
        return {"status": "completed", "next_question": None}

    next_turn_index = len(session["answers"]) - 1
    intent = get_intent_for_turn(next_turn_index)
    next_question = generate_gemini_follow_up(session, intent, cleaned_answer)
    if next_question == "SAFETY_STOP":
        session["safety_stop"] = True
        normalize_interview_state(session)
        return {"status": "safety_stop", "next_question": None}
    if next_question == "END_INTERVIEW":
        normalize_interview_state(session)
        return {"status": "completed", "next_question": None}
    if not next_question:
        session["interview_generation_source"] = "fallback"
        session["interview_generation_note"] = "A suitable follow-up question has been prepared."
        next_question = _adaptive_question(intent, cleaned_answer, session["questions"])
    session["questions"].append(next_question)
    normalize_interview_state(session)
    return {"status": "next_question_added", "next_question": next_question}
