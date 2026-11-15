"""Data shapes shared across the workflow.

`LessonState` is the "notebook" that LangGraph passes from node to node. Each node reads
what it needs and returns only the fields it changed. Everything here is plain dicts and
lists, so the whole state can be saved straight to `run.json`.
"""

from __future__ import annotations

from typing import Literal, TypedDict


class CheckResult(TypedDict):
    """The outcome of one rubric check. There is no partial credit: `passed` is True or False."""

    id: str  # Stable id, e.g. "accuracy". Used by memory and the feedback command.
    name: str  # Human-readable name for logs.
    kind: Literal["code", "judge"]
    passed: bool
    reason: str  # Why it passed or failed.
    evidence: str  # The offending text (or what is missing). Empty when it passed.
    fix: str  # A concrete suggestion for the reviser. Empty when it passed.
    overruled: bool  # True if a judge said FAIL but gave no verifiable quote (evidence rule).


class AttemptRecord(TypedDict):
    """One evaluated draft, kept for the rejection log."""

    attempt: int
    lesson: str
    changes: list[str]  # What was done to produce this draft (first draft / injected / revised).
    checks: list[CheckResult]
    passed: bool
    passed_count: int
    total: int


class LessonState(TypedDict, total=False):
    """Everything the workflow knows about one run."""

    # Inputs
    run_id: str
    topic: str
    inject_error: bool
    started_at: str

    # Working fields
    plan: str
    lesson: str  # The current draft.
    attempt: int  # Number of the current draft (1, 2, 3).
    changes: list[str]  # What produced the current draft.
    checks: list[CheckResult]  # Results for the current draft.
    history: list[AttemptRecord]  # Every evaluated draft, in order.
    memory_rules_used: list[str]  # Lessons learned that were added to the generator prompt.

    # Results
    status: Literal["PASSED", "BLOCKED"]
    final_lesson: str
    best_attempt: int
    new_rules: list[str]  # Rules the reflect step learned or reinforced in this run.


def make_result(
    check_id: str,
    name: str,
    kind: Literal["code", "judge"],
    passed: bool,
    reason: str,
    evidence: str = "",
    fix: str = "",
    overruled: bool = False,
) -> CheckResult:
    """Build a `CheckResult` with every field set (keeps call sites short and consistent)."""
    return CheckResult(
        id=check_id,
        name=name,
        kind=kind,
        passed=passed,
        reason=reason,
        evidence=evidence if not passed else "",
        fix=fix if not passed else "",
        overruled=overruled,
    )
