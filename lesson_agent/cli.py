"""Command-line interface.

    python -m lesson_agent run [--inject-error]        generate, evaluate and revise a lesson
    python -m lesson_agent feedback --check ID "note"  add a human note to a judge's prompt
    python -m lesson_agent memory show                 show what the system has learned
    python -m lesson_agent diagram                     print the workflow as a Mermaid diagram
"""

from __future__ import annotations

import argparse
import logging
import sys

from .config import ConfigError, load_settings
from .evaluate import ALL_CHECKS
from .graph import build_graph
from .llm import LLMError
from .memory import MemoryStore
from .pipeline import run_pipeline
from .services import build_services


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the chosen command, and return an exit code."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a narrower charset.
    # Libraries only show warnings; our own package shows every step.
    logging.basicConfig(level=logging.WARNING, format="%(message)s", stream=sys.stdout)
    logging.getLogger("lesson_agent").setLevel(logging.INFO)

    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ConfigError, LLMError) as exc:
        logging.getLogger(__name__).error("Error: %s", exc)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lesson_agent", description="Self-evaluating lesson generator.")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="Generate, evaluate and revise a lesson.")
    run.add_argument("--inject-error", action="store_true",
                     help="Demo: plant a false claim and an undefined term after the first draft.")
    run.set_defaults(handler=_cmd_run)

    feedback = commands.add_parser("feedback", help="Add a human note to one check's judge prompt.")
    feedback.add_argument("--check", required=True, help=f"Check id, one of: {', '.join(ALL_CHECKS)}")
    feedback.add_argument("note", help="The note, in quotes.")
    feedback.set_defaults(handler=_cmd_feedback)

    memory = commands.add_parser("memory", help="Inspect long-term memory.")
    memory.add_argument("action", choices=["show"])
    memory.set_defaults(handler=_cmd_memory_show)

    diagram = commands.add_parser("diagram", help="Print the workflow as a Mermaid diagram.")
    diagram.set_defaults(handler=_cmd_diagram)
    return parser


def _cmd_run(args: argparse.Namespace) -> int:
    services = build_services(load_settings())
    state, _ = run_pipeline(services, inject_error=args.inject_error)
    return 0 if state["status"] == "PASSED" else 2  # Non-zero lets scripts and CI spot BLOCKED runs.


def _cmd_feedback(args: argparse.Namespace) -> int:
    if args.check not in ALL_CHECKS:
        print(f"Unknown check '{args.check}'. Valid ids: {', '.join(ALL_CHECKS)}")
        return 1
    settings = load_settings(require_api_key=False)
    memory = MemoryStore(settings.memory_path)
    memory.add_feedback(args.check, args.note)
    memory.save()
    print(f"Saved. The '{ALL_CHECKS[args.check]}' check will use this note on future runs.")
    return 0


def _cmd_memory_show(args: argparse.Namespace) -> int:
    settings = load_settings(require_api_key=False)
    memory = MemoryStore(settings.memory_path)
    data = memory.data

    passed, total = memory.first_attempt_pass_rate()
    rate = f"{passed}/{total} ({passed / total:.0%})" if total else "no real runs yet"
    print(f"\nFIRST-ATTEMPT PASS RATE (excluding --inject-error demo runs): {rate}")

    print("\nRUNS")
    for run in data["runs"]:
        demo = "  [demo]" if run.get("inject_error") else ""
        first = "yes" if run["first_attempt_passed"] else "no"
        print(f"  {run['run_id']}  {run['status']:<8} attempts={run['attempts']}  passed first try={first}{demo}")

    print("\nCHECK FAILURE RATES")
    for check_id, stats in sorted(data["check_stats"].items(), key=lambda kv: -kv[1]["failed"]):
        print(f"  {stats['name']:<28} failed {stats['failed']}/{stats['evaluated']}")

    print("\nLESSONS LEARNED (most seen first; the top ones go into the generator prompt)")
    for rule in sorted(data["lessons_learned"], key=lambda r: -r["count"]):
        print(f"  x{rule['count']}  {rule['rule']}")

    print("\nHUMAN FEEDBACK (added to judge prompts)")
    for check_id, notes in data["human_feedback"].items():
        for item in notes:
            print(f"  [{check_id}] {item['note']}")
    print()
    return 0


def _cmd_diagram(args: argparse.Namespace) -> int:
    services = build_services(load_settings(require_api_key=False))
    print(build_graph(services).get_graph().draw_mermaid())
    return 0
