"""A tiny LLM wrapper.

The rest of the code only knows one method: `complete(system, user, ...) -> str`.
Because Groq, Gemini and OpenAI all offer an OpenAI-compatible API, one class talks to all
three, and switching provider is a change in `.env`, not in code. Tests swap in a fake
object with the same method, so they never need an API key.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Protocol

import openai
from openai import OpenAI

logger = logging.getLogger(__name__)

# Errors that usually go away if we wait: rate limits, network problems, server hiccups.
_RETRYABLE_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
)


class LLMError(RuntimeError):
    """Raised when the model cannot give a usable answer."""


class LLMClient(Protocol):
    """Anything that can answer a prompt. The real client and the test fake both fit."""

    def complete(
        self,
        system: str,
        user: str,
        *,
        label: str,
        temperature: float,
        json_mode: bool = False,
    ) -> str:
        """Send one system + user message and return the model's text reply.

        `label` names the call (e.g. "generate", "judge:accuracy") for logs and tests.
        """
        ...


class OpenAICompatibleClient:
    """Calls any OpenAI-compatible chat API, waiting and retrying on temporary errors."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str | None = None,
        max_attempts: int = 6,
        timeout_seconds: float = 120.0,
        reasoning_effort: str | None = None,
    ) -> None:
        self.model = model
        self.max_attempts = max_attempts
        self.reasoning_effort = reasoning_effort  # Only sent if set (not every model supports it).
        # One entry per successful API call: step, model, tokens and time. See `summarize_usage`.
        self.usage_log: list[dict[str, Any]] = []
        # No max_tokens on purpose: Groq's free tier counts it against an 8k tokens-per-minute
        # cap and rejects big values outright. Cut-off replies are caught below instead.
        # max_retries=0: we retry ourselves so every wait is visible in the console.
        self._client = OpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout_seconds, max_retries=0
        )

    def complete(
        self,
        system: str,
        user: str,
        *,
        label: str,
        temperature: float,
        json_mode: bool = False,
    ) -> str:
        """See `LLMClient.complete`."""
        extra: dict[str, Any] = {}
        if json_mode:
            extra["response_format"] = {"type": "json_object"}
        if self.reasoning_effort:
            extra["reasoning_effort"] = self.reasoning_effort

        waited = 0.0  # Seconds spent waiting out rate limits for this call.
        for attempt in range(1, self.max_attempts + 1):
            started = time.perf_counter()
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    **extra,
                )
            except _RETRYABLE_ERRORS as exc:
                if "too large" in str(exc).lower():
                    # The request exceeds a hard per-request limit; waiting will not help.
                    raise LLMError(f"[{label}] request too large for this model's limits: {exc}") from exc
                if attempt == self.max_attempts:
                    raise LLMError(f"[{label}] gave up after {attempt} tries: {exc}") from exc
                delay = _retry_delay(exc, attempt)
                logger.warning(
                    "      ...%s on '%s', waiting %.0fs (try %d of %d)",
                    type(exc).__name__, label, delay, attempt, self.max_attempts,
                )
                time.sleep(delay)
                waited += delay
                continue
            except openai.APIError as exc:
                # Wrong key, unknown model, bad request: waiting will not fix these.
                raise LLMError(f"[{label}] {exc}") from exc

            # Record usage before any checks: the tokens were spent even if the reply is unusable.
            usage = response.usage
            self.usage_log.append({
                "label": label,
                "model": self.model,
                "input_tokens": usage.prompt_tokens if usage else 0,
                "output_tokens": usage.completion_tokens if usage else 0,
                "seconds": round(time.perf_counter() - started, 2),
                "waited_seconds": round(waited, 1),
            })

            choice = response.choices[0]
            text = choice.message.content or ""
            if choice.finish_reason == "length":
                # A cut-off lesson would silently lose its last sections, so never use it.
                raise LLMError(f"[{label}] the reply was cut off at the output token limit")
            if not text.strip():
                raise LLMError(f"[{label}] the model returned an empty reply")
            return text

        raise LLMError(f"[{label}] no reply")  # Only reached if max_attempts < 1.


def _retry_delay(exc: Exception, attempt: int) -> float:
    """Seconds to wait before the next try.

    Use the server's `retry-after` header when it sends one; otherwise back off
    exponentially (2, 4, 8, ... seconds, capped at 60).
    """
    response = getattr(exc, "response", None)
    header = response.headers.get("retry-after") if response is not None else None
    if header:
        try:
            return min(float(header) + 1.0, 90.0)
        except ValueError:
            pass
    return float(min(2**attempt, 60))


def summarize_usage(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Total tokens and time for a list of usage entries, overall and per step.

    Steps are grouped by the part of the label before ":", so all six judges add up
    under "judge".
    """
    by_step: dict[str, dict[str, Any]] = {}
    for call in calls:
        step = by_step.setdefault(
            call["label"].split(":")[0], {"calls": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0}
        )
        step["calls"] += 1
        step["input_tokens"] += call["input_tokens"]
        step["output_tokens"] += call["output_tokens"]
        step["seconds"] = round(step["seconds"] + call["seconds"], 2)
    return {
        "calls": len(calls),
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
        "total_tokens": sum(c["input_tokens"] + c["output_tokens"] for c in calls),
        "model_seconds": round(sum(c["seconds"] for c in calls), 1),
        "rate_limit_wait_seconds": round(sum(c["waited_seconds"] for c in calls), 1),
        "by_step": by_step,
    }


def parse_json_object(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of a model reply.

    Models sometimes wrap JSON in ```json fences or add a sentence before it, so we take
    the text between the first "{" and the last "}".

    Raises:
        ValueError: if no valid JSON object is found.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in the reply")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("the reply is JSON but not an object")
    return data


def complete_json(
    llm: LLMClient, system: str, user: str, *, label: str, temperature: float
) -> dict[str, Any]:
    """Ask for a JSON object; if the reply is not valid JSON, ask once more.

    The first try uses the provider's JSON mode. Some providers reject a reply that fails
    their own JSON validation, so the second try asks in plain text and we parse it ourselves.

    Raises:
        LLMError: if both replies are unusable.
    """
    reminder = "\n\nIMPORTANT: Reply with ONE valid JSON object and nothing else."
    attempts = [(user, True), (user + reminder, False)]
    for prompt, json_mode in attempts:
        try:
            reply = llm.complete(system, prompt, label=label, temperature=temperature, json_mode=json_mode)
            return parse_json_object(reply)
        except ValueError as exc:
            logger.warning("      ...'%s' reply was not valid JSON (%s); asking again", label, exc)
        except LLMError as exc:
            if "json" not in str(exc).lower():
                raise  # Not a JSON problem (e.g. rate limit gave up): do not hide it.
            logger.warning("      ...'%s' provider rejected the JSON reply; asking again", label)
    raise LLMError(f"[{label}] did not return valid JSON after 2 tries")
