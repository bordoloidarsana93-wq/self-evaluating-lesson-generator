"""Every prompt in one place.

Each function builds the text for one LLM call. Keeping prompts here (not scattered in the
logic) makes them easy to read, review and improve.
"""

from __future__ import annotations

from .knowledge import Knowledge
from .state import CheckResult

# --- Shared pieces ------------------------------------------------------------------------

TEACHER_SYSTEM = (
    "You are an expert teacher who writes beginner lessons about AI. Your readers finished "
    "12th grade in India, studied in a non-English-medium school, and have a limited English "
    "vocabulary. You write in simple, clear, correct English and you never invent facts."
)


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _must_cover(kb: Knowledge) -> str:
    # No ids here: the generator once copied ids like "rag_vs_finetuning" into the lesson.
    return "\n".join(f"- {p.point}" for p in kb.must_cover)


def _writing_rules(kb: Knowledge) -> str:
    """Style rules shared by the generator and the reviser, so a fix never breaks another check."""
    return f"""WRITING RULES (every rule is checked automatically):
- Use short sentences: 8 to 15 words on average. One idea per sentence.
- Use common, everyday words. No idioms, slang or figures of speech.
- Never use these words: {", ".join(kb.hard_words)}.
- Explain every technical word in simple words the first time you use it.
- Never use a concept before you have explained it.
- If you use any of these terms, you MUST also define it in "## {kb.glossary_section}": {", ".join(kb.jargon_terms)}.
- Do not use any other technical term unless you explain it right where you use it.
- Every fact must agree with the reference sheet."""


# --- Plan, generate, revise ---------------------------------------------------------------

def plan_prompt(kb: Knowledge) -> str:
    """Ask for a short teaching plan before writing the full lesson."""
    return f"""Plan a beginner lesson. Do not write the lesson yet.

TOPIC: {kb.topic}
LEARNER: {kb.audience}

The lesson must use these sections, in this order: {", ".join(kb.required_sections)}.
It must explain these key points:
{_must_cover(kb)}

Write a short plan (max 250 words):
1. For each section, 2-3 bullet points of what it will teach.
2. One concrete, relatable worked example from daily life in India that you will trace
   step by step through retrieve, augment and generate.
3. The technical terms to introduce, in the order they will first appear."""


def generate_prompt(
    kb: Knowledge,
    plan: str,
    lessons_learned: list[str],
    common_failures: list[str],
) -> str:
    """Ask for the full lesson, adding rules learned from earlier runs (memory)."""
    memory_block = ""
    if lessons_learned:
        memory_block += "\nLESSONS LEARNED FROM PAST RUNS (follow these):\n" + _bullets(lessons_learned) + "\n"
    if common_failures:
        memory_block += "\nCHECKS THAT PAST LESSONS OFTEN FAILED (take extra care):\n" + _bullets(common_failures) + "\n"

    headings = "\n".join(f"## {title}" for title in kb.required_sections)
    return f"""Write a complete beginner lesson in Markdown.

TOPIC: {kb.topic}
LEARNER: {kb.audience}

YOUR PLAN:
{plan}

STRUCTURE:
- Start with one "# " title line.
- Use these "## " headings, in this order, with these exact words:
{headings}
- Also add a "## Limits, and RAG compared with fine-tuning" section just before
  "## {kb.glossary_section}". Explain each limit and the comparison in full sentences there.
- In "## Why it matters", describe at least one real-world use case (who uses RAG, for what).
- "## {kb.glossary_section}": a bullet list, one term per line: "- **Term**: simple definition."
  List ONLY technical terms that you actually used in the lesson text above it.
- "## {kb.quiz_section}": 4 numbered questions, each a real question ending in "?", each
  followed by an indented line that starts with "**Answer:**".
- Length: 1000 to 1400 words. Explain ideas fully in short sentences; do not just list terms.
- A point mentioned only in the Recap or Key words does NOT count as explained.

KEY POINTS THE LESSON MUST EXPLAIN:
{_must_cover(kb)}

{_writing_rules(kb)}
{memory_block}
REFERENCE SHEET (the only source of facts):
<<<
{kb.reference}
>>>

Reply with the lesson in Markdown only. No notes before or after it."""


def revise_prompt(kb: Knowledge, lesson: str, failed: list[CheckResult]) -> str:
    """Targeted revision: send only the failed checks and ask to keep everything else."""
    problems = "\n\n".join(
        f"CHECK: {c['name']}\nREASON: {c['reason']}\nEVIDENCE: {c['evidence']}\nFIX: {c['fix']}"
        for c in failed
    )
    reference = ""
    if any(c["id"] == "accuracy" for c in failed):
        reference = f"\nREFERENCE SHEET (the only source of facts):\n<<<\n{kb.reference}\n>>>\n"

    return f"""The lesson below failed some quality checks. Fix ONLY these problems.
Keep every other sentence, heading and section exactly as it is.

FAILED CHECKS:
{problems}

{_writing_rules(kb)}
{reference}
LESSON:
<<<
{lesson}
>>>

Reply in exactly this format:
<lesson>
(the full corrected lesson in Markdown)
</lesson>
<changes>
- (one short line for each change you made)
</changes>"""


# --- Judges -------------------------------------------------------------------------------

JUDGE_SYSTEM = (
    "You are a strict but fair reviewer of beginner lessons. You check exactly ONE criterion. "
    "You FAIL a lesson only for a real, specific problem that you can point to in the text. "
    "You reply with one JSON object and nothing else."
)


def judge_prompt(
    criterion_name: str,
    criterion: str,
    lesson: str,
    context: str,
    feedback_notes: list[str],
    coverage: bool,
) -> str:
    """Build the prompt for one judge check.

    `context` carries extra material (reference sheet, must-cover list, known terms).
    `feedback_notes` are human reviewer notes stored in memory for this check.
    """
    notes = ""
    if feedback_notes:
        notes = "\nNOTES FROM HUMAN REVIEWERS (follow them):\n" + _bullets(feedback_notes) + "\n"

    if coverage:
        answer_format = (
            '{"points": {"<point id>": "the exact sentence from the main lesson text that explains '
            'this point, copied character for character, or empty if it is not explained"}, '
            '"reason": "short explanation", "fix": "how to explain the missing points, or empty"}'
        )
    else:
        answer_format = (
            '{"pass": true or false, "reason": "short explanation", '
            '"quotes": ["if FAIL: for EVERY problem you found, the exact words from the lesson '
            'that show it, copied character for character (max 30 words each). If PASS: empty list"], '
            '"fix": "how to fix all the problems, or empty"}'
        )

    return f"""CRITERION: {criterion_name}
{criterion}
{context}{notes}
LESSON TO REVIEW:
<<<
{lesson}
>>>

Reply with JSON only, in this format:
{answer_format}"""


# --- Reflect (memory) ---------------------------------------------------------------------

REFLECT_SYSTEM = (
    "You turn quality-check failures into short, general writing rules that will help "
    "future lessons pass on the first try. You reply with one JSON object only."
)


def reflect_prompt(failures: list[str], existing_rules: list[str]) -> str:
    """Ask for up to 3 general rules; reuse an existing rule's exact words if it already fits."""
    existing = _bullets(existing_rules) if existing_rules else "(none yet)"
    return f"""These checks failed while writing a beginner lesson:
{_bullets(failures)}

EXISTING RULES:
{existing}

Write at most 3 rules that would prevent these failures next time.
- Each rule: one instruction, max 20 words, general (useful for any lesson, not just this one).
- If an existing rule already covers a failure, return that rule copied exactly.

Reply with JSON only: {{"rules": ["rule 1", "rule 2"]}}"""
