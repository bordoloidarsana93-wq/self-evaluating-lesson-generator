"""The shared tools every node needs, bundled into one object.

LangGraph nodes receive only the state, so `graph.py` passes this object to each node
with `functools.partial`. Tests build it with fake LLMs and temporary paths instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .knowledge import Knowledge, load_knowledge
from .llm import LLMClient, OpenAICompatibleClient
from .memory import MemoryStore


@dataclass
class Services:
    settings: Settings
    knowledge: Knowledge
    memory: MemoryStore
    generator: LLMClient  # Plans, writes and revises the lesson; also writes reflections.
    judge: LLMClient  # Grades the lesson (a separate model where possible).


def build_services(settings: Settings) -> Services:
    """Create the real services from settings."""
    # The diagram command never calls a model, so a placeholder key is fine there.
    api_key = settings.api_key or "not-set"
    return Services(
        settings=settings,
        knowledge=load_knowledge(settings.knowledge_dir),
        memory=MemoryStore(settings.memory_path),
        generator=OpenAICompatibleClient(model=settings.generator_model, api_key=api_key, base_url=settings.base_url),
        judge=OpenAICompatibleClient(
            model=settings.judge_model, api_key=api_key, base_url=settings.base_url,
            reasoning_effort=settings.judge_reasoning_effort,
        ),
    )
