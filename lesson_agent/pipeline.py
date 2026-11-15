"""Runs the whole workflow once: build the graph, invoke it, write the output files."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .graph import build_graph
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

    # Our own retry cap already ends the loop; LangGraph's step limit is a second safety net.
    step_limit = 10 + 2 * services.settings.max_retries
    state: LessonState = build_graph(services).invoke(initial, config={"recursion_limit": step_limit})

    run_dir = write_outputs(state, services.settings)
    logger.info("\nDone: %s after %d attempt(s). Files written to %s", state["status"], len(state["history"]), run_dir)
    return state, run_dir
