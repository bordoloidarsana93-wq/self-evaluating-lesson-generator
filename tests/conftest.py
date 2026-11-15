"""Shared test helpers: settings in a temp folder, a known-good lesson, and fake LLMs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lesson_agent.config import Settings
from lesson_agent.knowledge import load_knowledge
from lesson_agent.memory import MemoryStore
from lesson_agent.nodes import INJECTED_FALSE_CLAIM
from lesson_agent.services import Services
from tests.fake_llm import FakeLLM

GOOD_LESSON = (Path(__file__).parent / "fixtures" / "good_lesson.md").read_text(encoding="utf-8")
LEARNED_RULE = "Use only simple everyday words; never use words from the hard-words list."

PASS_JSON = json.dumps({"pass": True, "reason": "Looks good.", "quotes": [], "fix": ""})

# Coverage proof: for each must-cover id, a sentence that really is in GOOD_LESSON's main text.
COVERAGE_QUOTES = {
    "retrieve": "Retrieve: find the useful information.",
    "augment": "Augment: add that information to the question.",
    "generate": "Generate: the LLM writes the answer.",
    "chunking": "A chunk is a small piece of a document, such as one paragraph.",
    "embeddings": "An embedding is a list of numbers that captures the meaning of a piece of text.",
    "similarity_search": "A similarity search finds the chunks whose embeddings are closest to the question's embedding.",
    "real_use_case": "For example, a bank can let its chatbot read its own rules.",
    "limits": "If the retriever finds the wrong chunks, the answer will be wrong too.",
    "rag_vs_finetuning": "Fine-tuning means training an existing model a little more on your own examples.",
}


def coverage_json(quotes: dict[str, str] = COVERAGE_QUOTES) -> str:
    return json.dumps({"points": quotes, "reason": "Checked each point.", "fix": ""})


def fail_json(*quotes: str, reason: str = "Problem found.") -> str:
    return json.dumps({"pass": False, "reason": reason, "quotes": list(quotes), "fix": "Fix it."})


def make_generator(first_draft: str = GOOD_LESSON, revised: str = GOOD_LESSON) -> FakeLLM:
    """A fake generator: plans, writes `first_draft`, revises to `revised`, reflects one rule."""
    return FakeLLM({
        "plan": "1. What is RAG\n2. Why it matters\n3. How it works",
        "generate": first_draft,
        "revise": f"<lesson>\n{revised}\n</lesson>\n<changes>\n- Fixed the failed checks.\n</changes>",
        "reflect": json.dumps({"rules": [LEARNED_RULE]}),
    })


def make_judge() -> FakeLLM:
    """A fake judge that passes everything, except the accuracy judge catches the planted claim."""
    def accuracy(prompt: str) -> str:
        if "RAG retrains the model on your documents" in prompt:
            return fail_json(INJECTED_FALSE_CLAIM, reason="Contradicts the reference: RAG does not retrain the model.")
        return PASS_JSON

    return FakeLLM({"judge:accuracy": accuracy, "judge:coverage": coverage_json(), "judge": PASS_JSON})


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Real knowledge files, but memory and outputs go to a temp folder."""
    return Settings(memory_path=tmp_path / "memory.json", outputs_dir=tmp_path / "outputs")


@pytest.fixture
def knowledge(settings: Settings):
    return load_knowledge(settings.knowledge_dir)


def make_services(settings: Settings, generator: FakeLLM | None = None, judge: FakeLLM | None = None) -> Services:
    """Build Services with fakes. A fresh MemoryStore reads whatever is on disk at that moment."""
    return Services(
        settings=settings,
        knowledge=load_knowledge(settings.knowledge_dir),
        memory=MemoryStore(settings.memory_path),
        generator=generator or make_generator(),
        judge=judge or make_judge(),
    )
