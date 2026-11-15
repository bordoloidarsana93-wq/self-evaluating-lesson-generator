"""Small, pure text helpers used by the code checks, the evidence rule and the nodes.

No I/O and no LLM calls here, so every function is easy to unit-test.
"""

from __future__ import annotations

import re

_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_SECTION_HEADING = re.compile(r"^##\s+(.+?)\s*$")  # Level-2 headings only ("## Recap").
_ANY_HEADING = re.compile(r"^#{1,6}\s")
_LIST_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_WORD = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


# --- Sections -----------------------------------------------------------------------------

def normalize_heading(heading: str) -> str:
    """Lowercase a heading and drop numbering and punctuation: "2. What is RAG?" -> "what is rag"."""
    text = re.sub(r"[^a-z0-9 ]", " ", heading.lower())
    text = re.sub(r"^\s*\d+\s+", "", text)  # Leading "2 " left over from "2."
    return " ".join(text.split())


def split_sections(markdown: str) -> dict[str, str]:
    """Map each normalized `## ` heading to the text under it (up to the next `## `)."""
    sections: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    for line in strip_code_blocks(markdown).splitlines():
        match = _SECTION_HEADING.match(line)
        if match:
            if current is not None:
                sections[current] = "\n".join(body).strip()
            current, body = normalize_heading(match.group(1)), []
        elif current is not None:
            body.append(line)
    if current is not None:
        sections[current] = "\n".join(body).strip()
    return sections


def remove_sections(markdown: str, titles: list[str]) -> str:
    """Return the markdown without the `## ` sections whose headings contain any of `titles`."""
    wanted = [normalize_heading(t) for t in titles]
    kept, skipping = [], False
    for line in markdown.splitlines():
        match = _SECTION_HEADING.match(line)
        if match:
            heading = normalize_heading(match.group(1))
            skipping = any(w in heading for w in wanted)
        if not skipping:
            kept.append(line)
    return "\n".join(kept)


def find_section(sections: dict[str, str], title: str) -> str | None:
    """Return the body of the first section whose heading contains `title`, else None.

    Matching on "contains" lets "Key words" match "Key words (glossary)".
    """
    wanted = normalize_heading(title)
    for heading, body in sections.items():
        if wanted in heading:
            return body
    return None


# --- Prose, words and sentences -----------------------------------------------------------

def strip_code_blocks(markdown: str) -> str:
    """Remove fenced ``` code blocks."""
    return _CODE_BLOCK.sub("", markdown)


def strip_outer_fence(text: str) -> str:
    """Remove a ```markdown ... ``` fence if the model wrapped its whole answer in one."""
    stripped = text.strip()
    match = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", stripped, re.DOTALL)
    return match.group(1).strip() if match else stripped


def prose_lines(markdown: str) -> list[str]:
    """Return the readable text lines: no code blocks, headings, tables or markdown symbols."""
    lines = []
    for raw in strip_code_blocks(markdown).splitlines():
        line = raw.strip()
        if not line or _ANY_HEADING.match(line) or line.startswith("|") or set(line) <= {"-", "*", "_"}:
            continue
        line = _LIST_MARKER.sub("", line)
        line = _LINK.sub(r"\1", line)
        line = re.sub(r"[*_`>]", "", line).strip()
        if line:
            lines.append(line)
    return lines


def words(text: str) -> list[str]:
    """Split text into words (keeps "don't" and "fine-tuning" as one word)."""
    return _WORD.findall(text)


def sentences(lines: list[str]) -> list[str]:
    """Split prose lines into sentences.

    A line break also ends a sentence, so list items without a full stop are not glued
    together into one giant "sentence".
    """
    result = []
    for line in lines:
        result.extend(part for part in _SENTENCE_END.split(line) if words(part))
    return result


def count_syllables(word: str) -> int:
    """Estimate syllables with the usual vowel-group heuristic (good enough for Flesch)."""
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and not word.endswith(("le", "ee")) and count > 1:
        count -= 1  # Silent final "e", as in "make".
    return max(count, 1)


def readability(markdown: str) -> tuple[float, float]:
    """Return (Flesch reading ease, average words per sentence) for the lesson's prose.

    Flesch reading ease = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words).
    Higher is easier; 60-70 is plain English.
    """
    sents = sentences(prose_lines(markdown))
    all_words = [w for s in sents for w in words(s)]
    if not sents or not all_words:
        return 0.0, 0.0
    words_per_sentence = len(all_words) / len(sents)
    syllables_per_word = sum(count_syllables(w) for w in all_words) / len(all_words)
    flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    return round(flesch, 1), round(words_per_sentence, 1)


# --- Matching -----------------------------------------------------------------------------

def snippet(text: str, start: int, end: int, width: int = 40) -> str:
    """Return the matched text with a little context on each side, on one line."""
    left, right = max(0, start - width), min(len(text), end + width)
    piece = " ".join(text[left:right].split())
    return f"...{piece}..."


def normalize_for_match(text: str) -> str:
    """Make text comparison forgiving about case, spacing, quotes, dashes and markdown symbols."""
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[*_`#>]", "", text)
    return " ".join(text.lower().split())


def quote_in_text(quote: str, text: str) -> bool:
    """True if a judge's quote really appears in the text (the evidence rule).

    Judges sometimes shorten a quote with "..." so each part must appear. Surrounding
    quote marks and end punctuation are ignored.
    """
    haystack = normalize_for_match(text)
    parts = [
        normalize_for_match(part).strip(" .,;:!?\"'")
        for part in re.split(r"\.\.\.|…", quote)
    ]
    parts = [part for part in parts if part]
    return bool(parts) and all(part in haystack for part in parts)


def extract_tag(text: str, tag: str) -> str | None:
    """Return the content between <tag> and </tag>, or None if the tag is missing."""
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else None
