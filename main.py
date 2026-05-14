#!/usr/bin/env python3
"""
cobol-moderniser — main entry point

Usage:
    python main.py --input samples/payroll.cbl
    python main.py --input samples/payroll.cbl --report output/report.md
    python main.py --input samples/payroll.cbl --ast
    python main.py --input samples/payroll.cbl --annotate
"""

import argparse
import os
import sys

from parser.structure   import parse
from parser.antipatterns import detect
from parser.complexity  import score_all
from reporter.markdown  import render


def main():
    parser = argparse.ArgumentParser(
        description="COBOL Moderniser — static analysis and annotation tool"
    )
    parser.add_argument("--input",    required=True, help="Path to .cbl source file")
    parser.add_argument("--report",   default=None,  help="Output path for Markdown report")
    parser.add_argument("--ast",      action="store_true", help="Print parsed structure to stdout")
    parser.add_argument("--annotate", action="store_true", help="Generate LLM paragraph annotations")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, 'r', encoding='utf-8', errors='replace') as f:
        source = f.read()

    # ── Parse ────────────────────────────────────────────────────────────────
    prog = parse(source)

    if args.ast:
        print(f"Program ID : {prog.program_id}")
        print(f"Data items : {len(prog.data_items)}")
        for d in prog.data_items:
            print(f"  {d.level:02d} {d.name:<30} PIC {d.pic or '-':<12} VALUE {d.value or '-'}")
        print(f"Paragraphs : {len(prog.paragraphs)}")
        for p in prog.paragraphs:
            print(f"  {p.name} ({len(p.statements)} stmts, line {p.line})")
            for s in p.statements:
                print(f"    [{s.verb}] {s.text[:60]}")

    # ── Anti-pattern detection ────────────────────────────────────────────────
    findings = detect(prog)

    # ── Complexity scoring ────────────────────────────────────────────────────
    scores = score_all(prog)

    # ── Console summary ───────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  COBOL Moderniser — {os.path.basename(args.input)}")
    print(f"{'='*60}")
    print(f"  Program ID  : {prog.program_id}")
    print(f"  Lines       : {len(prog.raw_lines)}")
    print(f"  Data items  : {len(prog.data_items)}")
    print(f"  Paragraphs  : {len(prog.paragraphs)}")
    print()

    high = sum(1 for f in findings if f.severity == 'HIGH')
    med  = sum(1 for f in findings if f.severity == 'MEDIUM')
    low  = sum(1 for f in findings if f.severity == 'LOW')
    print(f"  Findings: 🔴 {high} HIGH  🟡 {med} MEDIUM  🟢 {low} LOW")
    print()

    for finding in findings:
        sym = {'HIGH': '🔴', 'MEDIUM': '🟡', 'LOW': '🟢'}.get(finding.severity, '')
        print(f"  {sym}  [{finding.category}] line {finding.line}: {finding.description[:70]}")

    print()
    print(f"  Top 3 most complex paragraphs:")
    for s in scores[:3]:
        print(f"    {s.paragraph:<30} complexity: {s.score}")
    print(f"{'='*60}\n")

    # ── Annotations (optional) ────────────────────────────────────────────────
    annotations = {}
    if args.annotate:
        annotations = _generate_annotations(prog)

    # ── Report ────────────────────────────────────────────────────────────────
    report_path = args.report or args.input.replace('.cbl', '_report.md')
    os.makedirs(os.path.dirname(report_path) if os.path.dirname(report_path) else '.', exist_ok=True)
    report_text = render(prog, findings, scores, args.input, annotations)
    with open(report_path, 'w') as f:
        f.write(report_text)
    print(f"  Report written to: {report_path}\n")


def _generate_annotations(prog) -> dict[str, str]:
    """
    Generate plain-English summaries for each paragraph.
    Uses a simple rule-based approach; swap in an LLM call for richer output.
    """
    annotations = {}
    verb_descriptions = {
        'MOVE':     'moves data between variables',
        'COMPUTE':  'performs arithmetic computation',
        'DISPLAY':  'outputs data to the screen',
        'PERFORM':  'calls another paragraph',
        'IF':       'makes a conditional decision',
        'ADD':      'adds values',
        'SUBTRACT': 'subtracts values',
        'MULTIPLY': 'multiplies values',
        'DIVIDE':   'divides values',
        'STOP':     'terminates the program',
    }

    for para in prog.paragraphs:
        if not para.statements:
            continue
        verbs = [s.verb for s in para.statements]
        verb_counts: dict[str, int] = {}
        for v in verbs:
            verb_counts[v] = verb_counts.get(v, 0) + 1

        parts = []
        for verb, count in sorted(verb_counts.items(), key=lambda x: -x[1]):
            desc = verb_descriptions.get(verb, f'executes {verb}')
            parts.append(f"{desc} ({count}×)")

        summary = (
            f"Paragraph `{para.name}` contains {len(para.statements)} statement(s). "
            f"Primary operations: {', '.join(parts[:3])}."
        )
        annotations[para.name] = summary

    return annotations


if __name__ == '__main__':
    main()
