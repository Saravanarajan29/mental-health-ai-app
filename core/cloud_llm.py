import json
import re
from typing import Any

from openai import OpenAI
from pydantic import BaseModel

from config.settings import get_settings


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _call_openai(system_prompt: str, user_prompt: str) -> str:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content or ""


def request_json(
    user_prompt: str,
    system_prompt: str,
    response_model: type[BaseModel],
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OpenAI API key is not configured.")

    latest_error: Exception | None = None
    prompt = user_prompt
    for _ in range(3):
        try:
            raw = _call_openai(system_prompt, prompt)
            payload = extract_json_object(raw)
            return response_model.model_validate(payload).model_dump()
        except Exception as exc:
            latest_error = exc
            prompt = f"{user_prompt}\n\nReminder: return valid JSON only with every required field."
    raise RuntimeError(f"Cloud JSON generation failed: {latest_error}") from latest_error
