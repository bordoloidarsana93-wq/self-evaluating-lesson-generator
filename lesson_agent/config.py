"""Project settings.

Everything you might want to tune lives here: the LLM provider and models, the retry
budget, the temperatures, and the thresholds for the code checks. API keys are read from a
`.env` file and are never hard-coded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ConfigError(RuntimeError):
    """Raised when settings are missing or invalid (for example, no API key)."""


@dataclass(frozen=True)
class Provider:
    """Connection details and default models for one OpenAI-compatible provider."""

    base_url: str | None  # None means the official OpenAI endpoint.
    api_key_env: str  # Name of the environment variable that holds the key.
    generator_model: str  # Writes and revises the lesson.
    judge_model: str  # Grades the lesson. A different model avoids "grading its own homework".
    # How much a reasoning model "thinks" before judging. "low" halves judge tokens on Groq's
    # gpt-oss models and still caught every known flaw in tests. None = provider default.
    judge_reasoning_effort: str | None = None


# Groq, Gemini and OpenAI all speak the OpenAI API, so one client works for all three.
PROVIDERS: dict[str, Provider] = {
    "groq": Provider(
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        # Free-tier quotas are per model, so the jobs are split: the generator makes few calls
        # (about 20k tokens a run); the judge makes 6 calls per attempt (about 60-70k a run).
        generator_model="openai/gpt-oss-120b",  # Writes complete, well-structured lessons.
        judge_model="openai/gpt-oss-20b",  # A separate model and quota; caught every known flaw in tests.
        judge_reasoning_effort="low",
    ),
    # Free with any GitHub account (no card). Key = a GitHub personal access token with the
    # "Models" read permission. Free limits are small (roughly 150 requests a day on smaller
    # models), which is enough for a few runs.
    "github": Provider(
        base_url="https://models.github.ai/inference",
        api_key_env="GITHUB_TOKEN",
        generator_model="openai/gpt-4.1-mini",
        judge_model="openai/gpt-4.1-mini",
    ),
    "gemini": Provider(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key_env="GEMINI_API_KEY",
        generator_model="gemini-2.5-flash",
        judge_model="gemini-2.5-flash",
    ),
    "openai": Provider(
        base_url=None,
        api_key_env="OPENAI_API_KEY",
        generator_model="gpt-4.1-mini",
        judge_model="gpt-4.1",
    ),
}


@dataclass(frozen=True)
class Thresholds:
    """Limits used by the deterministic code checks (calibrated on real lessons)."""

    min_words: int = 700
    max_words: int = 1800
    max_avg_sentence_words: float = 16.0
    min_flesch_reading_ease: float = 60.0
    min_quiz_questions: int = 3


@dataclass(frozen=True)
class Settings:
    """All runtime settings in one immutable object.

    Every field has a default, so tests can build `Settings(memory_path=tmp_path / ...)`
    without touching `.env`.
    """

    provider: str = "groq"
    api_key: str = ""
    base_url: str | None = PROVIDERS["groq"].base_url
    generator_model: str = PROVIDERS["groq"].generator_model
    judge_model: str = PROVIDERS["groq"].judge_model
    judge_reasoning_effort: str | None = PROVIDERS["groq"].judge_reasoning_effort

    max_retries: int = 2  # At most 1 + 2 = 3 evaluated attempts. The loop always ends.
    generator_temperature: float = 0.7  # Some creativity for a natural lesson.
    reviser_temperature: float = 0.3  # Revisions should change as little as possible.
    judge_temperature: float = 0.0  # Judges must be as repeatable as possible.

    top_rules_in_prompt: int = 5  # How many "lessons learned" go into the generator prompt.
    thresholds: Thresholds = field(default_factory=Thresholds)

    knowledge_dir: Path = PROJECT_ROOT / "knowledge"
    memory_path: Path = PROJECT_ROOT / "memory" / "memory.json"
    outputs_dir: Path = PROJECT_ROOT / "outputs"


def load_settings(require_api_key: bool = True) -> Settings:
    """Build `Settings` from environment variables (and the `.env` file).

    Args:
        require_api_key: If True, raise `ConfigError` when the provider's key is missing.
            Commands that never call a model (like `diagram`) pass False.
    """
    load_dotenv(PROJECT_ROOT / ".env")

    provider_name = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    if provider_name not in PROVIDERS:
        raise ConfigError(
            f"Unknown LLM_PROVIDER '{provider_name}'. Choose one of: {', '.join(PROVIDERS)}."
        )
    provider = PROVIDERS[provider_name]

    api_key = os.getenv(provider.api_key_env, "").strip()
    if require_api_key and not api_key:
        raise ConfigError(
            f"{provider.api_key_env} is not set. Copy .env.example to .env and add your key."
        )

    return Settings(
        provider=provider_name,
        api_key=api_key,
        base_url=provider.base_url,
        generator_model=os.getenv("GENERATOR_MODEL") or provider.generator_model,
        judge_model=os.getenv("JUDGE_MODEL") or provider.judge_model,
        judge_reasoning_effort=provider.judge_reasoning_effort,
    )
