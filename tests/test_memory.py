"""Long-term memory: persists across runs, feeds back into prompts, deduplicates rules."""

from __future__ import annotations

from lesson_agent.memory import MemoryStore
from lesson_agent.pipeline import run_pipeline
from tests.conftest import GOOD_LESSON, LEARNED_RULE, make_generator, make_services

# A first draft with a hard word, so run 1 fails once, learns a rule and then passes.
DRAFT_WITH_HARD_WORD = GOOD_LESSON.replace(
    "The LLM uses it to write the answer.", "The LLM is utilizing it to write the answer."
)


def test_lessons_learned_persist_and_reach_the_next_run(settings):
    # Run 1: hard word -> fail -> revise -> pass. Reflection learns a rule.
    run1 = make_services(settings, generator=make_generator(first_draft=DRAFT_WITH_HARD_WORD))
    state1, _ = run_pipeline(run1)
    assert state1["status"] == "PASSED" and len(state1["history"]) == 2
    assert state1["new_rules"] == [LEARNED_RULE]

    # Memory is on disk: a brand-new store (as in a new process) sees it.
    reloaded = MemoryStore(settings.memory_path)
    assert reloaded.all_rules() == [LEARNED_RULE]
    assert reloaded.data["check_stats"]["hard_words"] == {"name": "No hard words", "evaluated": 2, "failed": 1}

    # Run 2: the learned rule is now part of the generator prompt.
    run2 = make_services(settings)
    state2, _ = run_pipeline(run2)
    generate_prompt = next(c.user for c in run2.generator.calls if c.label == "generate")
    assert LEARNED_RULE in generate_prompt
    assert state2["memory_rules_used"] == [LEARNED_RULE]

    passed, total = MemoryStore(settings.memory_path).first_attempt_pass_rate()
    assert (passed, total) == (1, 2)  # Run 1 needed a retry, run 2 passed first time.


def test_same_rule_is_counted_not_duplicated(tmp_path):
    memory = MemoryStore(tmp_path / "memory.json")
    memory.add_rules(["Define every technical term."])
    memory.add_rules(["define every technical term"])  # Same rule, different case/punctuation.
    memory.add_rules(["Keep sentences short."])
    assert len(memory.data["lessons_learned"]) == 2
    assert memory.top_rules(1) == ["Define every technical term."]
    assert memory.data["lessons_learned"][0]["count"] == 2


def test_human_feedback_persists_and_sharpens_the_judge(settings):
    memory = MemoryStore(settings.memory_path)
    memory.add_feedback("simple_english", "Treat 'kick off' as an idiom.")
    memory.save()

    services = make_services(settings)  # Loads memory from disk.
    run_pipeline(services)
    judge_prompt = next(c.user for c in services.judge.calls if c.label == "judge:simple_english")
    assert "Treat 'kick off' as an idiom." in judge_prompt
    other_prompt = next(c.user for c in services.judge.calls if c.label == "judge:flow")
    assert "kick off" not in other_prompt  # Notes only go to their own check.


def test_judge_outages_are_not_learned_as_content_mistakes(settings):
    from lesson_agent.llm import LLMError
    from tests.conftest import make_judge

    judge = make_judge()

    def outage(prompt: str) -> str:
        raise LLMError("[judge:flow] gave up after 6 tries: rate limit")

    judge.handlers["judge:flow"] = outage
    services = make_services(settings, judge=judge)
    state, _ = run_pipeline(services)

    assert state["status"] == "BLOCKED"  # Fail closed: an unchecked lesson is never shipped...
    assert "flow" not in services.memory.data["check_stats"]  # ...but the outage is not "learned".
    assert services.memory.data["lessons_learned"] == []


def test_common_failures_become_warnings(tmp_path):
    memory = MemoryStore(tmp_path / "memory.json")
    fail = {"id": "readability", "name": "Readability", "passed": False}
    ok = {"id": "readability", "name": "Readability", "passed": True}
    memory.record_checks([fail])
    memory.record_checks([fail])
    memory.record_checks([ok])
    assert memory.common_failures() == ["Readability (failed 2 of 3 attempts)"]
