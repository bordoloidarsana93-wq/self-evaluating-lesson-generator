"""The six deterministic code checks.

These are fast, free and 100% repeatable, so anything that can be measured with code is
measured here instead of asking an LLM. Each check takes the lesson and returns a
`CheckResult` with a reason, evidence and a fix the reviser can act on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .config import Thresholds
from .knowledge import Knowledge
from .state import CheckResult, make_result
from .text_utils import find_section, prose_lines, readability, snippet, split_sections, strip_code_blocks, words


@dataclass(frozen=True)
class CodeCheck:
    """A named code check. `run(lesson, knowledge, thresholds)` returns the result."""

    id: str
    name: str
    run: Callable[[str, Knowledge, Thresholds], CheckResult]


def check_sections(lesson: str, kb: Knowledge, th: Thresholds) -> CheckResult:
    """Every required section exists as a `## ` heading and has text under it."""
    sections = split_sections(lesson)
    missing = [title for title in kb.required_sections if not find_section(sections, title)]
    if not missing:
        return make_result("sections", "Required sections", "code", True, "All required sections are present.")
    return make_result(
        "sections", "Required sections", "code", False,
        reason=f"{len(missing)} required section(s) missing or empty.",
        evidence="Missing: " + ", ".join(missing),
        fix="Add these sections as '## ' headings with content: " + ", ".join(missing),
    )


def check_word_count(lesson: str, kb: Knowledge, th: Thresholds) -> CheckResult:
    """The lesson is long enough to teach properly but short enough to finish."""
    count = len(words(" ".join(prose_lines(lesson))))
    if th.min_words <= count <= th.max_words:
        return make_result("word_count", "Word count", "code", True, f"{count} words (allowed {th.min_words}-{th.max_words}).")
    direction = "Shorten" if count > th.max_words else "Expand"
    return make_result(
        "word_count", "Word count", "code", False,
        reason=f"{count} words is outside the allowed range {th.min_words}-{th.max_words}.",
        evidence=f"Word count: {count}",
        fix=f"{direction} the lesson to between {th.min_words} and {th.max_words} words.",
    )


def check_readability(lesson: str, kb: Knowledge, th: Thresholds) -> CheckResult:
    """Short sentences and an easy Flesch score (prose only; headings and code are ignored)."""
    flesch, avg_len = readability(lesson)
    problems = []
    if avg_len > th.max_avg_sentence_words:
        problems.append(f"average sentence length {avg_len} words (max {th.max_avg_sentence_words})")
    if flesch < th.min_flesch_reading_ease:
        problems.append(f"Flesch reading ease {flesch} (min {th.min_flesch_reading_ease})")
    detail = f"Flesch {flesch}, average sentence {avg_len} words."
    if not problems:
        return make_result("readability", "Readability", "code", True, detail)
    return make_result(
        "readability", "Readability", "code", False,
        reason="Too hard to read: " + "; ".join(problems) + ".",
        evidence=detail,
        fix="Split long sentences into shorter ones (aim for 10-15 words) and use shorter, common words.",
    )


def check_hard_words(lesson: str, kb: Knowledge, th: Thresholds) -> CheckResult:
    """No word from the hard-words blocklist (matched by stem: utilize -> utilized, utilizing)."""
    text = strip_code_blocks(lesson)
    found = []
    for word in kb.hard_words:
        stem = word[:-1] if word.endswith("e") and len(word) > 4 else word
        match = re.search(rf"\b{re.escape(stem)}\w*\b", text, re.IGNORECASE)
        if match:
            found.append(f"'{match.group(0)}' in {snippet(text, match.start(), match.end())}")
    if not found:
        return make_result("hard_words", "No hard words", "code", True, "No blocklisted words found.")
    return make_result(
        "hard_words", "No hard words", "code", False,
        reason=f"Found {len(found)} hard word(s) from the blocklist.",
        evidence="; ".join(found),
        fix="Replace each hard word with a simple everyday word (e.g. 'use' instead of 'utilize').",
    )


def check_jargon_defined(lesson: str, kb: Knowledge, th: Thresholds) -> CheckResult:
    """Every known technical term used in the lesson is defined in the Key words section."""
    text = strip_code_blocks(lesson)
    glossary = find_section(split_sections(lesson), kb.glossary_section) or ""
    terms, examples = [], []
    for term in kb.jargon_terms:
        used = re.search(rf"\b{re.escape(term)}s?\b", text, re.IGNORECASE)
        defined = re.search(rf"\b{re.escape(term)}", glossary, re.IGNORECASE)
        if used and not defined:
            terms.append(term)
            examples.append(f"'{term}' used in {snippet(text, used.start(), used.end())}")
    if not terms:
        return make_result("jargon_defined", "Jargon defined", "code", True, "Every technical term used is in Key words.")
    return make_result(
        "jargon_defined", "Jargon defined", "code", False,
        reason=f"{len(terms)} technical term(s) are used but not defined in '{kb.glossary_section}'.",
        evidence="; ".join(examples),
        fix=f"Add a simple definition to '{kb.glossary_section}' for: {', '.join(terms)} "
            "(or remove the term if it is not needed).",
    )


def check_quiz(lesson: str, kb: Knowledge, th: Thresholds) -> CheckResult:
    """The quiz has at least N numbered questions, and each has an answer."""
    quiz = find_section(split_sections(lesson), kb.quiz_section) or ""
    questions = len(re.findall(r"^\s*\d+[.)]\s+.*\?", quiz, re.MULTILINE))
    answers = len(re.findall(r"answer\s*:", quiz.replace("*", ""), re.IGNORECASE))
    ok = questions >= th.min_quiz_questions and answers >= questions
    detail = f"{questions} question(s), {answers} answer(s)."
    if ok:
        return make_result("quiz", "Quiz with answers", "code", True, detail)
    return make_result(
        "quiz", "Quiz with answers", "code", False,
        reason=f"Need at least {th.min_quiz_questions} numbered questions, each with an answer. Found {detail}",
        evidence=detail,
        fix=f"In '{kb.quiz_section}', write at least {th.min_quiz_questions} numbered questions ending in '?', "
            "each followed by a line starting with '**Answer:**'.",
    )


CODE_CHECKS: tuple[CodeCheck, ...] = (
    CodeCheck("sections", "Required sections", check_sections),
    CodeCheck("word_count", "Word count", check_word_count),
    CodeCheck("readability", "Readability", check_readability),
    CodeCheck("hard_words", "No hard words", check_hard_words),
    CodeCheck("jargon_defined", "Jargon defined", check_jargon_defined),
    CodeCheck("quiz", "Quiz with answers", check_quiz),
)


def run_code_checks(lesson: str, kb: Knowledge, th: Thresholds) -> list[CheckResult]:
    """Run all code checks in a fixed order."""
    return [check.run(lesson, kb, th) for check in CODE_CHECKS]
