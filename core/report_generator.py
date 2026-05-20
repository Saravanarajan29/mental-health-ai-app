from typing import Any

from pydantic import BaseModel

from core.safety import CRISIS_SIGNPOSTING_MESSAGE


class ReportSections(BaseModel):
    emotional_summary: str
    cognitive_summary: str
    combined_insights: str
    next_steps: str


class ReportJSON(BaseModel):
    meta: dict[str, Any]
    headline: str
    scores: dict[str, Any]
    risk_flags: dict[str, Any]
    sections: ReportSections
    disclaimer: str
    signposting: str
    generation_source: str = "cloud"
    generation_note: str = ""


def _fallback_report(emotion_result: dict, bcqol_result: dict, meta: dict) -> dict[str, Any]:
    mmse_result = meta.get("mmse_result", {})
    risk_flags = emotion_result.get("risk_flags", {})
    weak_areas = mmse_result.get("weak_areas", [])
    mmse_interpretation = mmse_result.get("interpretation", "MMSE screening was unavailable.")
    mmse_score = mmse_result.get("total_score")
    payload = ReportJSON(
        meta=meta,
        headline="Screening Summary Report",
        scores={
            "emotion_label": emotion_result.get("emotion_label", "neutral"),
            "bcqol_score_total": bcqol_result.get("score_total"),
            "mmse_score_total": mmse_score,
            "mmse_interpretation": mmse_interpretation,
        },
        risk_flags=risk_flags,
        sections=ReportSections(
            emotional_summary=emotion_result.get(
                "summary",
                "Emotional results were generated with cautious language and should be reviewed as screening guidance only.",
            ),
            cognitive_summary=(
                f"The BC-QoL score suggests {bcqol_result.get('interpretation', 'a self-reported view of cognitive quality of life')}. "
                f"The MMSE result is {mmse_interpretation.lower()}"
                + (f" with weaker areas in {', '.join(weak_areas)}." if weak_areas else ".")
            ),
            combined_insights=(
                "This prototype combines conversational, quality-of-life, and cognitive screening signals to support educational screening."
            ),
            next_steps=(
                "If symptoms feel persistent, worsening, or disruptive, or if the MMSE score raised concern, consider discussing them with a qualified clinician."
            ),
        ),
        disclaimer=(
            "This report is an educational screening output and is not a diagnosis or a substitute for professional care."
        ),
        signposting=CRISIS_SIGNPOSTING_MESSAGE if risk_flags.get("self_harm_ideation") else "Consider local support resources if distress continues.",
        generation_source="fallback",
        generation_note="Screening report has been generated for review.",
    )
    return payload.model_dump()


def compose_report_llm(
    emotion_result: dict,
    bcqol_result: dict,
    mmse_result: dict,
    stage_two_assessment: dict,
    meta: dict,
) -> dict[str, Any]:
    enriched_meta = dict(meta)
    enriched_meta["mmse_result"] = mmse_result
    enriched_meta["stage_two_assessment"] = stage_two_assessment
    try:
        from core.cloud_llm import request_json
        from core.prompts import REPORT_GENERATOR_SYSTEM_PROMPT, build_report_prompt

        result = request_json(
            user_prompt=build_report_prompt(
                emotion_result,
                bcqol_result,
                mmse_result,
                stage_two_assessment,
                enriched_meta,
            ),
            system_prompt=REPORT_GENERATOR_SYSTEM_PROMPT,
            response_model=ReportJSON,
        )
        # Normalize emotion_label in scores - handle LLM variations
        scores = result.get("scores", {})
        if "emotion_label" not in scores:
            # Try common variations
            emotion_label = (
                scores.get("primary_emotion_label")
                or scores.get("emotion")
                or emotion_result.get("emotion_label", "neutral")
            )
            scores["emotion_label"] = emotion_label
        # Ensure emotion_label is valid
        valid_labels = ["joy", "sadness", "anger", "fear", "neutral", "stress", "anxiety"]
        if scores.get("emotion_label", "").lower() not in valid_labels:
            scores["emotion_label"] = emotion_result.get("emotion_label", "neutral")
        if "bcqol_score_total" not in scores:
            scores["bcqol_score_total"] = bcqol_result.get("score_total")
        if "mmse_score_total" not in scores:
            scores["mmse_score_total"] = mmse_result.get("total_score")
        if "mmse_interpretation" not in scores:
            scores["mmse_interpretation"] = mmse_result.get("interpretation")
        result["scores"] = scores
        result["generation_source"] = "cloud"
        result["generation_note"] = "Screening report has been generated for review."
        return ReportJSON.model_validate(result).model_dump()
    except Exception:
        return _fallback_report(emotion_result, bcqol_result, enriched_meta)
