"""tests/test_parser.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parser.structure    import parse
from parser.antipatterns import detect
from parser.complexity   import score_all

SIMPLE_SRC = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SIMPLE.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-A PIC 9(4) VALUE 0.
       01 WS-B PIC 9(4) VALUE 0.
       01 WS-C PIC 9(8) VALUE 0.
       PROCEDURE DIVISION.
       MAIN.
           MOVE 10 TO WS-A
           MOVE 20 TO WS-B
           COMPUTE WS-C = WS-A + WS-B
           DISPLAY WS-C
           STOP RUN.
"""

GOTO_SRC = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. GOTOTEST.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-X PIC 9(4) VALUE 0.
       PROCEDURE DIVISION.
       MAIN.
           MOVE 1 TO WS-X
           GO TO END-PARA
           DISPLAY WS-X
           STOP RUN.
       END-PARA.
           STOP RUN.
"""

def test_program_id():
    prog = parse(SIMPLE_SRC)
    assert prog.program_id == 'SIMPLE', f"Expected 'SIMPLE', got '{prog.program_id}'"
    print("PASS: test_program_id")

def test_data_items():
    prog = parse(SIMPLE_SRC)
    assert len(prog.data_items) == 3, f"Expected 3 data items, got {len(prog.data_items)}"
    names = [d.name for d in prog.data_items]
    assert 'WS-A' in names and 'WS-C' in names
    print("PASS: test_data_items")

def test_pic_parsing():
    prog = parse(SIMPLE_SRC)
    ws_a = next(d for d in prog.data_items if d.name == 'WS-A')
    assert ws_a.pic_type == '9', f"Expected '9', got '{ws_a.pic_type}'"
    assert ws_a.pic_len  == 4,  f"Expected 4, got {ws_a.pic_len}"
    print("PASS: test_pic_parsing")

def test_paragraphs():
    prog = parse(SIMPLE_SRC)
    assert len(prog.paragraphs) >= 1
    print("PASS: test_paragraphs")

def test_no_antipatterns_in_clean_code():
    prog     = parse(SIMPLE_SRC)
    findings = detect(prog)
    serious  = [f for f in findings if f.category in ('GOTO', 'ALTER')]
    assert len(serious) == 0, f"Unexpected findings: {serious}"
    print("PASS: test_no_antipatterns_in_clean_code")

def test_goto_detected():
    prog     = parse(GOTO_SRC)
    findings = detect(prog)
    gotos    = [f for f in findings if f.category == 'GOTO']
    assert len(gotos) >= 1, "GOTO not detected"
    print("PASS: test_goto_detected")

def test_unreferenced_data():
    src = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. UNREF.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-USED   PIC 9(4) VALUE 0.
       01 WS-UNUSED PIC 9(4) VALUE 0.
       PROCEDURE DIVISION.
       MAIN.
           DISPLAY WS-USED
           STOP RUN.
"""
    prog     = parse(src)
    findings = detect(prog)
    unref    = [f for f in findings if f.category == 'UNREFERENCED_DATA']
    assert len(unref) >= 1, "Unreferenced data not detected"
    assert any('WS-UNUSED' in f.description for f in unref)
    print("PASS: test_unreferenced_data")

def test_complexity_ordering():
    prog   = parse(SIMPLE_SRC)
    scores = score_all(prog)
    assert len(scores) == len(prog.paragraphs)
    # Scores should be in descending order
    for i in range(len(scores) - 1):
        assert scores[i].score >= scores[i+1].score
    print("PASS: test_complexity_ordering")

def test_payroll_sample():
    path = os.path.join(os.path.dirname(__file__), 'samples', 'payroll.cbl')
    with open(path) as f:
        source = f.read()
    prog     = parse(source)
    findings = detect(prog)
    scores   = score_all(prog)
    assert prog.program_id == 'PAYROLL'
    assert len(prog.data_items) >= 5
    assert len(prog.paragraphs) >= 3
    magic = [f for f in findings if f.category == 'MAGIC_LITERAL']
    assert len(magic) >= 1, "Should detect magic literals in payroll"
    print("PASS: test_payroll_sample")

if __name__ == '__main__':
    tests = [
        test_program_id,
        test_data_items,
        test_pic_parsing,
        test_paragraphs,
        test_no_antipatterns_in_clean_code,
        test_goto_detected,
        test_unreferenced_data,
        test_complexity_ordering,
        test_payroll_sample,
    ]
    passed = failed = 0
    print("=== COBOL Moderniser Tests ===\n")
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
