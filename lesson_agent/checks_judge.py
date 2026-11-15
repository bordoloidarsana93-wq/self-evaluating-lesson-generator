"""The six LLM-judge checks and the evidence rule.

Some qualities (accuracy, flow, good examples) cannot be measured with code, so a judge
model checks them. To keep the judges honest:

- One separate call per check at temperature 0: a narrow question gives a sharper answer.
- Evidence rule: a FAIL only counts if the judge quotes the offending text AND code
  confirms that quote really exists in the lesson. Made-up quotes are dropped; a FAIL
  with no verified quote left is discarded. Judges list every problem at once, so the
  reviser can fix them all in one round.
- Coverage works the other way round, because missing content has nothing to quote: the
  judge must PROVE each must-cover point with a quote, and code checks that the quote
  exists in the main lesson text (not just in Key words, Recap or the quiz). A point
  without a verified quote counts as missing. This stops a lenient judge from waving
  through a lesson that only names a topic.
- If a judge cannot give a usable answer, the check fails ("fail closed"): we never ship
  a lesson that was not actually checked.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .knowledge import Knowledge
from .llm import LLMClient, LLMError, complete_json
from .prompts import JUDGE_SYSTEM, judge_prompt
from .state import CheckResult, make_result
from .text_utils import quote_in_text, remove_sections

logger = logging.getLogger(__name__)

# Evidence text for a check that failed because the judge could not answer (an
# infrastructure problem, not a content problem). Memory ignores these failures.
NO_JUDGE_ANSWER = "(no judge answer)"


@dataclass(frozen=True)
class JudgeCheck:
    """One rubric question for the judge model."""

    id: str
    name: str
    criterion: str
    context: str = "none"  # Extra material: "reference", "must_cover", "known_terms" or "none".


JUDGE_CHECKS: tuple[JudgeCheck, ...] = (
    JudgeCheck(
        "accuracy", "Accurate & grounded",
        "Is every factual claim in the lesson consistent with the REFERENCE SHEET? FAIL if any "
        "statement contradicts it (for example, a claim that RAG retrains or changes the model). "
        "Simplifications are fine as long as they are not wrong.",
        context="reference",
    ),
    JudgeCheck(
        "coverage", "Covers key points",
        "Does the lesson clearly explain every MUST-COVER point below? Check each point one by one. "
        "A point counts only if the main lesson text explains it in simple words, in at least one "
        "full sentence. A point that is only named, or that appears only in the Key words, Recap "
        "or quiz sections, is MISSING.",
        context="must_cover",
    ),
    JudgeCheck(
        "unexplained_jargon", "No unexplained jargon",
        "Does the lesson avoid technical words or abbreviations that a beginner would not know, "
        "unless they are explained in simple words where they first appear? FAIL if any such word "
        "is used without explanation.",
        context="known_terms",
    ),
    JudgeCheck(
        "worked_example", "Teaches by a worked example",
        "Does the lesson include at least one concrete, relatable worked example from everyday "
        "life (something a young person in India would know) that walks step by step through how "
        "RAG handles it: retrieve, augment, generate? FAIL if the example is missing, abstract or "
        "skips steps. If FAIL, quote the weakest part of the example (or its heading).",
    ),
    JudgeCheck(
        "flow", "Coherent flow",
        "Is every concept explained before or where it is first used? FAIL if a sentence uses a "
        "term or idea that the lesson only explains later. If FAIL, quote the sentence that uses "
        "it too early.",
    ),
    JudgeCheck(
        "simple_english", "Simple English",
        "Is the English simple enough for a reader with limited English vocabulary? FAIL if there "
        "are idioms, slang or figures of speech (like 'a piece of cake', 'under the hood', "
        "'game-changer') or long, complex sentences.",
    ),
)


def _context_text(check: JudgeCheck, kb: Knowledge) -> str:
    """Return the extra material this judge needs to see."""
    if check.context == "reference":
        return f"\nREFERENCE SHEET (ground truth):\n<<<\n{kb.reference}\n>>>\n"
    if check.context == "must_cover":
        points = "\n".join(f"- [{p.id}] {p.point}" for p in kb.must_cover)
        return f"\nMUST-COVER POINTS (use the ids in brackets):\n{points}\n"
    if check.context == "known_terms":
        return (
            "\nIGNORE these terms; a separate check makes sure they are defined: "
            f"{', '.join(kb.jargon_terms)}, RAG.\n"
        )
    return ""


def run_judge_check(
    check: JudgeCheck,
    lesson: str,
    kb: Knowledge,
    llm: LLMClient,
    temperature: float,
    feedback_notes: list[str],
) -> CheckResult:
    """Ask the judge one question and apply the evidence rule to its answer."""
    coverage = check.id == "coverage"
    prompt = judge_prompt(check.name, check.criterion, lesson, _context_text(check, kb), feedback_notes, coverage)

    try:
        reply = complete_json(llm, JUDGE_SYSTEM, prompt, label=f"judge:{check.id}", temperature=temperature)
    except LLMError as exc:
        logger.warning("      ...judge '%s' failed to answer: %s", check.id, exc)
        return make_result(
            check.id, check.name, "judge", False,
            reason=f"Judge gave no usable answer, so the check fails closed ({exc}).",
            evidence=NO_JUDGE_ANSWER,
            fix="Re-run the evaluation; if it keeps failing, check the judge model settings.",
        )

    reason = str(reply.get("reason", "")).strip() or "(no reason given)"
    fix = str(reply.get("fix", "")).strip()
    if coverage:
        return _coverage_result(check, reply, lesson, kb, fix)

    if reply.get("pass") is True:
        return make_result(check.id, check.name, "judge", True, reason)

    # The judge lists every problem it found, so the reviser can fix them all in one round.
    raw = reply.get("quotes", [])
    quotes = [str(q).strip() for q in raw if str(q).strip()] if isinstance(raw, list) else []
    verified = [q for q in quotes if quote_in_text(q, lesson)]
    if verified:
        evidence = " | ".join(f'"{q}"' for q in verified)
        return make_result(check.id, check.name, "judge", False, reason, evidence=evidence, fix=fix)

    # Evidence rule: no quote could be verified, so the FAIL is discarded.
    shown = " | ".join(f'"{q}"' for q in quotes) if quotes else "no quote"
    return make_result(
        check.id, check.name, "judge", True,
        reason=f"Judge said FAIL, but its evidence ({shown}) was not found in the lesson, so the "
               f"FAIL was discarded (evidence rule). Judge's reason: {reason}",
        overruled=True,
    )


def _coverage_result(check: JudgeCheck, reply: dict, lesson: str, kb: Knowledge, fix: str) -> CheckResult:
    """A point is covered only if the judge's quote for it exists in the main lesson text."""
    # Summary sections do not count as "explaining" a point.
    main_text = remove_sections(lesson, [kb.glossary_section, "Recap", kb.quiz_section])
    quotes = reply.get("points", {})
    quotes = quotes if isinstance(quotes, dict) else {}

    missing = [
        p for p in kb.must_cover
        if not quote_in_text(str(quotes.get(p.id) or ""), main_text)
    ]
    covered = len(kb.must_cover) - len(missing)
    if not missing:
        return make_result(
            check.id, check.name, "judge", True,
            f"All {covered} must-cover points are explained, each proven by a verified quote.",
        )
    return make_result(
        check.id, check.name, "judge", False,
        reason=f"{len(missing)} of {len(kb.must_cover)} must-cover point(s) are not clearly explained "
               "in the main lesson text.",
        evidence="Missing: " + "; ".join(f"[{p.id}] {p.point}" for p in missing),
        fix=fix or "Explain each missing point in the main lesson (not only in Key words or Recap), "
                   "in simple full sentences.",
    )
