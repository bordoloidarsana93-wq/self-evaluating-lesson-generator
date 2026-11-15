"""The steps (nodes) of the lesson workflow.

Each node is a plain function: it reads the shared state, does one job, and returns ONLY
the fields it changed. LangGraph merges those fields into the state. Nodes never call
each other; `graph.py` decides the order. Because they are plain functions, tests can call
any node directly.
"""

from __future__ import annotations

import logging

from .checks_judge import NO_JUDGE_ANSWER
from .evaluate import evaluate_lesson
from .llm import LLMError, complete_json
from .prompts import REFLECT_SYSTEM, TEACHER_SYSTEM, generate_prompt, plan_prompt, reflect_prompt, revise_prompt
from .services import Services
from .state import AttemptRecord, LessonState
from .text_utils import extract_tag, normalize_heading, strip_outer_fence

logger = logging.getLogger(__name__)

# The deliberate errors planted by --inject-error: one false claim (the accuracy judge
# must catch it) and one undefined technical term (the jargon code check must catch it).
INJECTED_FALSE_CLAIM = "RAG retrains the model on your documents, so the new facts are stored inside the model itself."
INJECTED_JARGON = "After that, a reranker sorts the results."
INJECT_INTO_SECTION = "How it works"


def _banner(title: str) -> None:
    logger.info("\n=== %s %s", title, "=" * max(3, 60 - len(title)))


# --- Nodes --------------------------------------------------------------------------------

def plan(state: LessonState, services: Services) -> dict:
    """Write a short teaching plan first, so the lesson has a clear structure and order."""
    _banner("PLAN")
    text = services.generator.complete(
        TEACHER_SYSTEM, plan_prompt(services.knowledge),
        label="plan", temperature=services.settings.generator_temperature,
    )
    preview = "\n".join(f"   {line}" for line in text.strip().splitlines()[:8])
    logger.info("%s\n   ...", preview)
    return {"plan": text.strip()}


def generate(state: LessonState, services: Services) -> dict:
    """Write the first full draft, adding lessons learned from memory to the prompt."""
    _banner("GENERATE (attempt 1)")
    memory = services.memory
    rules = memory.top_rules(services.settings.top_rules_in_prompt)
    warnings = memory.common_failures()
    logger.info("   Using %d lesson(s) learned and %d failure warning(s) from memory.", len(rules), len(warnings))
    for rule in rules:
        logger.info("     - %s", rule)

    text = services.generator.complete(
        TEACHER_SYSTEM, generate_prompt(services.knowledge, state["plan"], rules, warnings),
        label="generate", temperature=services.settings.generator_temperature,
    )
    lesson = strip_outer_fence(text)
    logger.info("   Draft written: %d characters.", len(lesson))
    return {"lesson": lesson, "attempt": 1, "changes": ["First draft."], "memory_rules_used": rules}


def inject_error(state: LessonState, services: Services) -> dict:
    """Demo only: plant a false claim and an undefined term so we can watch the evaluator catch them."""
    _banner("INJECT ERROR (demo)")
    planted = f"{INJECTED_FALSE_CLAIM} {INJECTED_JARGON}"
    lesson = _insert_after_heading(state["lesson"], INJECT_INTO_SECTION, planted)
    logger.info('   Planted false claim: "%s"', INJECTED_FALSE_CLAIM)
    logger.info('   Planted undefined term: "reranker"')
    return {
        "lesson": lesson,
        "changes": state["changes"] + [
            f'INJECTED (demo) false claim: "{INJECTED_FALSE_CLAIM}"',
            f'INJECTED (demo) undefined jargon: "{INJECTED_JARGON}"',
        ],
    }


def evaluate(state: LessonState, services: Services) -> dict:
    """Run all 12 checks on the current draft and add the result to the history."""
    attempt = state["attempt"]
    _banner(f"EVALUATE (attempt {attempt})")
    checks = evaluate_lesson(state["lesson"], services)
    passed_count = sum(1 for c in checks if c["passed"])
    record = AttemptRecord(
        attempt=attempt,
        lesson=state["lesson"],
        changes=state["changes"],
        checks=checks,
        passed=passed_count == len(checks),
        passed_count=passed_count,
        total=len(checks),
    )
    logger.info("   Result: %d/%d checks passed -> %s", passed_count, len(checks), "PASS" if record["passed"] else "FAIL")
    return {"checks": checks, "history": state.get("history", []) + [record]}


def route_after_evaluate(state: LessonState, max_retries: int) -> str:
    """Decide where to go next. This is what guarantees the loop ends.

    - every check passed            -> "finalize"
    - failed and retries remain     -> "revise"
    - failed and no retries remain  -> "finalize" (ships the best attempt as BLOCKED)
    """
    if all(c["passed"] for c in state["checks"]):
        return "finalize"
    retries_used = state["attempt"] - 1
    if retries_used < max_retries:
        return "revise"
    logger.info("   No retries left (%d used).", retries_used)
    return "finalize"


def route_after_generate(state: LessonState) -> str:
    """Go through the inject_error step only when the demo flag is set."""
    return "inject_error" if state.get("inject_error") else "evaluate"


