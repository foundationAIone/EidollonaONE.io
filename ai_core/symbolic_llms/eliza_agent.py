"""
ELIZA-like offline conversational fallback (no network).
Simple pattern transforms + reflections, safe in SAFE mode.
"""

from __future__ import annotations
from typing import List, Tuple
import re
import random

REFLECTIONS = {
    "am": "are",
    "was": "were",
    "i": "you",
    "i'd": "you would",
    "i've": "you have",
    "i'll": "you will",
    "my": "your",
    "are": "am",
    "you've": "I have",
    "you'll": "I will",
    "your": "my",
    "yours": "mine",
    "you": "I",
    "me": "you",
}


def reflect(fragment: str) -> str:
    tokens = re.findall(r"\w+|[^\w\s]", fragment.lower())
    replacements = [REFLECTIONS[t] if t in REFLECTIONS else t for t in tokens]
    return " ".join(replacements)


PATTERNS: List[Tuple[re.Pattern, List[str]]] = [
    (
        re.compile(r"\b(hi|hello|hey)\b", re.I),
        [
            "Hello. How are you feeling today?",
            "Hi there. What would you like to explore?",
        ],
    ),
    (
        re.compile(r"i need (.*)", re.I),
        [
            "Why do you need {X}?",
            "Would it help you to get {X}?",
        ],
    ),
    (
        re.compile(r"i feel (.*)", re.I),
        [
            "Do you often feel {X}?",
            "When did you first begin to feel {X}?",
        ],
    ),
    (
        re.compile(r"why (.*)", re.I),
        [
            "What do you think is the reason {X}?",
            "Why do you ask about {X}?",
        ],
    ),
    (
        re.compile(r"(.*)\?\s*$", re.I),
        [
            "What are your thoughts?",
            "What do you think the answer might be?",
        ],
    ),
]

DEFAULTS = [
    "Tell me more about that.",
    "Please go on.",
    "What comes to mind when you say that?",
]


class ElizaAgent:
    def reply(self, text: str) -> str:
        s = (text or "").strip()
        for pat, outs in PATTERNS:
            m = pat.search(s)
            if m:
                x = m.group(1) if m.groups() else s
                return random.choice(outs).replace("{X}", reflect(x))
        return random.choice(DEFAULTS)
