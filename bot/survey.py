from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    type: str
    spec: dict[str, Any]


@dataclass(frozen=True)
class Survey:
    title: str
    welcome: str
    done_message: str
    questions: list[Question]


def load_survey(path: Path) -> Survey:
    raw = json.loads(path.read_text(encoding="utf-8"))
    title = raw.get("title", "Survey")
    welcome = raw.get("welcome", "Please answer the following questions.")
    done_message = raw.get("done_message", "Thank you. Your responses have been saved.")
    questions = []
    for i, q in enumerate(raw.get("questions") or []):
        qid = q.get("id") or f"q_{i + 1}"
        text = q.get("text", "")
        qtype = q.get("type", "text")
        spec = {k: v for k, v in q.items() if k not in ("id", "text", "type")}
        questions.append(Question(id=qid, text=text, type=qtype, spec=spec))
    return Survey(title=title, welcome=welcome, done_message=done_message, questions=questions)
