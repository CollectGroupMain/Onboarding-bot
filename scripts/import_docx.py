"""
Build a draft data/survey.json from a Word document: each non-empty paragraph becomes a text question.
Edit the JSON after import to set types (number, date, email, choice, etc.).

Usage:
  python scripts/import_docx.py "C:\\path\\to\\file.docx" -o data/survey.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Import survey questions from .docx")
    parser.add_argument("docx", type=Path, help="Path to .docx file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/survey.json"),
        help="Output survey JSON path",
    )
    args = parser.parse_args()
    if not args.docx.is_file():
        print(f"File not found: {args.docx}", file=sys.stderr)
        sys.exit(1)
    try:
        from docx import Document
    except ImportError:
        print("Install python-docx: pip install python-docx", file=sys.stderr)
        sys.exit(1)
    doc = Document(str(args.docx))
    questions = []
    for p in doc.paragraphs:
        text = (p.text or "").strip()
        if not text:
            continue
        questions.append(
            {
                "id": f"q_{len(questions) + 1}",
                "text": text,
                "type": "text",
            }
        )
    survey = {
        "title": "Imported survey",
        "welcome": "Please answer the following questions. Send /cancel to stop.",
        "done_message": "Thank you. Your responses have been saved.",
        "questions": questions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(survey, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(questions)} questions to {args.output}")


if __name__ == "__main__":
    main()
