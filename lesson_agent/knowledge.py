"""Loads the files in `knowledge/`: the topic spec, the RAG reference sheet and the word lists.

Keeping these as data files (not code) means a content expert can change the rubric inputs,
such as adding a hard word or a must-cover point, without touching Python.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MustCoverPoint:
    """One key point the lesson has to explain (checked by the coverage judge)."""

    id: str
    point: str


@dataclass(frozen=True)
class Knowledge:
    """All the reference material the generator and the evaluator need."""

    topic: str
    audience: str
    required_sections: list[str]
    glossary_section: str
    quiz_section: str
    must_cover: list[MustCoverPoint]
    reference: str  # The curated RAG reference sheet (ground truth for accuracy).
    hard_words: list[str]
    jargon_terms: list[str]


def load_knowledge(knowledge_dir: Path) -> Knowledge:
    """Read every knowledge file from `knowledge_dir` into one `Knowledge` object."""
    spec = json.loads((knowledge_dir / "topic_spec.json").read_text(encoding="utf-8"))
    return Knowledge(
        topic=spec["topic"],
        audience=spec["audience"],
        required_sections=spec["required_sections"],
        glossary_section=spec["glossary_section"],
        quiz_section=spec["quiz_section"],
        must_cover=[MustCoverPoint(p["id"], p["point"]) for p in spec["must_cover"]],
        reference=(knowledge_dir / "rag_reference.md").read_text(encoding="utf-8"),
        hard_words=_read_word_list(knowledge_dir / "hard_words.txt"),
        jargon_terms=_read_word_list(knowledge_dir / "jargon_terms.txt"),
    )


def _read_word_list(path: Path) -> list[str]:
    """Read one entry per line, skipping blank lines and `#` comments."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
