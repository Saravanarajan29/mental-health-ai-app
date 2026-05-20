from __future__ import annotations

import re
from datetime import datetime


MMSE_MAX_SCORE = 30
MMSE_REMOTE_DISCLAIMER = (
    "This assessment is for educational and preliminary screening purposes only. "
    "It does not provide a medical diagnosis and should not replace advice from a qualified "
    "healthcare professional. If you are worried about your memory, mood, safety, or wellbeing, "
    "please contact a healthcare professional or emergency support service."
)
MMSE_RESULT_DISCLAIMER = (
    "Your results are screening indicators only. They cannot confirm or rule out any medical or "
    "mental health condition. A qualified professional should interpret cognitive or mental health concerns."
)
MMSE_REGISTRATION_WORDS = ["Apple", "Table", "Penny"]
MMSE_WORD_OPTIONS = ["Apple", "Table", "Penny", "Chair", "Book", "Coin", "Orange", "Window"]
MMSE_COPY_DESIGN_CORRECT_ANSWER = "Two overlapping pentagons"
MMSE_SHAPE_OPTIONS = [
    "A single triangle",
    "Two separate squares",
    MMSE_COPY_DESIGN_CORRECT_ANSWER,
    "A circle inside a square",
]
MMSE_SETTING_OPTIONS = ["Home", "Workplace", "University", "Hospital/clinic", "Public place", "Other"]
MMSE_ACCESSIBILITY_FLAGS = {
    "language_limitation": "language_limitation",
    "vision_issue": "vision_issue",
    "hearing_issue": "hearing_issue",
    "typing_difficulty": "typing_difficulty",
}
SERIAL_7_TARGET = [93, 86, 79, 72, 65]
WORLD_BACKWARD_TARGET = "DLROW"


def build_default_mmse_state(now: datetime | None = None) -> dict:
    now = now or datetime.now()
    return {
        "consent": False,
        "accessibility_flags": {
            "language_limitation": False,
            "vision_issue": False,
            "hearing_issue": False,
            "typing_difficulty": False,
        },
        "orientationTime": {
            "year": "",
            "season": "",
            "date": "",
            "day": "",
            "month": "",
        },
        "orientationPlace": {
            "country": "",
            "city": "",
            "region": "",
            "setting": "",
            "floorOrContext": "",
        },
        "registration": {
            "shownWords": list(MMSE_REGISTRATION_WORDS),
            "userWords": ["", "", ""],
            "attempts": 1,
        },
        "attention": {
            "method": "serial_7s",
            "serialAnswers": ["", "", "", "", ""],
            "worldBackward": "",
        },
        "recall": {
            "userWords": ["", "", ""],
        },
        "language": {
            "naming": {
                "method": "image_object_naming",
                "pencil": "",
                "watch": "",
                "fallbackItem1": "",
                "fallbackItem2": "",
            },
            "repetition": "",
            "threeStageCommand": {
                "step1": False,
                "step2": False,
                "step3": False,
                "sequence": ["", "", ""],
            },
            "readAndObey": False,
            "writtenSentence": "",
            "copyDesignMethod": "multiple_choice_shape_match",
            "copyDesignAnswer": "",
        },
        "admin": {
            "current_year": now.year,
            "current_month": now.strftime("%B"),
            "current_day": now.strftime("%A"),
            "current_date": str(now.day),
            "current_season": infer_season(now.month),
            "remote_administration": True,
            "review_flags": ["remote_administration"],
        },
    }


def infer_season(month: int) -> str:
    if month in {12, 1, 2}:
        return "Winter"
    if month in {3, 4, 5}:
        return "Spring"
    if month in {6, 7, 8}:
        return "Summer"
    return "Autumn"


