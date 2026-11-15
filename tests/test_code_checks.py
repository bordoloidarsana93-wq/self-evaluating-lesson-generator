"""The deterministic code checks: a good lesson passes, each kind of problem is caught."""

from __future__ import annotations

from lesson_agent.checks_code import run_code_checks
from lesson_agent.config import Thresholds
from tests.conftest import GOOD_LESSON


def _results(lesson: str, knowledge, thresholds: Thresholds | None = None) -> dict:
    return {r["id"]: r for r in run_code_checks(lesson, knowledge, thresholds or Thresholds())}


def test_good_lesson_passes_every_code_check(knowledge):
    results = _results(GOOD_LESSON, knowledge)
    assert all(r["passed"] for r in results.values()), {k: r["reason"] for k, r in results.items()}


def test_missing_section_is_caught(knowledge):
    lesson = GOOD_LESSON.replace("## Recap", "## Summary")
    result = _results(lesson, knowledge)["sections"]
    assert not result["passed"]
    assert "Recap" in result["evidence"]


def test_hard_word_is_caught_by_its_stem(knowledge):
    lesson = GOOD_LESSON.replace("The LLM uses it to write the answer.", "The LLM is utilizing it to write the answer.")
    result = _results(lesson, knowledge)["hard_words"]
    assert not result["passed"]
    assert "utilizing" in result["evidence"]


def test_undefined_jargon_is_caught(knowledge):
    lesson = GOOD_LESSON.replace("## Why it matters", "A reranker sorts the chunks.\n\n## Why it matters")
    result = _results(lesson, knowledge)["jargon_defined"]
    assert not result["passed"]
    assert "reranker" in result["evidence"]


def test_quiz_without_answers_fails(knowledge):
    lesson = "\n".join(line for line in GOOD_LESSON.splitlines() if "**Answer:**" not in line)
    assert not _results(lesson, knowledge)["quiz"]["passed"]


def test_too_short_lesson_fails_word_count(knowledge):
    short = GOOD_LESSON[:1500]
    assert not _results(short, knowledge)["word_count"]["passed"]


def test_readability_threshold_is_enforced(knowledge):
    strict = Thresholds(min_flesch_reading_ease=100.0)
    result = _results(GOOD_LESSON, knowledge, strict)["readability"]
    assert not result["passed"]
    assert "Flesch" in result["reason"]
