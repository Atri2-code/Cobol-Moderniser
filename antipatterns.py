"""
parser/antipatterns.py

Detects common COBOL anti-patterns that complicate modernisation:
  - GOTO / GO TO usage
  - ALTER statements
  - Hardcoded literals in PROCEDURE DIVISION
  - Unreferenced data items
  - Deeply nested IF blocks
  - Missing STOP RUN
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .structure import CobolProgram


@dataclass
class Finding:
    category: str
    severity: str        # 'HIGH', 'MEDIUM', 'LOW'
    description: str
    line: int
    snippet: str = ''


def detect(prog: "CobolProgram") -> list[Finding]:
    findings: list[Finding] = []

    data_names = {d.name for d in prog.data_items}
    referenced_names: set[str] = set()

    for para in prog.paragraphs:
        for stmt in para.statements:
            text_upper = stmt.text.upper()
            words = stmt.text.split()

            # ── GOTO ──────────────────────────────────────────────────────────
            if stmt.verb in ('GO', 'GOTO') or 'GO TO' in text_upper:
                findings.append(Finding(
                    category='GOTO',
                    severity='HIGH',
                    description=f"GOTO statement found in paragraph '{para.name}' — "
                                f"hinders structured refactoring",
                    line=stmt.line,
                    snippet=stmt.text[:80]
                ))

            # ── ALTER ─────────────────────────────────────────────────────────
            if stmt.verb == 'ALTER':
                findings.append(Finding(
                    category='ALTER',
                    severity='HIGH',
                    description="ALTER statement modifies GOTO targets at runtime — "
                                "makes control flow analysis impossible",
                    line=stmt.line,
                    snippet=stmt.text[:80]
                ))

            # ── Hardcoded literals in MOVE / COMPUTE ──────────────────────────
            if stmt.verb in ('MOVE', 'COMPUTE', 'ADD', 'SUBTRACT'):
                literals = re.findall(r'\b\d{3,}\b', stmt.text)
                for lit in literals:
                    findings.append(Finding(
                        category='MAGIC_LITERAL',
                        severity='MEDIUM',
                        description=f"Hardcoded numeric literal '{lit}' in {stmt.verb} statement "
                                    f"— consider moving to a named constant in WORKING-STORAGE",
                        line=stmt.line,
                        snippet=stmt.text[:80]
                    ))

            # ── Nested IF depth ───────────────────────────────────────────────
            if stmt.verb == 'IF':
                depth = _count_if_depth(stmt.text)
                if depth > 3:
                    findings.append(Finding(
                        category='DEEP_NESTING',
                        severity='MEDIUM',
                        description=f"IF nesting depth {depth} in paragraph '{para.name}' "
                                    f"— consider extracting into sub-paragraphs",
                        line=stmt.line,
                        snippet=stmt.text[:80]
                    ))

            # Track referenced data names
            for word in words:
                clean = word.strip('.,()').upper()
                if clean in data_names:
                    referenced_names.add(clean)

    # ── Unreferenced data items ────────────────────────────────────────────────
    for item in prog.data_items:
        if item.level == 1 and item.name not in referenced_names:
            findings.append(Finding(
                category='UNREFERENCED_DATA',
                severity='LOW',
                description=f"Data item '{item.name}' (level 01) is declared but never "
                            f"referenced in PROCEDURE DIVISION",
                line=item.line,
                snippet=f"01 {item.name} PIC {item.pic or '?'}"
            ))

    # ── Missing STOP RUN ──────────────────────────────────────────────────────
    has_stop = any(
        stmt.verb == 'STOP'
        for para in prog.paragraphs
        for stmt in para.statements
    )
    if not has_stop:
        findings.append(Finding(
            category='MISSING_STOP_RUN',
            severity='HIGH',
            description="No STOP RUN found — program may fall through unexpectedly",
            line=0,
            snippet=''
        ))

    return findings


def _count_if_depth(text: str) -> int:
    """Rough count of IF nesting depth in a statement block."""
    depth = max_depth = 0
    for word in text.upper().split():
        if word == 'IF':
            depth += 1
            max_depth = max(max_depth, depth)
        elif word in ('END-IF', 'ENDIF'):
            depth = max(0, depth - 1)
    return max_depth