def validate_mmse_state(state: dict) -> list[str]:
    missing_fields: list[str] = []
    if not state.get("consent"):
        missing_fields.append("consent")

    orientation_time = state.get("orientationTime", {})
    for field in ["year", "season", "date", "day", "month"]:
        if not str(orientation_time.get(field, "")).strip():
            missing_fields.append(f"orientation_time.{field}")

    orientation_place = state.get("orientationPlace", {})
    for field in ["country", "city", "region", "setting", "floorOrContext"]:
        if not str(orientation_place.get(field, "")).strip():
            missing_fields.append(f"orientation_place.{field}")

    registration_words = state.get("registration", {}).get("userWords", [])
    for index in range(3):
        if index >= len(registration_words) or not str(registration_words[index]).strip():
            missing_fields.append(f"registration.word_{index + 1}")

    attention = state.get("attention", {})
    method = attention.get("method")
    if method not in {"serial_7s", "world_backward"}:
        missing_fields.append("attention.method")
    elif method == "serial_7s":
        for index, value in enumerate(attention.get("serialAnswers", [])):
            if not str(value).strip():
                missing_fields.append(f"attention.serial_{index + 1}")
    else:
        if not str(attention.get("worldBackward", "")).strip():
            missing_fields.append("attention.world_backward")

    recall_words = state.get("recall", {}).get("userWords", [])
    for index in range(3):
        if index >= len(recall_words) or not str(recall_words[index]).strip():
            missing_fields.append(f"recall.word_{index + 1}")

    naming = state.get("language", {}).get("naming", {})
    if naming.get("method") == "character_recognition_fallback":
        for field in ["fallbackItem1", "fallbackItem2"]:
            if not str(naming.get(field, "")).strip():
                missing_fields.append(f"language.naming.{field}")
    else:
        for field in ["pencil", "watch"]:
            if not str(naming.get(field, "")).strip():
                missing_fields.append(f"language.naming.{field}")

    language = state.get("language", {})
    if not str(language.get("repetition", "")).strip():
        missing_fields.append("language.repetition")
    command = language.get("threeStageCommand", {})
    sequence = command.get("sequence", [])
    if len(sequence) < 3 or any(not str(value).strip() for value in sequence):
        missing_fields.append("language.three_stage_command")
    if not language.get("readAndObey"):
        missing_fields.append("language.read_and_obey")
    if not str(language.get("writtenSentence", "")).strip():
        missing_fields.append("language.written_sentence")
    if not str(language.get("copyDesignAnswer", "")).strip():
        missing_fields.append("language.copy_design")
    return missing_fields


