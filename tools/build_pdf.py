#!/usr/bin/env python3
"""Build the Round 1 proposal PDF from docs/round1.md.

The ten numbered sections are the ten substantive responses. Their answer
text (headings excluded) must stay within 500 English words; the
third-party license and tool sections after them are excluded from the
limit by the Official Rules. The PDF must stay within 1 MB.

Usage: python tools/build_pdf.py [--source docs/round1.md] [--out dist/round1.pdf]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO / "docs" / "round1.md"
DEFAULT_OUT = REPO / "dist" / "round1.pdf"
WORD_LIMIT = 500
SIZE_LIMIT = 1024 * 1024
OPEN_BLANK = re.compile(r"\[JOSHUA TO FILL[^\]]*\]")

# The ten questions, in order, worded as on the Official Rules page.
QUESTIONS = [
    "One sentence: What does the Skill do?",
    "Who is the target user and problem?",
    "What is your proposed solution?",
    "What is the Core User Flow?",
    "What substantive difference does your idea offer compared with existing tools or conventional AI solutions?",
    "Which UGREEN AI NAS capabilities will be used, and at which step in the workflow?",
    "What was your technical approach?",
    "What is the current development status?",
    "What is your final validation plan?",
    "Are there any known limitations of your Project?",
]

SECTION = re.compile(r"^## (\d+)\. (.+)$")


def parse(source: str):
    """Split the source into (title, preamble lines, sections). Each section is (heading, number or None, body lines)."""
    lines = source.splitlines()
    title = ""
    preamble: list[str] = []
    sections: list[tuple[str, int | None, list[str]]] = []
    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            match = SECTION.match(line)
            number = int(match.group(1)) if match else None
            heading = match.group(2).strip() if match else line[3:].strip()
            sections.append((heading, number, []))
            continue
        if sections:
            sections[-1][2].append(line)
        else:
            preamble.append(line)
    return title, preamble, sections


def answers(source: str) -> dict[int, str]:
    _, _, sections = parse(source)
    return {number: "\n".join(body).strip() for _, number, body in sections if number is not None}


def _words(text: str, split_compounds: bool) -> list[str]:
    text = re.sub(r"[*_`#>]", " ", text)
    if split_compounds:
        text = re.sub(r"[-/–—]", " ", text)
    return [token for token in text.split() if re.search(r"[A-Za-z0-9]", token)]


def word_count(source: str, split_compounds: bool = False) -> int:
    """Words in the ten answers. split_compounds also splits hyphenated and slashed terms (a stricter count)."""
    return sum(len(_words(text, split_compounds)) for text in answers(source).values())


def validate(source: str) -> list[str]:
    problems = []
    _, _, sections = parse(source)
    numbered = [(number, heading) for heading, number, _ in sections if number is not None]
    if [n for n, _ in numbered] != list(range(1, 11)):
        problems.append(f"expected sections 1 to 10 in order, found {[n for n, _ in numbered]}")
    for (number, heading), question in zip(numbered, QUESTIONS):
        if heading != question:
            problems.append(f"section {number} heading differs from the rules wording: {heading!r}")
    for number, text in answers(source).items():
        if not text:
            problems.append(f"section {number} has no answer")
    first = answers(source).get(1, "")
    if first.count(". ") > 0 or first.count(".") > 1:
        problems.append("answer 1 must be one sentence")
    for limit_name, count in (("plain", word_count(source)), ("strict", word_count(source, True))):
        if count > WORD_LIMIT:
            problems.append(f"{limit_name} word count {count} exceeds {WORD_LIMIT}")
    return problems


def _inline(text: str) -> str:
    # The built-in PDF fonts use WinAnsi encoding, which has no arrow glyph.
    text = text.replace("→", "»")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", text)
    return text


def render(source: str, out: Path) -> Path:
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5, leading=12.5, alignment=TA_LEFT, spaceAfter=4)
    small = ParagraphStyle("Small", parent=body, fontSize=8.5, leading=11)
    heading = ParagraphStyle("Q", parent=body, fontName="Helvetica-Bold", fontSize=10, leading=13, spaceBefore=6, spaceAfter=2, keepWithNext=1)
    title_style = ParagraphStyle("T", parent=body, fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=4)

    title, preamble, sections = parse(source)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out), pagesize=LETTER, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch, title=f"{title} - Round 1 Proposal",
        author="Joshua Yeung", subject="UGREEN Hackathon 2026 on AI NAS, Round 1", creator="",
        producer="",
    )
    story = [Paragraph(_inline(title), title_style)]
    for line in preamble:
        if line.strip():
            story.append(Paragraph(_inline(line.strip()), small))
    story.append(Spacer(1, 4))

    for head, number, lines in sections:
        label = f"{number}. {head}" if number is not None else head
        story.append(Paragraph(_inline(label), heading))
        style = body if number is not None else small
        bullets: list[str] = []
        paragraph: list[str] = []

        def flush_paragraph():
            if paragraph:
                story.append(Paragraph(_inline(" ".join(paragraph)), style))
                paragraph.clear()

        def flush_bullets():
            if bullets:
                story.append(ListFlowable(
                    [ListItem(Paragraph(_inline(b), style), leftIndent=10) for b in bullets],
                    bulletType="bullet", start="•", leftIndent=10, bulletFontSize=7,
                ))
                bullets.clear()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- "):
                flush_paragraph()
                bullets.append(stripped[2:])
            elif not stripped:
                flush_paragraph()
                flush_bullets()
            else:
                flush_bullets()
                paragraph.append(stripped)
        flush_paragraph()
        flush_bullets()

    count = word_count(source)
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"Word count of the ten responses: {count} (limit {WORD_LIMIT}).", small))
    doc.build(story)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the Round 1 proposal PDF.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    source = args.source.read_text(encoding="utf-8")
    problems = validate(source)
    for problem in problems:
        print(f"ERROR {problem}")
    if problems:
        return 1
    out = render(source, args.out)
    size = out.stat().st_size
    print(f"words: {word_count(source)} (strict count {word_count(source, True)}, limit {WORD_LIMIT})")
    print(f"built {out} ({size} bytes, limit {SIZE_LIMIT})")
    if size > SIZE_LIMIT:
        print("ERROR PDF exceeds 1 MB")
        return 1
    blanks = OPEN_BLANK.findall(source)
    if blanks:
        print(f"WARNING {len(blanks)} [JOSHUA TO FILL] blank(s) still open in {args.source.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
