# Rejection log: run 20261115-194433-7f13

- **Topic:** Introduction to RAG (Retrieval-Augmented Generation)
- **Final status:** PASSED (shipped attempt 3 of 3)
- **Models:** generator `openai/gpt-oss-120b`, judge `openai/gpt-oss-20b` (groq)
- **Error injection:** on
- **Usage:** 23 model calls, 66,671 tokens (writer 20,337, judge 46,334), 322s total

Legend: PASS = check passed. FAIL = check failed. PASS* = a judge said FAIL but its evidence was not found in the lesson, so it was discarded.

## Attempt 1: FAILED (9/12 checks passed)

**What changed before this attempt:**

- First draft.
- INJECTED (demo) false claim: "RAG retrains the model on your documents, so the new facts are stored inside the model itself."
- INJECTED (demo) undefined jargon: "After that, a reranker sorts the results."

**Checks:**

- **PASS** Required sections (code): All required sections are present.
- **PASS** Word count (code): 1120 words (allowed 700-1800).
- **PASS** Readability (code): Flesch 63.4, average sentence 11.2 words.
- **PASS** No hard words (code): No blocklisted words found.
- **FAIL** Jargon defined (code): 1 technical term(s) are used but not defined in 'Key words'.
  - Evidence: 'reranker' used in ...inside the model itself. After that, a reranker sorts the results. RAG has two phases:...
  - Fix: Add a simple definition to 'Key words' for: reranker (or remove the term if it is not needed).
- **PASS** Quiz with answers (code): 3 question(s), 4 answer(s).
- **FAIL** Accurate & grounded (judge): Lesson contains statements that RAG retrains or changes the model, contradicting the reference sheet.
  - Evidence: "RAG retrains the model on your documents, so the new facts are stored inside the model itself. After that, a reranker sorts the results." | "RAG retrains the model on your documents, so the new facts are stored inside the model itself. After that, a reranker sorts the results."
  - Fix: Remove or correct any statements implying that RAG retrains, fine‑tunes, or otherwise changes the LLM’s weights. Clarify that RAG only retrieves, augments, and generates without modifying the model.
- **PASS** Covers key points (judge): All 9 must-cover points are explained, each proven by a verified quote.
- **PASS** No unexplained jargon (judge): All technical terms are either in the ignore list or explained.
- **PASS** Teaches by a worked example (judge): Includes a concrete, relatable worked example with step-by-step Retrieve, Augment, Generate.
- **FAIL** Coherent flow (judge): Terms such as Retriever, similarity search, cosine similarity, top‑k, and context window are used before they are defined.
  - Evidence: "Retriever runs a similarity search in the vector database." | "It measures closeness with cosine similarity and returns the top‑k most similar chunks." | "The LLM reads the prompt (which may be up to a limited size called the context window)"
  - Fix: Move the definitions of Retriever, similarity search, cosine similarity, top‑k, and context window to the beginning of the lesson (e.g., in the introductory section or immediately after the first mention).
- **PASS** Simple English (judge): No idioms, slang, or figures of speech detected.

## Attempt 2: FAILED (9/12 checks passed)

**What changed before this attempt:**

- Revision failed, previous draft kept: [revise] the reply was cut off at the output token limit

**Checks:**

- **PASS** Required sections (code): All required sections are present.
- **PASS** Word count (code): 1120 words (allowed 700-1800).
- **PASS** Readability (code): Flesch 63.4, average sentence 11.2 words.
- **PASS** No hard words (code): No blocklisted words found.
- **FAIL** Jargon defined (code): 1 technical term(s) are used but not defined in 'Key words'.
  - Evidence: 'reranker' used in ...inside the model itself. After that, a reranker sorts the results. RAG has two phases:...
  - Fix: Add a simple definition to 'Key words' for: reranker (or remove the term if it is not needed).
- **PASS** Quiz with answers (code): 3 question(s), 4 answer(s).
- **FAIL** Accurate & grounded (judge): Contains a factual contradiction about RAG retraining the model.
  - Evidence: "RAG retrains the model on your documents, so the new facts are stored inside the model itself. After that, a reranker sorts the results."
  - Fix: Replace the sentence with a correct statement: "RAG does not retrain or fine‑tune the model; it only retrieves documents and augments the prompt at answer time."
- **PASS** Covers key points (judge): All 9 must-cover points are explained, each proven by a verified quote.
- **PASS** No unexplained jargon (judge): All technical terms are either defined or are part of the allowed list.
- **PASS** Teaches by a worked example (judge): Includes a concrete, relatable worked example with step‑by‑step explanation
- **FAIL** Coherent flow (judge): Terms such as Retriever, similarity search, cosine similarity, top‑k, and context window are used before they are defined.
  - Evidence: "Retriever runs a similarity search in the vector database." | "It measures closeness with cosine similarity and returns the top‑k most similar chunks." | "The LLM reads the prompt (which may be up to a limited size called the context window)"
  - Fix: Move the definitions of Retriever, similarity search, cosine similarity, top‑k, and context window to the beginning of the lesson (e.g., in the introductory section or immediately after the first mention).
- **PASS** Simple English (judge): No idioms, slang, or figures of speech detected.

## Attempt 3: PASSED (12/12 checks passed)

**What changed before this attempt:**

- Added early definitions for retriever, similarity search, cosine similarity, top‑k, and context window before first use.
- Replaced incorrect sentence about retraining with correct statement that RAG does not retrain or fine‑tune the model.
- Removed the term “reranker” and its reference, eliminating the undefined jargon.

**Checks:**

- **PASS** Required sections (code): All required sections are present.
- **PASS** Word count (code): 1164 words (allowed 700-1800).
- **PASS** Readability (code): Flesch 63.2, average sentence 11.3 words.
- **PASS** No hard words (code): No blocklisted words found.
- **PASS** Jargon defined (code): Every technical term used is in Key words.
- **PASS** Quiz with answers (code): 3 question(s), 4 answer(s).
- **PASS** Accurate & grounded (judge): All factual claims align with the reference sheet.
- **PASS** Covers key points (judge): All 9 must-cover points are explained, each proven by a verified quote.
- **PASS** No unexplained jargon (judge): All technical terms are defined before use.
- **PASS** Teaches by a worked example (judge): Includes a concrete, relatable worked example with step‑by‑step details
- **PASS** Coherent flow (judge): All terms are defined before first use
- **PASS** Simple English (judge): No idioms, slang, or overly complex sentences detected.

## Lessons learned this run (saved to memory)

- Define every technical term immediately before its first use in the text.
- Verify claims against references to avoid overstating capabilities or contradicting source material.
- List all technical terms used in the lesson body within the Key words section.
