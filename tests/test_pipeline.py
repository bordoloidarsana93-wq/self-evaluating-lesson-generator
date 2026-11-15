"""End-to-end runs of the LangGraph workflow with fake LLMs: pass path, retry cap, error injection."""

from __future__ import annotations

from dataclasses import replace

from lesson_agent.pipeline import run_pipeline
from tests.conftest import fail_json, make_judge, make_services
from tests.fake_llm import FakeLLM


def test_pass_path_ships_first_draft(settings):
    services = make_services(settings)
    state, run_dir = run_pipeline(services)

    assert state["status"] == "PASSED"
    assert len(state["history"]) == 1
    assert "revise" not in services.generator.labels()
    assert services.generator.labels()[:2] == ["plan", "generate"]
    assert len(services.judge.calls) == 6  # One separate call per judge check.
    for name in ("lesson.md", "rejection_log.md", "run.json"):
        assert (run_dir / name).exists()
    assert (run_dir / "lesson.md").read_text(encoding="utf-8").startswith("# Introduction to RAG")


def test_retry_cap_stops_the_loop_and_marks_blocked(settings):
    # The flow judge always fails with a quote that really exists, so nothing can pass.
    stubborn_judge = FakeLLM({"judge:flow": fail_json("RAG works in the same way."), "judge": make_judge().handlers["judge"]})
    services = make_services(settings, judge=stubborn_judge)
    state, run_dir = run_pipeline(services)

    assert state["status"] == "BLOCKED"
    assert len(state["history"]) == settings.max_retries + 1  # 3 evaluated attempts, never more.
    assert services.generator.labels().count("revise") == settings.max_retries
    assert (run_dir / "lesson.md").read_text(encoding="utf-8").startswith("> **BLOCKED – needs human review.**")


def test_zero_retries_still_terminates(settings):
    stubborn_judge = FakeLLM({"judge:flow": fail_json("RAG works in the same way."), "judge": make_judge().handlers["judge"]})
    services = make_services(replace(settings, max_retries=0), judge=stubborn_judge)
    state, _ = run_pipeline(services)
    assert state["status"] == "BLOCKED" and len(state["history"]) == 1


def test_failed_revision_keeps_previous_draft_and_still_terminates(settings):
    from lesson_agent.llm import LLMError
    from tests.conftest import make_generator

    generator = make_generator()

    def broken_revise(prompt: str) -> str:
        raise LLMError("[revise] the reply was cut off at the output token limit")

    generator.handlers["revise"] = broken_revise
    stubborn_judge = FakeLLM({"judge:flow": fail_json("RAG works in the same way."), "judge": make_judge().handlers["judge"],
                              "judge:coverage": make_judge().handlers["judge:coverage"]})
    services = make_services(settings, generator=generator, judge=stubborn_judge)
    state, _ = run_pipeline(services)

    assert state["status"] == "BLOCKED"
    assert len(state["history"]) == settings.max_retries + 1
    assert "Revision failed" in state["history"][1]["changes"][0]
    assert state["history"][1]["lesson"] == state["history"][0]["lesson"]


def test_injected_errors_are_caught_and_fixed(settings):
    services = make_services(settings)
    state, run_dir = run_pipeline(services, inject_error=True)

    first, second = state["history"]
    failed_first = {c["id"] for c in first["checks"] if not c["passed"]}
    assert {"accuracy", "jargon_defined"} <= failed_first  # Judge caught the claim, code caught the term.
    assert any("INJECTED" in change for change in first["changes"])

    assert second["passed"]  # The reviser fixed both.
    assert state["status"] == "PASSED"
    assert "retrains the model" not in state["final_lesson"]

    log = (run_dir / "rejection_log.md").read_text(encoding="utf-8")
    assert "INJECTED (demo) false claim" in log
    assert "Fixed the failed checks." in log


def test_injected_failures_do_not_pollute_memory(settings):
    services = make_services(settings)
    run_pipeline(services, inject_error=True)
    stats = services.memory.data["check_stats"]
    assert stats["accuracy"]["failed"] == 0  # The planted error is not a real model mistake.
    assert services.memory.data["lessons_learned"] == []
    assert services.memory.first_attempt_pass_rate() == (0, 0)  # Demo runs are excluded.
