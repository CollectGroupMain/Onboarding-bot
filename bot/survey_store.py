from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

ALLOWED_TYPES = frozenset({"text", "number", "date", "email", "phone", "choice"})


def read_survey_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {
            "title": "",
            "welcome": "",
            "done_message": "",
            "questions": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def write_survey_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(
        suffix=".json", dir=str(path.parent), text=True
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def validate_survey_dict(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Root value must be a JSON object."
    questions = data.get("questions")
    if not isinstance(questions, list):
        return False, "Field 'questions' must be an array."
    if len(questions) == 0:
        return False, "Add at least one question."
    seen: set[str] = set()
    for i, q in enumerate(questions):
        if not isinstance(q, dict):
            return False, f"Question {i + 1}: expected an object."
        qid = str(q.get("id", "")).strip()
        if not qid:
            return False, f"Question {i + 1}: id must be non-empty."
        if qid in seen:
            return False, f"Duplicate id: {qid}"
        seen.add(qid)
        text = str(q.get("text", "")).strip()
        if not text:
            return False, f"Question {qid}: question text is required."
        t = str(q.get("type", "text")).strip()
        if t not in ALLOWED_TYPES:
            return (
                False,
                f"Question {qid}: unknown type '{t}'. Allowed: {', '.join(sorted(ALLOWED_TYPES))}.",
            )
        if t == "choice":
            ch = q.get("choices")
            if not isinstance(ch, list) or len(ch) == 0:
                return False, f"Question {qid}: type 'choice' requires a non-empty 'choices' array."
            for j, c in enumerate(ch):
                if not str(c).strip():
                    return False, f"Question {qid}: empty choice at position {j + 1}."
    for key in ("title", "welcome", "done_message"):
        if key in data and data[key] is not None and not isinstance(data[key], str):
            return False, f"Field '{key}' must be a string."
    return True, ""
