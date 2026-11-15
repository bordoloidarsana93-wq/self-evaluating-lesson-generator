"""Long-term memory that persists across runs in `memory/memory.json`.

This is what makes the system self-evolving:

- lessons_learned: short, general rules distilled from past failures (deduplicated, with
  a count). The most-seen rules are added to the generator prompt on later runs.
- check_stats: how often each check has failed. The most common failures become warnings
  in the generator prompt.
- human_feedback: notes a human adds with `feedback --check <id> "note"`. They are added
  to that check's judge prompt, which sharpens the rubric.
- runs: one summary per run, used to show the first-attempt pass rate over time.

A plain JSON file is enough here: it is human-readable, easy to inspect on video, and
needs no database. It is written atomically (temp file + rename) so a crash cannot
leave half a file behind.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .state import CheckResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_rule(rule: str) -> str:
    """Compare rules ignoring case, punctuation and spacing (for deduplication)."""
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", rule.lower()).split())


class MemoryStore:
    """Loads, updates and saves the memory file."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.data: dict[str, Any] = self._load()

    # --- Load / save ----------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
        # setdefault keeps old memory files working if we add new sections later.
        data.setdefault("version", 1)
        data.setdefault("runs", [])
        data.setdefault("check_stats", {})
        data.setdefault("lessons_learned", [])
        data.setdefault("human_feedback", {})
        return data

    def save(self) -> None:
        """Write memory to disk atomically."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    # --- Lessons learned ------------------------------------------------------------------

    def top_rules(self, limit: int) -> list[str]:
        """The most frequently learned rules (ties: most recently seen first)."""
        rules = sorted(
            self.data["lessons_learned"],
            key=lambda r: (r["count"], r["last_seen"]),
            reverse=True,
        )
        return [r["rule"] for r in rules[:limit]]

    def all_rules(self) -> list[str]:
        return [r["rule"] for r in self.data["lessons_learned"]]

    def add_rules(self, rules: list[str]) -> None:
        """Add new rules, or bump the count of a rule we already know."""
        known = {_normalize_rule(r["rule"]): r for r in self.data["lessons_learned"]}
        for rule in rules:
            rule = rule.strip()
            key = _normalize_rule(rule)
            if not key:
                continue
            if key in known:
                known[key]["count"] += 1
                known[key]["last_seen"] = _now()
            else:
                entry = {"rule": rule, "count": 1, "first_seen": _now(), "last_seen": _now()}
                self.data["lessons_learned"].append(entry)
                known[key] = entry

    # --- Check stats ----------------------------------------------------------------------

    def record_checks(self, checks: list[CheckResult]) -> None:
        """Count one evaluated attempt for each check, and one failure for each failed check."""
        for check in checks:
            stats = self.data["check_stats"].setdefault(
                check["id"], {"name": check["name"], "evaluated": 0, "failed": 0}
            )
            stats["evaluated"] += 1
            stats["failed"] += 0 if check["passed"] else 1

    def common_failures(self, limit: int = 3, min_rate: float = 0.3, min_evaluated: int = 2) -> list[str]:
        """Warnings like "Readability failed 3 of 5 times" for the checks that fail most."""
        rows = []
        for stats in self.data["check_stats"].values():
            if stats["evaluated"] >= min_evaluated and stats["failed"] / stats["evaluated"] >= min_rate:
                rows.append(stats)
        rows.sort(key=lambda s: s["failed"] / s["evaluated"], reverse=True)
        return [f"{s['name']} (failed {s['failed']} of {s['evaluated']} attempts)" for s in rows[:limit]]

    # --- Human feedback -------------------------------------------------------------------

    def add_feedback(self, check_id: str, note: str) -> None:
        self.data["human_feedback"].setdefault(check_id, []).append({"note": note.strip(), "added": _now()})

    def feedback_for(self, check_id: str) -> list[str]:
        return [item["note"] for item in self.data["human_feedback"].get(check_id, [])]

    # --- Runs -----------------------------------------------------------------------------

    def record_run(self, summary: dict[str, Any]) -> None:
        self.data["runs"].append({**summary, "finished_at": _now()})

    def first_attempt_pass_rate(self) -> tuple[int, int]:
        """(runs that passed on attempt 1, total runs), ignoring error-injection demo runs."""
        real_runs = [r for r in self.data["runs"] if not r.get("inject_error")]
        return sum(1 for r in real_runs if r["first_attempt_passed"]), len(real_runs)
