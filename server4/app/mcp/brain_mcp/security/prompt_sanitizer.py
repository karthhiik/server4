"""
Prompt injection prevention for user-provided refinement instructions.
Strips suspicious patterns before sending to LLMs.
"""

import re
from typing import Optional


class PromptInjectionError(Exception):
    """Raised when suspicious input is detected."""
    pass


class PromptSanitizer:
    """
    Prevents prompt injection in user-provided instructions.

    Blocks patterns like:
    - "ignore previous instructions"
    - "system prompt" / "you are now"
    - Attempts to extract secrets/keys/env vars
    - Role-play injection ("pretend you are", "act as")
    """

    BLOCKLIST_PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"ignore\s+(all\s+)?above\s+instructions",
        r"disregard\s+(all\s+)?previous",
        r"forget\s+(all\s+)?previous",
        r"override\s+(all\s+)?rules",
        r"you\s+are\s+now\s+a",
        r"pretend\s+(you\s+are|to\s+be)",
        r"act\s+as\s+(a\s+)?",
        r"system\s*prompt",
        r"(print|output|reveal|show|display|return|give)\s*.*(password|key|secret|env|token|api|credential|connection)",
        r"(database|db)\s*.*(password|uri|connection|string)",
        r"\bsudo\b",
        r"\bexec\s*\(",
        r"\beval\s*\(",
        r"__[a-z]+__",  # Python dunder methods
        r"<script",
        r"javascript:",
    ]

    _compiled = [re.compile(p, re.IGNORECASE) for p in BLOCKLIST_PATTERNS]

    @classmethod
    def sanitize(cls, user_input: str) -> str:
        """
        Check user input for injection patterns.
        Returns cleaned input or raises PromptInjectionError.
        """
        if not user_input:
            return ""

        cleaned = user_input.strip()

        for pattern in cls._compiled:
            if pattern.search(cleaned):
                raise PromptInjectionError(
                    "Input contains suspicious patterns and was blocked for safety."
                )

        # Length limit — no single instruction should be enormous
        if len(cleaned) > 5000:
            cleaned = cleaned[:5000]

        return cleaned

    @classmethod
    def is_safe(cls, user_input: str) -> bool:
        """Check if input is safe without raising."""
        try:
            cls.sanitize(user_input)
            return True
        except PromptInjectionError:
            return False
