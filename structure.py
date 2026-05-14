"""
parser/structure.py

Parses a COBOL source file into a structured representation:
  - Divisions (IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE)
  - Sections within DATA division (WORKING-STORAGE, etc.)
  - Data items (level number, name, PIC clause, VALUE)
  - Paragraphs within PROCEDURE division
  - Statements within each paragraph
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class DataItem:
    level: int
    name: str
    pic: Optional[str]
    pic_type: Optional[str]   # '9' or 'X'
    pic_len: Optional[int]
    value: Optional[str]
    line: int


@dataclass
class Statement:
    verb: str          # MOVE, COMPUTE, DISPLAY, PERFORM, IF, GOTO, etc.
    text: str          # full statement text
    line: int


@dataclass
class Paragraph:
    name: str
    statements: list[Statement] = field(default_factory=list)
    line: int = 0


@dataclass
class CobolProgram:
    program_id: str
    data_items: list[DataItem] = field(default_factory=list)
    paragraphs: list[Paragraph] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)


# ─── Helpers ──────────────────────────────────────────────────────────────────

_DIVISIONS = {"IDENTIFICATION", "ENVIRONMENT", "DATA", "PROCEDURE"}
_VERBS = {
    "MOVE", "COMPUTE", "DISPLAY", "PERFORM", "IF", "ELSE", "END-IF",
    "STOP", "GO", "GOTO", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE",
    "EVALUATE", "INSPECT", "STRING", "UNSTRING", "READ", "WRITE",
    "OPEN", "CLOSE", "CALL", "EXIT", "CONTINUE",
}

_PIC_RE  = re.compile(r'PIC\s+([\w()]+)', re.IGNORECASE)
_PIC_TYPED_RE = re.compile(r'([9Xx])\((\d+)\)')
_LEVEL_RE = re.compile(r'^\s{0,7}(\d{2})\s+(\S+)(.*)', re.IGNORECASE)
_PARA_RE  = re.compile(r'^(\s{0,7})([A-Z0-9][A-Z0-9\-]*)\s*\.\s*$', re.IGNORECASE)
_PROG_ID_RE = re.compile(r'PROGRAM-ID\s*\.\s*(\S+?)\.', re.IGNORECASE)


def _strip_sequence_area(line: str) -> str:
    """Remove columns 1-6 (sequence number) and column 7 (indicator) in fixed format."""
    if len(line) >= 7 and line[6] in ('*', '/'):
        return ''  # comment line
    return line[7:] if len(line) > 7 else ''


def _is_division_header(text: str) -> Optional[str]:
    clean = text.strip().upper()
    for d in _DIVISIONS:
        if clean.startswith(d) and 'DIVISION' in clean:
            return d
    return None


def _parse_pic(text: str):
    m = _PIC_RE.search(text)
    if not m:
        return None, None, None
    pic = m.group(1).upper()
    tm = _PIC_TYPED_RE.search(pic)
    if tm:
        return pic, tm.group(1).upper(), int(tm.group(2))
    # single char e.g. PIC 9
    if pic and pic[0] in ('9', 'X'):
        return pic, pic[0], 1
    return pic, None, None


# ─── Main parser ──────────────────────────────────────────────────────────────

def parse(source: str) -> CobolProgram:
    lines = source.splitlines()
    prog  = CobolProgram(program_id="UNKNOWN", raw_lines=lines)

    current_division = None
    current_para: Optional[Paragraph] = None
    stmt_buffer: list[str] = []
    stmt_start_line = 0

    def flush_stmt(line_no: int):
        nonlocal stmt_buffer, stmt_start_line
        if not stmt_buffer or not current_para:
            stmt_buffer = []
            return
        text = ' '.join(stmt_buffer).strip()
        verb = text.split()[0].upper() if text else ''
        current_para.statements.append(Statement(verb=verb, text=text, line=stmt_start_line))
        stmt_buffer = []

    for lineno, raw in enumerate(lines, 1):
        # Detect fixed or free format
        stripped = raw.rstrip()
        # Try fixed format strip; if content is in cols 1-6 range it may be free format
        fixed = _strip_sequence_area(stripped)
        text  = fixed.strip() if fixed else stripped.strip()

        if not text:
            continue

        # Division header
        div = _is_division_header(text)
        if div:
            if current_para and stmt_buffer:
                flush_stmt(lineno)
            current_division = div
            current_para = None
            continue

        # PROGRAM-ID
        pm = _PROG_ID_RE.search(text)
        if pm:
            prog.program_id = pm.group(1).rstrip('.')
            continue

        # DATA DIVISION — data items
        if current_division == 'DATA':
            lm = _LEVEL_RE.match(stripped)
            if lm:
                level = int(lm.group(1))
                name  = lm.group(2).upper()
                rest  = lm.group(3)
                pic, pic_type, pic_len = _parse_pic(rest)
                value_m = re.search(r'VALUE\s+(\S+)', rest, re.IGNORECASE)
                value   = value_m.group(1).rstrip('.') if value_m else None
                prog.data_items.append(DataItem(
                    level=level, name=name, pic=pic, pic_type=pic_type,
                    pic_len=pic_len, value=value, line=lineno
                ))
            continue

        # PROCEDURE DIVISION
        if current_division == 'PROCEDURE':
            # Paragraph name: word ending with '.'  on its own line
            pm2 = _PARA_RE.match(stripped)
            if pm2 and pm2.group(1) == '' or (stripped.endswith('.') and len(text.split()) == 1):
                flush_stmt(lineno)
                current_para = Paragraph(name=text.rstrip('.'), line=lineno)
                prog.paragraphs.append(current_para)
                continue

            # Accumulate statement tokens until '.'
            if text.endswith('.'):
                stmt_buffer.append(text[:-1])
                flush_stmt(lineno)
            else:
                if not stmt_buffer:
                    stmt_start_line = lineno
                stmt_buffer.append(text)

    if current_para and stmt_buffer:
        flush_stmt(len(lines))

    return prog
