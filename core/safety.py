CRISIS_SIGNPOSTING_MESSAGE = (
    "If you are in immediate danger please contact local emergency services or a crisis support line."
)

IMMINENT_RISK_KEYWORDS = {
    "suicide",
    "kill myself",
    "want to die",
    "self harm",
    "hurt myself",
    "harm myself",
    "end my life",
}


def contains_imminent_risk(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in IMMINENT_RISK_KEYWORDS)
