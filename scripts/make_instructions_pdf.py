"""
Собирает PDF с инструкцией (кириллица). На Windows используется Arial из системы.
Установка: pip install fpdf2
Запуск из корня проекта: python scripts/make_instructions_pdf.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "docs" / "Инструкция_Preboarding_Bot.md"
OUT_PATH = ROOT / "docs" / "Инструкция_Preboarding_Bot.pdf"


def _find_unicode_font() -> tuple[str, str]:
    """Return (family_name, path) for a TTF with Cyrillic."""
    candidates = [
        (r"C:\Windows\Fonts\arial.ttf", "Arial"),
        (r"C:\Windows\Fonts\arialuni.ttf", "ArialUni"),
        (r"C:\Windows\Fonts\segoeui.ttf", "SegoeUI"),
    ]
    for path, name in candidates:
        p = Path(path)
        if p.is_file():
            return name, str(p)
    return "", ""


def md_to_plain_lines(text: str) -> list[tuple[str, int]]:
    """
    Parse minimal markdown: # / ## headers, ---, tables skipped to lines, **bold** stripped.
    Yields (line, level) where level 0=body, 1=h1, 2=h2.
    """
    lines_out: list[tuple[str, int]] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            lines_out.append(("", 0))
            continue
        if line.strip() == "---":
            lines_out.append(("", 0))
            continue
        if line.startswith("# "):
            lines_out.append((line[2:].strip(), 1))
            continue
        if line.startswith("## "):
            lines_out.append((line[3:].strip(), 2))
            continue
        if line.startswith("|"):
            continue
        # strip ** and markdown links [text](url) -> text
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
        if s.strip().startswith("* "):
            s = "• " + s.strip()[2:].strip()
        lines_out.append((s, 0))
    return lines_out


def build_pdf(font_path: str, font_family: str) -> None:
    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos
    except ImportError:
        print("Установите: pip install fpdf2", file=sys.stderr)
        sys.exit(1)

    text = MD_PATH.read_text(encoding="utf-8")
    chunks = md_to_plain_lines(text)

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(16, 16, 16)
    pdf.add_font(font_family, "", font_path)
    pdf.add_page()

    def mcell(txt: str, size: int, line_h: int) -> None:
        pdf.set_font(font_family, "", size)
        pdf.multi_cell(
            pdf.epw,
            line_h,
            txt,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
            wrapmode="CHAR",
        )

    for line, level in chunks:
        if level == 1:
            pdf.ln(4)
            mcell(line, 15, 8)
            pdf.ln(1)
        elif level == 2:
            pdf.ln(3)
            mcell(line, 12, 7)
            pdf.ln(0.5)
        else:
            if not line:
                pdf.ln(3)
            else:
                mcell(line, 11, 6)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT_PATH))
    print(f"PDF сохранён: {OUT_PATH}")


def main() -> None:
    if not MD_PATH.is_file():
        print(f"Нет файла: {MD_PATH}", file=sys.stderr)
        sys.exit(1)
    family, path = _find_unicode_font()
    if not path:
        print(
            "Не найден шрифт с кириллицей (Arial/Segoe в Windows). "
            "Укажите путь к .ttf в скрипте или установите шрифт.",
            file=sys.stderr,
        )
        sys.exit(1)
    build_pdf(path, family)


if __name__ == "__main__":
    main()
