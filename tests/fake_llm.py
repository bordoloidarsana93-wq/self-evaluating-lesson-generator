"""A scripted stand-in for a real LLM, so tests run offline, free and repeatably."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

Handler = Callable[[str], str] | str


@dataclass
class Call:
    label: str
    system: str
    user: str


@dataclass
class FakeLLM:
    """Answers each call by its label.

    `handlers` maps a label ("generate") or a label prefix ("judge" matches
    "judge:accuracy") to either a fixed reply or a function of the user prompt.
    Every call is recorded in `calls` so tests can inspect the prompts.
    """

    handlers: dict[str, Handler]
    calls: list[Call] = field(default_factory=list)
    usage_log: list[dict] = field(default_factory=list)  # Same shape as the real client's log.

    def complete(self, system: str, user: str, *, label: str, temperature: float, json_mode: bool = False) -> str:
        self.calls.append(Call(label, system, user))
        handler = self.handlers.get(label, self.handlers.get(label.split(":")[0]))
        if handler is None:
            raise KeyError(f"FakeLLM has no handler for '{label}'")
        reply = handler(user) if callable(handler) else handler
        # Rough token estimate (about 4 characters per token), so usage tracking can be tested.
        self.usage_log.append({
            "label": label, "model": "fake", "input_tokens": len(system + user) // 4,
            "output_tokens": len(reply) // 4, "seconds": 0.0, "waited_seconds": 0.0,
        })
        return reply

    def labels(self) -> list[str]:
        return [call.label for call in self.calls]
