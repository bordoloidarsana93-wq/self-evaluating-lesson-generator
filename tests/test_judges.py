"""LLM-judge checks and the evidence rule (a FAIL only counts with a quote that really exists)."""

from __future__ import annotations

from lesson_agent.checks_judge import JUDGE_CHECKS, run_judge_check
from lesson_agent.text_utils import quote_in_text
from tests.conftest import COVERAGE_QUOTES, GOOD_LESSON, PASS_JSON, coverage_json, fail_json
from tests.fake_llm import FakeLLM

CHECKS = {c.id: c for c in JUDGE_CHECKS}


def _run(check_id: str, reply: str, knowledge, notes: list[str] | None = None):
    judge = FakeLLM({"judge": reply})
    result = run_judge_check(CHECKS[check_id], GOOD_LESSON, knowledge, judge, 0.0, notes or [])
    return result, judge


def test_pass_is_accepted(knowledge):
    result, _ = _run("flow", PASS_JSON, knowledge)
    assert result["passed"] and not result["overruled"]


def test_fail_with_a_real_quote_counts(knowledge):
    result, _ = _run("simple_english", fail_json("RAG works in the same way."), knowledge)
    assert not result["passed"]
    assert "RAG works in the same way." in result["evidence"]


def test_imagined_quotes_are_dropped_but_real_ones_count(knowledge):
    reply = fail_json("RAG works in the same way.", "A sentence the judge imagined.")
    result, _ = _run("simple_english", reply, knowledge)
    assert not result["passed"]
    assert "RAG works in the same way." in result["evidence"]
    assert "imagined" not in result["evidence"]


def test_fail_with_an_imagined_quote_is_discarded(knowledge):
    result, _ = _run("simple_english", fail_json("This sentence is not in the lesson at all."), knowledge)
    assert result["passed"]
    assert result["overruled"]
    assert "evidence rule" in result["reason"]


def test_fail_without_any_quote_is_discarded(knowledge):
    result, _ = _run("flow", fail_json(), knowledge)
    assert result["passed"] and result["overruled"]


def test_coverage_passes_only_when_every_point_is_proven(knowledge):
    result, _ = _run("coverage", coverage_json(), knowledge)
    assert result["passed"]


def test_coverage_rejects_missing_or_imagined_proof(knowledge):
    quotes = dict(COVERAGE_QUOTES, limits="", chunking="Chunks are stored on the moon.")
    result, _ = _run("coverage", coverage_json(quotes), knowledge)
    assert not result["passed"]
    assert "[limits]" in result["evidence"] and "[chunking]" in result["evidence"]


def test_coverage_proof_from_recap_or_key_words_does_not_count(knowledge):
    # This sentence exists in the lesson, but only in the Key words section.
    quotes = dict(COVERAGE_QUOTES, chunking="Chunking means splitting documents into chunks.")
    result, _ = _run("coverage", coverage_json(quotes), knowledge)
    assert not result["passed"]
    assert "[chunking]" in result["evidence"]


def test_unusable_judge_reply_fails_closed(knowledge):
    result, judge = _run("accuracy", "I think the lesson is fine!", knowledge)
    assert not result["passed"]  # Never ship a lesson that was not really checked.
    assert len(judge.calls) == 2  # One retry asking for valid JSON.


def test_human_feedback_reaches_the_judge_prompt(knowledge):
    _, judge = _run("simple_english", PASS_JSON, knowledge, notes=["Treat 'on the fly' as an idiom."])
    assert "Treat 'on the fly' as an idiom." in judge.calls[0].user


def test_quote_matching_is_forgiving_but_strict():
    text = "RAG has **three** simple steps. The model is not trained again."
    assert quote_in_text("RAG has three simple steps", text)  # Markdown ignored.
    assert quote_in_text('"rag has three ... not trained again."', text)  # Ellipsis + case + quotes.
    assert not quote_in_text("RAG has four simple steps", text)
    assert not quote_in_text("", text)
