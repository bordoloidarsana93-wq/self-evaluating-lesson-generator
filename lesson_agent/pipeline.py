"""Runs the whole workflow once: build the graph, invoke it, write the output files."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .graph import build_graph
from .llm import summarize_usage
from .outputs import write_outputs
from .services import Services
from .state import LessonState

logger = logging.getLogger(__name__)


def new_run_id() -> str:
    """A sortable, unique id such as 20261115-153012-a1b2."""
    return f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"


def run_pipeline(services: Services, inject_error: bool = False) -> tuple[LessonState, Path]:
    """Generate, evaluate and (if needed) revise one lesson.

    Returns:
        The final state and the folder the output files were written to.
    """
    initial: LessonState = {
        "run_id": new_run_id(),
        "topic": services.knowledge.topic,
        "inject_error": inject_error,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "history": [],
    }
    logger.info("Run %s | topic: %s | max retries: %d%s",
                initial["run_id"], initial["topic"], services.settings.max_retries,
                " | ERROR INJECTION ON" if inject_error else "")

    # Remember where each usage log starts, so only this run's calls are counted.
    writer_log, judge_log = _usage_log(services.generator), _usage_log(services.judge)
    writer_start, judge_start = len(writer_log), len(judge_log)
    started = time.perf_counter()

    # Our own retry cap already ends the loop; LangGraph's step limit is a second safety net.
    step_limit = 10 + 2 * services.settings.max_retries
    state: LessonState = build_graph(services).invoke(initial, config={"recursion_limit": step_limit})

    state["usage"] = {
        "wall_seconds": round(time.perf_counter() - started, 1),
        "writer": summarize_usage(writer_log[writer_start:]),
        "judge": summarize_usage(judge_log[judge_start:]),
    }
    _log_usage(state["usage"])

    run_dir = write_outputs(state, services.settings)
    logger.info("\nDone: %s after %d attempt(s). Files written to %s", state["status"], len(state["history"]), run_dir)
    return state, run_dir


def _usage_log(llm: object) -> list[dict]:
    """The client's usage log, or an empty list for clients that do not track usage."""
    log = getattr(llm, "usage_log", None)
    return log if isinstance(log, list) else []


def _log_usage(usage: dict) -> None:
    """Print a short cost and time summary for the run."""
    writer, judge = usage["writer"], usage["judge"]
    total = writer["total_tokens"] + judge["total_tokens"]
    logger.info("\n=== USAGE %s", "=" * 54)
    logger.info("   Writer: %d calls, %s tokens | Judge: %d calls, %s tokens | Total: %s tokens",
                writer["calls"], f"{writer['total_tokens']:,}", judge["calls"], f"{judge['total_tokens']:,}", f"{total:,}")
    logger.info("   Time: %.0fs total (%.0fs waiting for rate limits)",
                usage["wall_seconds"], writer["rate_limit_wait_seconds"] + judge["rate_limit_wait_seconds"])