def revise(state: LessonState, services: Services) -> dict:
    """Targeted fix: send only the failed checks and keep the passing parts unchanged."""
    failed = [c for c in state["checks"] if not c["passed"]]
    _banner(f"REVISE (fixing {len(failed)} failed check(s))")
    for check in failed:
        logger.info("   - %s: %s", check["name"], check["fix"][:100])

    try:
        reply = services.generator.complete(
            TEACHER_SYSTEM, revise_prompt(services.knowledge, state["lesson"], failed),
            label="revise", temperature=services.settings.reviser_temperature,
        )
    except LLMError as exc:
        # Keep the previous draft rather than crash; it is re-evaluated and the retry is used up,
        # so the loop still ends.
        logger.warning("   Revision failed (%s); keeping the previous draft.", exc)
        return {"attempt": state["attempt"] + 1, "changes": [f"Revision failed, previous draft kept: {exc}"]}

    lesson = extract_tag(reply, "lesson")
    if not lesson:
        # The model ignored the format; use the reply without any stray tags.
        logger.warning("   Reviser did not use <lesson> tags correctly; using the reply text.")
        lesson = reply.split("<changes>")[0].replace("<lesson>", "").replace("</lesson>", "")
    lesson = strip_outer_fence(lesson)
    changes_text = extract_tag(reply, "changes") or ""
    changes = [line.lstrip("-* ").strip() for line in changes_text.splitlines() if line.strip()]
    # If the model skipped its change list, work it out ourselves from the text.
    changes = changes or _describe_changes(state["lesson"], lesson)
    for change in changes:
        logger.info("   changed: %s", change)
    return {"lesson": lesson, "attempt": state["attempt"] + 1, "changes": changes}


def finalize(state: LessonState, services: Services) -> dict:
    """Pick the lesson to ship: the passing draft, or the best draft marked BLOCKED."""
    history = state["history"]
    last = history[-1]
    if last["passed"]:
        best, status = last, "PASSED"
    else:
        # Most checks passed wins; on a tie, the later (more revised) draft wins.
        best = max(history, key=lambda r: (r["passed_count"], r["attempt"]))
        status = "BLOCKED"
    _banner(f"FINALIZE: {status}")
    logger.info("   Shipping attempt %d (%d/%d checks passed).", best["attempt"], best["passed_count"], best["total"])
    if status == "BLOCKED":
        logger.info("   BLOCKED - needs human review.")
    return {"status": status, "final_lesson": best["lesson"], "best_attempt": best["attempt"]}


def reflect(state: LessonState, services: Services) -> dict:
    """Update long-term memory: run summary, check stats and lessons learned."""
    _banner("REFLECT (update memory)")
    memory = services.memory
    history = state["history"]

    # Only learn from real content mistakes. Skipped: the injected first draft (errors we
    # planted on purpose) and checks a judge could not answer (API problems, not content).
    real_attempts = history[1:] if state.get("inject_error") else history
    real_checks = [
        [c for c in record["checks"] if c["evidence"] != NO_JUDGE_ANSWER] for record in real_attempts
    ]
    for checks in real_checks:
        memory.record_checks(checks)

    failures = [
        f"{c['name']}: {c['reason']} Fix: {c['fix']}"
        for checks in real_checks for c in checks if not c["passed"]
    ]
    new_rules: list[str] = []
    if failures:
        try:
            reply = complete_json(
                services.generator, REFLECT_SYSTEM, reflect_prompt(failures, memory.all_rules()),
                label="reflect", temperature=0.2,
            )
            new_rules = [r for r in reply.get("rules", []) if isinstance(r, str) and r.strip()][:3]
        except LLMError as exc:
            logger.warning("   Reflection failed (%s); memory stats are still saved.", exc)
        memory.add_rules(new_rules)
    for rule in new_rules:
        logger.info("   learned: %s", rule)
    if not failures:
        logger.info("   No real failures this run; nothing new to learn.")

    memory.record_run({
        "run_id": state["run_id"],
        "topic": state["topic"],
        "status": state["status"],
        "attempts": len(history),
        "first_attempt_passed": history[0]["passed"],
        "inject_error": bool(state.get("inject_error")),
    })
    memory.save()
    passed, total = memory.first_attempt_pass_rate()
    logger.info("   Memory saved. First-attempt pass rate so far: %d/%d real runs.", passed, total)
    return {"new_rules": new_rules}


# --- Helpers ------------------------------------------------------------------------------

def _describe_changes(old: str, new: str, limit: int = 6) -> list[str]:
    """List changed lines between two drafts (used when the reviser gives no change list)."""
    old_lines = [line.strip() for line in old.splitlines() if line.strip()]
    new_lines = [line.strip() for line in new.splitlines() if line.strip()]
    removed = [line for line in old_lines if line not in new_lines]
    added = [line for line in new_lines if line not in old_lines]
    if not removed and not added:
        return ["(No text changed.)"]
    changes = [f'Removed: "{line[:120]}"' for line in removed[:limit]]
    changes += [f'Added: "{line[:120]}"' for line in added[:limit]]
    hidden = len(removed) + len(added) - len(changes)
    if hidden > 0:
        changes.append(f"...and {hidden} more changed line(s).")
    return ["(Worked out by comparing drafts; the reviser gave no list.)"] + changes


def _insert_after_heading(lesson: str, section_title: str, text: str) -> str:
    """Insert a paragraph right after the `## ` heading that contains `section_title`."""
    wanted = normalize_heading(section_title)
    lines = lesson.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("## ") and wanted in normalize_heading(line[3:]):
            lines[i + 1:i + 1] = ["", text]
            return "\n".join(lines)
    return f"{lesson.rstrip()}\n\n{text}\n"  # Section missing: append so the demo still works.
