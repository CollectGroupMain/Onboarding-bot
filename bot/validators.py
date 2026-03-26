import re
from datetime import datetime

from bot.survey import Question


def validate_answer(question: Question, raw: str) -> tuple[bool, str | None, str | None]:
    """Returns (ok, normalized_value, error_message)."""
    t = question.type
    spec = question.spec
    raw = raw.strip() if raw is not None else ""

    if t == "text":
        if not raw:
            return False, None, "Please enter a non-empty answer."
        mn = spec.get("min_length")
        mx = spec.get("max_length")
        if mn is not None and len(raw) < int(mn):
            return False, None, f"Answer is too short (min {mn} characters)."
        if mx is not None and len(raw) > int(mx):
            return False, None, f"Answer is too long (max {mx} characters)."
        pattern = spec.get("regex")
        if pattern and not re.search(pattern, raw):
            return False, None, "Answer does not match the required format."
        return True, raw, None

    if t == "number":
        if not raw:
            return False, None, "Please enter a number."
        try:
            val = float(raw.replace(",", "."))
        except ValueError:
            return False, None, "Please enter a valid number."
        if spec.get("integer_only") and not val.is_integer():
            return False, None, "Please enter a whole number."
        if spec.get("integer_only"):
            val = int(val)
        mn, mx = spec.get("min"), spec.get("max")
        if mn is not None and val < float(mn):
            return False, None, f"Value must be at least {mn}."
        if mx is not None and val > float(mx):
            return False, None, f"Value must be at most {mx}."
        return True, str(val), None

    if t == "date":
        if not raw:
            return False, None, "Please enter a date."
        fmt = spec.get("format", "%Y-%m-%d")
        try:
            datetime.strptime(raw, fmt)
        except ValueError:
            hint = fmt.replace("%d", "DD").replace("%m", "MM").replace("%Y", "YYYY")
            return False, None, f"Use date format: {hint}"
        return True, raw, None

    if t == "email":
        if not raw:
            return False, None, "Please enter an email."
        pat = spec.get("pattern") or r"^[\w.+-]+@[\w-]+\.[\w.-]+$"
        if not re.match(pat, raw, re.I):
            return False, None, "Please enter a valid email address."
        return True, raw.lower(), None

    if t == "phone":
        if not raw:
            return False, None, "Please enter a phone number."
        digits = re.sub(r"\D", "", raw)
        mn = int(spec.get("min_digits", 10))
        mx = int(spec.get("max_digits", 15))
        if len(digits) < mn or len(digits) > mx:
            return False, None, f"Phone should have between {mn} and {mx} digits."
        return True, raw, None

    if t == "choice":
        return False, None, "Please use the buttons to answer this question."

    return False, None, f"Unknown question type: {t}"


def validate_choice(question: Question, choice_index: int) -> tuple[bool, str | None, str | None]:
    choices = question.spec.get("choices") or []
    if not choices:
        return False, None, "No choices configured."
    if choice_index < 0 or choice_index >= len(choices):
        return False, None, "Invalid choice."
    return True, str(choices[choice_index]), None
