# Rejection log: run 20261115-160508-d658

- **Topic:** Introduction to RAG (Retrieval-Augmented Generation)
- **Final status:** PASSED (shipped attempt 2 of 2)
- **Models:** generator `qwen/qwen3.8-27b`, judge `openai/gpt-oss-120b` (groq)
- **Error injection:** off

Legend: PASS = check passed. FAIL = check failed. PASS* = a judge said FAIL but its evidence was not found in the lesson, so it was discarded.

## Attempt 1: FAILED (8/12 checks passed)

**What changed before this attempt:**

- First draft.

**Checks:**

- **PASS** Required sections (code): All required sections are present.
- **PASS** Word count (code): 1326 words (allowed 700-1800).
- **PASS** Readability (code): Flesch 75.7, average sentence 7.3 words.
- **PASS** No hard words (code): No blocklisted words found.
- **FAIL** Jargon defined (code): 1 technical term(s) are used but not defined in 'Key words'.
  - Evidence: 'token' used in ...xt at once. This limit is measured in **tokens**. A token is a piece of a word. If you...
  - Fix: Add a simple definition to 'Key words' for: token (or remove the term if it is not needed).
- **FAIL** Quiz with answers (code): Need at least 3 numbered questions, each with an answer. Found 2 question(s), 4 answer(s).
  - Evidence: 2 question(s), 4 answer(s).
  - Fix: In 'Check your understanding', write at least 3 numbered questions ending in '?', each followed by a line starting with '**Answer:**'.
- **PASS** Accurate & grounded (judge): All factual statements align with the reference sheet; no contradictions found.
- **PASS** Covers key points (judge): All 9 must-cover points are explained, each proven by a verified quote.
- **FAIL** No unexplained jargon (judge): Uses technical term "weights" without explanation
  - Evidence: "changes the model's weights."
  - Fix: Add a brief explanation for "weights", e.g., "weights are the internal parameters of the model that are adjusted during training to learn patterns."
- **PASS** Teaches by a worked example (judge): The lesson provides a concrete, India‑relevant worked example (Class 10 board exam fees in UP) that clearly walks through retrieve, augment, and generate steps.
- **FAIL** Coherent flow (judge): Terms like "augments", "generates", and "retrieving" are used before they are defined later in the key‑words section.
  - Evidence: "Now, the system augments the prompt." | "Finally, the LLM generates the answer." | "It finds the top few chunks. This is called retrieving."
  - Fix: Introduce definitions of augmentation, generation, and retrieval (or retrieving) before their first occurrence, e.g., add brief explanations when the terms first appear.
- **PASS** Simple English (judge): The lesson uses straightforward vocabulary, avoids idioms, slang, and overly complex sentences, meeting the Simple English criterion.

## Attempt 2: PASSED (12/12 checks passed)

**What changed before this attempt:**

- Added definition for 'token' in the 'Key words' section.
- Replaced the matching question in 'Check your understanding' with a direct question to ensure 3 simple numbered questions with answers.
- Added a brief explanation for 'weights' in the 'Limits' section.
- Added brief definitions for 'retrieving', 'augments', and 'generates' at their first occurrence in the 'How it works' section.

**Checks:**

- **PASS** Required sections (code): All required sections are present.
- **PASS** Word count (code): 1358 words (allowed 700-1800).
- **PASS** Readability (code): Flesch 75.4, average sentence 7.7 words.
- **PASS** No hard words (code): No blocklisted words found.
- **PASS** Jargon defined (code): Every technical term used is in Key words.
- **PASS** Quiz with answers (code): 3 question(s), 4 answer(s).
- **PASS** Accurate & grounded (judge): All factual statements in the lesson are consistent with the reference sheet.
- **PASS** Covers key points (judge): All 9 must-cover points are explained, each proven by a verified quote.
- **PASS** No unexplained jargon (judge): No unexplained jargon found.
- **PASS** Teaches by a worked example (judge): Provides a concrete Indian example (Class 10 board fee) and clearly walks through retrieve, augment, generate steps
- **PASS** Coherent flow (judge): All key terms are introduced before or at their first use, providing immediate definitions where needed.
- **PASS** Simple English (judge): The lesson uses straightforward vocabulary and sentence structures without idioms, slang, or overly complex sentences.

## Lessons learned this run (saved to memory)

- Define every technical term immediately before its first use in the text.
- Ensure quiz sections contain at least three numbered questions, each followed by a labeled answer.
- List all technical terms used in the lesson body within the Key words section.