def _normalize_text(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", value or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def score_object_naming(pencil_answer: str, watch_answer: str) -> dict:
    pencil_valid = {"pencil", "writing pencil"}
    watch_valid = {"watch", "wrist watch", "wristwatch"}
    pencil = _normalize_text(pencil_answer)
    watch = _normalize_text(watch_answer)
    pencil_correct = pencil in pencil_valid
    watch_correct = watch in watch_valid
    return {
        "method": "image_object_naming",
        "score": int(pencil_correct) + int(watch_correct),
        "items": {
            "pencil": pencil_correct,
            "watch": watch_correct,
        },
    }


def score_character_recognition(item_1_answer: str, item_2_answer: str) -> dict:
    item_1_correct = _normalize_text(item_1_answer) == "a"
    item_2_correct = _normalize_text(item_2_answer) == "7"
    return {
        "method": "character_recognition_fallback",
        "score": int(item_1_correct) + int(item_2_correct),
        "items": {
            "item_1": {
                "target": "A",
                "answer": item_1_answer,
                "score": int(item_1_correct),
            },
            "item_2": {
                "target": "7",
                "answer": item_2_answer,
                "score": int(item_2_correct),
            },
        },
    }


def _score_sentence(text: str) -> tuple[int, bool]:
    normalized = _normalize_text(text)
    tokens = normalized.split()
    verbs = {
        "am", "is", "are", "was", "were", "be", "feel", "feels", "felt", "have", "has", "had",
        "think", "thinks", "thought", "sleep", "sleeps", "slept", "work", "works", "worked",
        "study", "studies", "studied", "live", "lives", "lived", "want", "wants", "wanted",
    }
    has_subject = any(token in {"i", "he", "she", "they", "we", "it", "you"} for token in tokens)
    has_verb = any(token in verbs or token.endswith("ing") or token.endswith("ed") for token in tokens)
    score = 1 if len(tokens) >= 3 and has_subject and has_verb else 0
    review_flag = len(tokens) >= 3 and score == 0
    return score, review_flag


def analyse_mmse_domains(domain_scores: dict[str, int]) -> list[str]:
    weak_areas = []
    if domain_scores["orientation_time"] < 4:
        weak_areas.append("time orientation")
    if domain_scores["orientation_place"] < 4:
        weak_areas.append("place orientation")
    if domain_scores["attention_calculation"] < 4:
        weak_areas.append("attention and calculation")
    if domain_scores["recall"] < 2:
        weak_areas.append("short-term recall")
    if domain_scores["language"] < 7:
        weak_areas.append("language or command-following")
    return weak_areas


def interpret_mmse(score: int) -> dict:
    if score >= 25:
        return {
            "level": "No major cognitive concern indicated",
            "severity": "normal_range",
            "message": "The MMSE score is within the commonly expected range. This is not a diagnosis.",
        }
    if score >= 21:
        return {
            "level": "Possible mild cognitive difficulty",
            "severity": "mild_flag",
            "message": "The score may suggest mild cognitive difficulty. A professional assessment is recommended if concerns are present.",
        }
    if score >= 10:
        return {
            "level": "Possible moderate cognitive difficulty",
            "severity": "moderate_flag",
            "message": "The score may suggest moderate cognitive difficulty. Professional clinical follow-up is recommended.",
        }
    return {
        "level": "Possible severe cognitive difficulty",
        "severity": "high_flag",
        "message": "The score may suggest significant cognitive difficulty. Urgent professional assessment is recommended.",
    }


def generate_rule_based_mmse_summary(score: int, interpretation: str, weak_areas: list[str]) -> str:
    summary = f"The user's MMSE score is {score}/30. The result is classified as: {interpretation}."
    if weak_areas:
        summary += " Lower performance was observed in: " + ", ".join(weak_areas) + "."
    else:
        summary += " No major weak domain was detected from the MMSE domain scores."
    summary += " This is a preliminary screening result and not a clinical diagnosis."
    return summary


def calculate_mmse_result(state: dict) -> dict:
    missing_fields = validate_mmse_state(state)
    if missing_fields:
        return {
            "success": False,
            "error": "Incomplete MMSE form",
            "missing_fields": missing_fields,
            "review_flags": ["incomplete_sections"],
        }

    review_flags = set(state.get("admin", {}).get("review_flags", []))
    for flag_name, review_flag in MMSE_ACCESSIBILITY_FLAGS.items():
        if state.get("accessibility_flags", {}).get(flag_name):
            review_flags.add(review_flag)
    if state.get("accessibility_support_required"):
        review_flags.add("accessibility_support")

    orientation_time_input = state["orientationTime"]
    admin = state["admin"]
    orientation_time = {
        "year": 1 if str(orientation_time_input["year"]).strip() == str(admin["current_year"]) else 0,
        "season": 1 if _normalize_text(orientation_time_input["season"]) == _normalize_text(admin["current_season"]) else 0,
        "date": 1 if str(orientation_time_input["date"]).strip() == str(admin["current_date"]) else 0,
        "day": 1 if _normalize_text(orientation_time_input["day"]) == _normalize_text(admin["current_day"]) else 0,
        "month": 1 if _normalize_text(orientation_time_input["month"]) == _normalize_text(admin["current_month"]) else 0,
    }

    orientation_place_input = state["orientationPlace"]
    orientation_place = {
        "country": 1 if _normalize_text(orientation_place_input["country"]) else 0,
        "city": 1 if _normalize_text(orientation_place_input["city"]) else 0,
        "setting": 1 if _normalize_text(orientation_place_input["setting"]) else 0,
        "region": 1 if _normalize_text(orientation_place_input["region"]) else 0,
        "floor_or_context": 1 if _normalize_text(orientation_place_input["floorOrContext"]) else 0,
    }

    registration_words = state["registration"]["userWords"]
    registration = {
        "word_1": 1 if _normalize_text(registration_words[0]) == "apple" else 0,
        "word_2": 1 if _normalize_text(registration_words[1]) == "table" else 0,
        "word_3": 1 if _normalize_text(registration_words[2]) == "penny" else 0,
        "attempts": int(state["registration"].get("attempts", 1)),
    }

    attention_input = state["attention"]
    if attention_input["method"] == "serial_7s":
        answers = []
        score = 0
        for index, target in enumerate(SERIAL_7_TARGET):
            try:
                value = int(str(attention_input["serialAnswers"][index]).strip())
            except ValueError:
                value = None
            answers.append(value)
            if value == target:
                score += 1
        attention_calculation = {
            "method": "serial_7s",
            "answers": answers,
            "score": score,
        }
    else:
        review_flags.add("alternative_task_used")
        normalized = _normalize_text(attention_input["worldBackward"]).replace(" ", "")
        score = sum(1 for index, letter in enumerate(WORLD_BACKWARD_TARGET) if index < len(normalized) and normalized[index].upper() == letter)
        attention_calculation = {
            "method": "world_backward",
            "answer": attention_input["worldBackward"],
            "score": score,
        }

    recall_words = state["recall"]["userWords"]
    recall = {
        "word_1": 1 if _normalize_text(recall_words[0]) == "apple" else 0,
        "word_2": 1 if _normalize_text(recall_words[1]) == "table" else 0,
        "word_3": 1 if _normalize_text(recall_words[2]) == "penny" else 0,
    }

    naming_input = state["language"]["naming"]
    if naming_input.get("method") == "character_recognition_fallback":
        language_naming = score_character_recognition(
            naming_input.get("fallbackItem1", ""),
            naming_input.get("fallbackItem2", ""),
        )
        review_flags.add("object_image_not_available_character_recognition_used")
    else:
        language_naming = score_object_naming(
            naming_input.get("pencil", ""),
            naming_input.get("watch", ""),
        )

    repetition_score = 1 if _normalize_text(state["language"]["repetition"]) == "no ifs ands or buts" else 0
    command_input = state["language"]["threeStageCommand"]
    sequence = command_input.get("sequence", [])
    if len(sequence) >= 3 and any(sequence):
        three_stage_command = {
            "step_1_select_paper": 1 if sequence[0] == "Take the paper in your right hand" else 0,
            "step_2_fold_paper": 1 if sequence[1] == "Fold the paper in half" else 0,
            "step_3_place_paper": 1 if sequence[2] == "Place the paper on the table" else 0,
        }
    else:
        three_stage_command = {
            "step_1_select_paper": 1 if command_input["step1"] else 0,
            "step_2_fold_paper": 1 if command_input["step2"] else 0,
            "step_3_place_paper": 1 if command_input["step3"] else 0,
        }
    read_and_obey = 1 if state["language"]["readAndObey"] else 0
    written_sentence_score, sentence_review_flag = _score_sentence(state["language"]["writtenSentence"])
    if sentence_review_flag:
        review_flags.add("written_sentence_review")
    copy_design_score = 1 if state["language"]["copyDesignAnswer"] == MMSE_COPY_DESIGN_CORRECT_ANSWER else 0

    domain_scores = {
        "orientation_time": sum(orientation_time.values()),
        "orientation_place": sum(orientation_place.values()),
        "registration": registration["word_1"] + registration["word_2"] + registration["word_3"],
        "attention_calculation": attention_calculation["score"],
        "recall": sum(recall.values()),
        "language": (
            language_naming["score"]
            + repetition_score
            + sum(three_stage_command.values())
            + read_and_obey
            + written_sentence_score
            + copy_design_score
        ),
    }
    total_score = sum(domain_scores.values())
    interpretation = interpret_mmse(total_score)
    weak_areas = analyse_mmse_domains(domain_scores)

    return {
        "success": True,
        "responses": state,
        "orientation_time": orientation_time,
        "orientation_place": orientation_place,
        "registration": registration,
        "attention_calculation": attention_calculation,
        "recall": recall,
        "language_naming": language_naming,
        "language_repetition": repetition_score,
        "three_stage_command": three_stage_command,
        "read_and_obey": read_and_obey,
        "written_sentence": {
            "text": state["language"]["writtenSentence"],
            "score": written_sentence_score,
            "review_flag": sentence_review_flag,
        },
        "copy_design": {
            "method": state["language"]["copyDesignMethod"],
            "score": copy_design_score,
            "review_flag": False,
        },
        "domain_scores": domain_scores,
        "total_score": total_score,
        "max_score": MMSE_MAX_SCORE,
        "interpretation": interpretation["level"],
        "interpretation_detail": interpretation,
        "risk_flag": total_score <= 23,
        "weak_areas": weak_areas,
        "review_flags": sorted(review_flags),
        "limitations": [
            "remote_administration",
            "not_diagnostic",
            "language_and_education_may_affect_score",
        ],
        "missing_fields": [],
        "rule_based_summary": generate_rule_based_mmse_summary(total_score, interpretation["level"], weak_areas),
    }
