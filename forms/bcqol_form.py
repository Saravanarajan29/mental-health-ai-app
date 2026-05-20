BCQOL_QUESTIONS = [
    "How would you rate your memory today?",
    "How often do you feel mentally fatigued?",
    "How well are you able to concentrate?",
    "How satisfied are you with your cognitive functioning?",
]


def compute_bcqol_result(responses: list[int]) -> dict:
    cleaned = [min(5, max(1, int(response))) for response in responses]
    total_score = sum(cleaned)
    max_possible_score = len(BCQOL_QUESTIONS) * 5
    normalized_score = round((total_score / max_possible_score) * 100, 2)
    average_score = total_score / len(cleaned)
    if normalized_score >= 75:
        interpretation = "relatively preserved cognitive quality of life"
    elif normalized_score >= 50:
        interpretation = "mild reduction in cognitive quality of life"
    else:
        interpretation = "reduced cognitive quality of life"

    domain_map = [
        ("memory confidence", cleaned[0]),
        ("mental fatigue", cleaned[1]),
        ("concentration", cleaned[2]),
        ("daily cognitive confidence", cleaned[3]),
    ]
    key_domains = [name for name, value in domain_map if value <= 3] or [name for name, _ in domain_map[:2]]
    return {
        "responses": cleaned,
        "score_total": normalized_score,
        "scale": "0-100",
        "raw_total": total_score,
        "max_possible_score": max_possible_score,
        "average_item_score": round(average_score, 2),
        "interpretation": interpretation,
        "key_domains": key_domains,
    }
