"""lesson_agent: a self-evaluating lesson generator.

The workflow plans a beginner lesson, writes it, grades it against a hard pass/fail rubric
(code checks + LLM judges), revises it until it passes (or the retry budget runs out), and
learns from its failures across runs.
"""

__version__ = "1.0.0"
