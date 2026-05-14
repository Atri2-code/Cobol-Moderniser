"""
parser/complexity.py

Scores cyclomatic complexity per paragraph:
  complexity = 1 + number of decision points (IF, EVALUATE, PERFORM...UNTIL, etc.)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .structure import CobolProgram, Paragraph

_DECISION_VERBS = {'IF', 'EVALUATE', 'WHEN', 'PERFORM'}
_DECISION_KEYWORDS = {'UNTIL', 'VARYING', 'TIMES', 'AND', 'OR'}


@dataclass
class ComplexityScore:
    paragraph: str
    score: int
    line: int


def score_all(prog: "CobolProgram") -> list[ComplexityScore]:
    scores = []
    for para in prog.paragraphs:
        scores.append(ComplexityScore(
            paragraph=para.name,
            score=_score_paragraph(para),
            line=para.line
        ))
    return sorted(scores, key=lambda s: s.score, reverse=True)


def _score_paragraph(para: "Paragraph") -> int:
    score = 1  # base complexity
    for stmt in para.statements:
        words = set(stmt.text.upper().split())
        if stmt.verb in _DECISION_VERBS:
            score += 1
        score += len(words & _DECISION_KEYWORDS)
    return score
