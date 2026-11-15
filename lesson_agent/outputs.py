"""Writes the three files for each run into `outputs/<run_id>/`.

- lesson.md          the lesson to ship (with a BLOCKED banner if it did not pass)
- rejection_log.md   per attempt: every check's result, reason, evidence and what changed
- run.json           everything, machine-readable
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import Settings
from .state import AttemptRecord, LessonState


def write_outputs(state: LessonState, settings: Settings) -> Path:
    """Write lesson.md, rejection_log.md and run.json; return the run folder."""
    run_dir = settings.outputs_dir / state["run_id"]
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "lesson.md").write_text(_lesson_markdown(state), encoding="utf-8")
    (run_dir / "rejection_log.md").write_text(_rejection_log(state, settings), encoding="utf-8")
    run_data = {
        "run_id": state["run_id"],
        "topic": state["topic"],
        "started_at": state["started_at"],
        "status": state["status"],
        "best_attempt": state["best_attempt"],
        "inject_error": state.get("inject_error", False),
        "settings": {
            "provider": settings.provider,
            "generator_model": settings.generator_model,
            "judge_model": settings.judge_model,
            "max_retries": settings.max_retries,
        },
        "plan": state.get("plan", ""),
        "memory_rules_used": state.get("memory_rules_used", []),
        "new_rules": state.get("new_rules", []),
        "attempts": state["history"],
        "final_lesson": state["final_lesson"],
    }
    (run_dir / "run.json").write_text(json.dumps(run_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return run_dir


def _lesson_markdown(state: LessonState) -> str:
    """The final lesson. A BLOCKED lesson gets a clear warning banner at the top."""
    if state["status"] == "PASSED":
        return state["final_lesson"].rstrip() + "\n"
    best = state["history"][state["best_attempt"] - 1]
    failed = ", ".join(c["name"] for c in best["checks"] if not c["passed"])
    banner = (
        "> **BLOCKED – needs human review.** This lesson did not pass every check after "
        f"{len(state['history'])} attempts. Failed checks: {failed}. See rejection_log.md.\n\n"
    )
    return banner + state["final_lesson"].rstrip() + "\n"


def _rejection_log(state: LessonState, settings: Settings) -> str:
    lines = [
        f"# Rejection log: run {state['run_id']}",
        "",
        f"- **Topic:** {state['topic']}",
        f"- **Final status:** {state['status']} (shipped attempt {state['best_attempt']} "
        f"of {len(state['history'])})",
        f"- **Models:** generator `{settings.generator_model}`, judge `{settings.judge_model}` ({settings.provider})",
        f"- **Error injection:** {'on' if state.get('inject_error') else 'off'}",
        "",
        "Legend: PASS = check passed. FAIL = check failed. "
        "PASS* = a judge said FAIL but its evidence was not found in the lesson, so it was discarded.",
    ]
    for record in state["history"]:
        lines += _attempt_section(record)
    if state.get("new_rules"):
        lines += ["", "## Lessons learned this run (saved to memory)", ""]
        lines += [f"- {rule}" for rule in state["new_rules"]]
    return "\n".join(lines) + "\n"


def _attempt_section(record: AttemptRecord) -> list[str]:
    verdict = "PASSED" if record["passed"] else "FAILED"
    lines = [
        "",
        f"## Attempt {record['attempt']}: {verdict} ({record['passed_count']}/{record['total']} checks passed)",
        "",
        "**What changed before this attempt:**",
        "",
    ]
    lines += [f"- {change}" for change in record["changes"]]
    lines += ["", "**Checks:**", ""]
    for check in record["checks"]:
        mark = "PASS*" if check["overruled"] else ("PASS" if check["passed"] else "FAIL")
        lines.append(f"- **{mark}** {check['name']} ({check['kind']}): {check['reason']}")
        if not check["passed"]:
            lines.append(f"  - Evidence: {check['evidence']}")
            lines.append(f"  - Fix: {check['fix']}")
    return lines
