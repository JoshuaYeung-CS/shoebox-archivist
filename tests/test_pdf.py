"""Tests for the Round 1 proposal source and PDF build."""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import build_pdf as bp  # noqa: E402

SOURCE = (REPO / "docs" / "round1.md").read_text(encoding="utf-8")


def test_source_is_valid():
    assert bp.validate(SOURCE) == []


def test_ten_answers_within_500_words():
    assert bp.word_count(SOURCE) <= 500
    assert bp.word_count(SOURCE, split_compounds=True) <= 500


def test_headings_use_the_official_wording_in_order():
    _, _, sections = bp.parse(SOURCE)
    numbered = [(n, h) for h, n, _ in sections if n is not None]
    assert numbered == list(enumerate(bp.QUESTIONS, start=1))


def test_license_and_tool_sections_are_present_and_excluded():
    _, _, sections = bp.parse(SOURCE)
    extra = [h for h, n, _ in sections if n is None]
    assert any("Third-party components and licenses" in h for h in extra)
    assert any("AI tools used" in h for h in extra)
    assert "uliya-skill-kit-0.7.3-en.zip" in SOURCE


def test_word_count_ignores_headings_and_extra_sections():
    padded = SOURCE + "\n## Notes\n\n" + "word " * 1000
    assert bp.word_count(padded) == bp.word_count(SOURCE)


def test_over_limit_is_rejected():
    long_answer = SOURCE.replace("## 2. Who is", "word " * 600 + "\n\n## 2. Who is", 1)
    assert any("exceeds" in p for p in bp.validate(long_answer))


def test_changed_heading_is_rejected():
    bad = SOURCE.replace("## 4. What is the Core User Flow?", "## 4. Main flow")
    assert any("heading differs" in p for p in bp.validate(bad))


def test_missing_section_is_rejected():
    start = SOURCE.index("## 9.")
    end = SOURCE.index("## 10.")
    assert any("expected sections" in p for p in bp.validate(SOURCE[:start] + SOURCE[end:]))


def test_first_answer_must_be_one_sentence():
    bad = SOURCE.replace("until the user approves.", "until the user approves. It is great.", 1)
    assert any("one sentence" in p for p in bp.validate(bad))


def test_pdf_builds_under_one_megabyte(tmp_path):
    pypdf = pytest.importorskip("pypdf")
    out = bp.render(SOURCE, tmp_path / "round1.pdf")
    assert out.stat().st_size <= bp.SIZE_LIMIT
    text = "".join(page.extract_text() for page in pypdf.PdfReader(str(out)).pages)
    for question in bp.QUESTIONS:
        assert question.split()[0] in text
    assert "Third-party components" in text


def test_main_succeeds(tmp_path):
    assert bp.main(["--out", str(tmp_path / "r1.pdf")]) == 0
