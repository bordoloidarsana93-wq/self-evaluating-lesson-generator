"""The hybrid evaluator: 6 code checks first, then 6 LLM-judge checks.

All 12 checks always run (no early stop), so the reviser gets the full list of problems
in one go and the rejection log is complete.
"""

from __future__ import annotations

import logging

from .checks_code import CODE_CHECKS, run_code_checks
from .checks_judge import JUDGE_CHECKS, run_judge_check
from .services import Services
from .state import CheckResult

logger = logging.getLogger(__name__)

# Every check id with its name; used by the `feedback` command to validate ids.
ALL_CHECKS: dict[str, str] = {c.id: c.name for c in CODE_CHECKS} | {c.id: c.name for c in JUDGE_CHECKS}


def evaluate_lesson(lesson: str, services: Services) -> list[CheckResult]:
    """Run the full rubric on one lesson and log each result as it comes in."""
    settings = services.settings
    results = run_code_checks(lesson, services.knowledge, settings.thresholds)
    for result in results:
        _log_result(result)

    for check in JUDGE_CHECKS:
        result = run_judge_check(
            check,
            lesson,
            services.knowledge,
            services.judge,
            settings.judge_temperature,
            services.memory.feedback_for(check.id),
        )
        _log_result(result)
        results.append(result)
    return results


def _log_result(result: CheckResult) -> None:
    if result["overruled"]:
        mark = "PASS*"  # Judge said FAIL, but the evidence rule discarded it.
    else:
        mark = "PASS " if result["passed"] else "FAIL "
    logger.info("   [%s] %-6s %-28s %s", mark, result["kind"], result["name"], result["reason"][:90])
    if not result["passed"] and result["evidence"]:
        logger.info("            evidence: %s", result["evidence"][:150])
