def extract_json(raw: str) -> str:
    """
    Robustly extract a JSON object or array from a Claude response.
    Handles markdown code fences and preamble text.
    """
    raw = raw.strip()

    # Strip markdown code fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    # Prefer array if it appears first
    bracket = raw.find("[")
    brace = raw.find("{")

    if bracket != -1 and (brace == -1 or bracket < brace):
        start, end = bracket, raw.rfind("]") + 1
    else:
        start, end = brace, raw.rfind("}") + 1

    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in response: {raw[:200]}")

    return raw[start:end]