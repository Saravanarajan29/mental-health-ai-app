import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from core.safety import contains_imminent_risk


EMOTION_LABELS = ["joy", "sadness", "anger", "fear", "neutral", "stress", "anxiety"]

EMOTION_CUES = {
    "joy": {
        "good": 1.0,
        "fine": 0.8,
        "hopeful": 1.4,
        "better": 1.1,
        "happy": 1.4,
        "calm": 1.0,
        "supported": 1.2,
        "positive": 1.1,
        "relieved": 1.0,
        "okay": 0.7,
    },
    "sadness": {
        "sad": 1.5,
        "feel down": 1.4,
        "low mood": 1.4,
        "hopeless": 1.8,
        "crying": 1.4,
        "empty": 1.2,
        "depressed": 1.8,
        "worthless": 1.7,
        "no motivation": 1.3,
    },
    "anger": {
        "angry": 1.6,
        "anger": 1.5,
        "irritated": 1.3,
        "frustrated": 1.3,
        "furious": 1.8,
        "annoyed": 1.1,
        "resentful": 1.4,
        "rage": 1.7,
    },
    "fear": {
        "afraid": 1.6,
        "scared": 1.6,
        "fear": 1.4,
        "fearful": 1.5,
        "terrified": 1.9,
        "unsafe": 1.5,
        "threatened": 1.5,
        "worried something bad": 1.3,
    },
    "stress": {
        "stress": 1.5,
        "stressed": 1.6,
        "overwhelmed": 1.7,
        "burnout": 1.7,
        "burned out": 1.7,
        "pressure": 1.3,
        "too much": 1.2,
        "exhausted": 1.2,
        "deadline": 1.0,
    },
    "anxiety": {
        "anxious": 1.7,
        "anxiety": 1.7,
        "worry": 1.4,
        "worried": 1.4,
        "panic": 1.8,
        "nervous": 1.4,
        "restless": 1.1,
        "racing thoughts": 1.5,
        "on edge": 1.4,
    },
}

NEGATION_TERMS = {"not", "no", "never", "without", "hardly"}


class RiskFlags(BaseModel):
    high_distress: bool = False
    self_harm_ideation: bool = False
    needs_human_followup: bool = False


