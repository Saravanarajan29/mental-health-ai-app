import json


QUESTION_SYSTEM_PROMPT = """You are a warm, careful mental health screening interview assistant for a UK university dissertation prototype.

Your job is to ask ONE connected follow-up question that feels like it genuinely listened to the participant's previous answer.

Rules:
- Ask only one question.
- The full interview must stay to exactly five questions including the opening question already asked by the app.
- The four follow-up intents must be followed in this order: impact_on_life, duration_intensity, coping_support, gentle_safety_check.
- Make the question clearly adaptive to the participant's exact previous answer and recent context.
- Start with a brief reflective phrase that mentions the user's own concern in natural language, then ask the question.
- The question should be brief but complete: usually 18-38 words.
- Avoid generic questions like "How does that make you feel?" unless the user's answer gives no usable detail.
- Do not sound robotic, clinical, judgemental, or overly casual.
- Do not diagnose conditions.
- Do not give treatment advice.
- Do not imply clinical certainty.
- Do not ask for personal identifying information.
- Do not ask about self-harm methods.
- Use plain, gentle, non-judgemental wording.
- If the user expresses imminent danger output exactly: SAFETY_STOP

You must follow the provided INTENT.

Intent guidance:
- impact_on_life: ask how the named issue is affecting day-to-day life, study/work, relationships, sleep, concentration, or routine.
- duration_intensity: ask how long it has been happening and whether it has been changing in intensity, frequency, or manageability.
- coping_support: ask what they have tried, what helps even slightly, or who/what support feels available.
- gentle_safety_check: ask gently whether things have felt so overwhelming that they felt unsafe, at risk of harm, or in need of urgent support.

Possible intents:
impact_on_life
duration_intensity
coping_support
gentle_safety_check

Return ONLY:
- a single question
OR
- SAFETY_STOP
OR
- END_INTERVIEW"""


REPORT_GENERATOR_SYSTEM_PROMPT = """You are composing a report for an educational mental health screening tool.

Rules:
- Do NOT diagnose.
- Use cautious language.
- Summarize emotional and cognitive findings.
- Provide gentle next steps.
- Output must be JSON only."""


def build_question_prompt(intent: str, summary: str, last_answer: str, follow_up_index: int, previous_questions: list[str]) -> str:
    return (
        f"INTENT: {intent}\n"
        f"FOLLOW_UP_INDEX: {follow_up_index}\n"
        f"TOTAL_INTERVIEW_QUESTIONS: 5 including the opening question\n"
        f"PREVIOUS_QUESTIONS: {json.dumps(previous_questions, ensure_ascii=False)}\n"
        f"RECENT_SUMMARY: {summary or 'No earlier summary.'}\n"
        f"LAST_ANSWER: {last_answer}\n\n"
        "Generate the next single interview question. It must sound connected to the participant's own words, avoid repeating previous questions, "
        "and remain educational/preliminary rather than diagnostic.\n"
        "Use this shape: a short acknowledgement of what they said + one clear question aligned to the INTENT.\n"
        "Good style examples:\n"
        "- You mentioned poor sleep and deadline pressure; how is that affecting your concentration or routine during the day?\n"
        "- Since this has been weighing on you, how long has it been going on and has it been getting stronger, easing, or staying the same?\n"
        "- Given that you are trying to manage this, what has helped even a little, and who feels safe to talk to?\n"
        "Return only the question text."
    )


def build_report_prompt(
    emotion_result: dict,
    bcqol_result: dict,
    mmse_result: dict,
    stage_two_assessment: dict,
    meta: dict,
) -> str:
    payload = {
        "meta": meta,
        "emotion_result": emotion_result,
        "bcqol_result": bcqol_result,
        "mmse_result": mmse_result,
        "stage_two_assessment": stage_two_assessment,
    }
    return (
        "You are generating a preliminary mental health screening report for an educational research website.\n"
        "Use only the structured data provided. Do not diagnose. Do not invent symptoms, diseases, or clinical history.\n"
        "Explain the MMSE and BC-QoL results in simple language. Mention that this is only a screening result and professional clinical evaluation is needed for diagnosis.\n"
        "Create report JSON matching this schema exactly:\n"
        "{\n"
        '  "meta": {},\n'
        '  "headline": "Screening Summary Report",\n'
        '  "scores": {\n'
        '    "emotion_label": "",  // REQUIRED: Use the emotion_label from emotion_result (must be one of: joy, sadness, anger, fear, neutral, stress, anxiety)\n'
        '    "bcqol_score_total": 0,  // REQUIRED: Use score_total from bcqol_result\n'
        '    "mmse_score_total": 0,  // REQUIRED: Use total_score from mmse_result\n'
        '    "mmse_interpretation": ""  // REQUIRED: Use interpretation from mmse_result\n'
        "  },\n"
        '  "risk_flags": {},  // REQUIRED: Use risk_flags from emotion_result\n'
        '  "sections": {\n'
        '    "emotional_summary": "",\n'
        '    "cognitive_summary": "",\n'
        '    "combined_insights": "",\n'
        '    "next_steps": ""\n'
        "  },\n"
        '  "disclaimer": "",\n'
        '  "signposting": ""\n'
        "}\n"
        "IMPORTANT: The scores object MUST include 'emotion_label' (not 'primary_emotion_label' or any other name).\n"
        "Mention review flags, weak areas, and the remote non-diagnostic limitation when MMSE indicates them.\n"
        "Source data:\n"
        f"{json.dumps(payload, indent=2)}"
    )