class EmotionResult(BaseModel):
    labels: list[str] = Field(default_factory=lambda: EMOTION_LABELS.copy())
    emotion_label: str
    emotion_probs: dict[str, float]
    summary: str
    risk_flags: RiskFlags
    confidence_note: str
    generation_source: str = "cloud"
    generation_note: str = ""

    @field_validator("emotion_label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        if value not in EMOTION_LABELS:
            return "neutral"
        return value

    @model_validator(mode="after")
    def normalize_probabilities(self) -> "EmotionResult":
        normalized: dict[str, float] = {label: 0.0 for label in EMOTION_LABELS}
        for label, value in self.emotion_probs.items():
            if label in normalized:
                normalized[label] = max(0.0, float(value))

        total = sum(normalized.values())
        if total <= 0:
            normalized["neutral"] = 1.0
            total = 1.0

        self.emotion_probs = {
            label: round(value / total, 4)
            for label, value in normalized.items()
        }

        rounded_total = sum(self.emotion_probs.values())
        if rounded_total != 1.0:
            adjustment = round(1.0 - rounded_total, 4)
            self.emotion_probs[self.emotion_label] = round(
                self.emotion_probs[self.emotion_label] + adjustment,
                4,
            )
        self.labels = EMOTION_LABELS.copy()
        return self


def _extract_answer_text(answers_text: str) -> str:
    """Use only participant answers when a Q/A transcript is provided."""
    lines = str(answers_text or "").splitlines()
    answer_blocks: list[str] = []
    current: list[str] = []
    collecting_answer = False

    for line in lines:
        answer_match = re.match(r"^\s*A\d+\s*:\s*(.*)$", line, flags=re.IGNORECASE)
        question_match = re.match(r"^\s*Q\d+\s*:", line, flags=re.IGNORECASE)
        if answer_match:
            if current:
                answer_blocks.append(" ".join(current).strip())
            current = [answer_match.group(1).strip()]
            collecting_answer = True
            continue
        if question_match:
            if current:
                answer_blocks.append(" ".join(current).strip())
            current = []
            collecting_answer = False
            continue
        if collecting_answer:
            current.append(line.strip())

    if current:
        answer_blocks.append(" ".join(current).strip())
    return "\n".join(block for block in answer_blocks if block) or str(answers_text or "")


def _cue_is_negated(text: str, start_index: int) -> bool:
    prefix = text[max(0, start_index - 45):start_index]
    words = re.findall(r"[a-z']+", prefix)
    return any(word in NEGATION_TERMS for word in words[-4:])


def _count_cue(text: str, cue: str) -> int:
    pattern = r"(?<![a-z])" + re.escape(cue) + r"(?![a-z])"
    count = 0
    for match in re.finditer(pattern, text):
        if not _cue_is_negated(text, match.start()):
            count += 1
    return count


def _score_emotions(answer_only_text: str) -> dict[str, float]:
    lowered = " ".join(answer_only_text.lower().split())
    scores = {label: 0.0 for label in EMOTION_LABELS}
    for label, cues in EMOTION_CUES.items():
        for cue, weight in cues.items():
            scores[label] += _count_cue(lowered, cue) * weight
    return scores


def _probabilities_from_scores(scores: dict[str, float]) -> tuple[str, dict[str, float]]:
    evidence_scores = {label: scores.get(label, 0.0) for label in EMOTION_LABELS if label != "neutral"}
    best_label, best_score = max(evidence_scores.items(), key=lambda item: item[1])
    if best_score <= 0:
        return "neutral", {
            "joy": 0.06,
            "sadness": 0.08,
            "anger": 0.05,
            "fear": 0.06,
            "neutral": 0.62,
            "stress": 0.07,
            "anxiety": 0.06,
        }

    raw = {
        "joy": 0.04,
        "sadness": 0.06,
        "anger": 0.04,
        "fear": 0.05,
        "neutral": max(0.18, 0.42 - min(best_score, 4.0) * 0.04),
        "stress": 0.06,
        "anxiety": 0.06,
    }
    for label, score in evidence_scores.items():
        raw[label] += min(score, 5.0) * 0.28
    return best_label, raw


def _fallback_emotion_result(answers_text: str) -> dict[str, Any]:
    answer_only_text = _extract_answer_text(answers_text)
    scores = _score_emotions(answer_only_text)
    label, probabilities = _probabilities_from_scores(scores)

    risk = contains_imminent_risk(answers_text)
    summary_map = {
        "anxiety": "The responses suggest prominent worry or nervous tension, with anxiety-related language appearing more often than other emotional cues.",
        "sadness": "The responses suggest lowered mood or discouragement may be present, based on the emotional wording used during the interview.",
        "anger": "The responses suggest frustration or anger may be a meaningful theme in the current situation.",
        "fear": "The responses suggest fear or feeling unsafe may be present and should be interpreted with care.",
        "stress": "The responses suggest current strain or overload may be a meaningful theme, with stress-related language appearing across answers.",
        "joy": "The responses suggest a generally stable or positive tone, although this remains only a screening-oriented interpretation.",
        "neutral": "The responses did not strongly cluster around a single emotional category, so the result remains broadly neutral and low-confidence.",
    }
    payload = EmotionResult(
        emotion_label=label,
        emotion_probs=probabilities,
        summary=summary_map[label],
        risk_flags=RiskFlags(
            high_distress=label in {"sadness", "stress", "anxiety"},
            self_harm_ideation=risk,
            needs_human_followup=risk or label in {"sadness", "stress", "anxiety"},
        ),
        confidence_note="This is a preliminary screening summary. Please review with a qualified professional if concerns remain.",
        generation_source="fallback",
        generation_note="Heuristic emotional summary has been generated.",
    )
    return payload.model_dump()


def classify_emotion_fast(answers_text: str) -> dict[str, Any]:
    return _fallback_emotion_result(answers_text)
