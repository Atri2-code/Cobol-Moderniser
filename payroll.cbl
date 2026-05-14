       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYROLL.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-HOURS       PIC 9(3)  VALUE 0.
       01 WS-RATE        PIC 9(5)  VALUE 0.
       01 WS-GROSS       PIC 9(8)  VALUE 0.
       01 WS-TAX         PIC 9(8)  VALUE 0.
       01 WS-NET-PAY     PIC 9(8)  VALUE 0.
       01 WS-OVERTIME    PIC 9(5)  VALUE 0.
       01 WS-UNUSED      PIC 9(4)  VALUE 0.

       PROCEDURE DIVISION.

       MAIN-PARA.
           PERFORM CALC-GROSS
           PERFORM CALC-TAX
           PERFORM CALC-NET
           DISPLAY WS-NET-PAY
           STOP RUN.

       CALC-GROSS.
           MOVE 40    TO WS-HOURS
           MOVE 25000 TO WS-RATE
           IF WS-HOURS > 40
               COMPUTE WS-OVERTIME = (WS-HOURS - 40) * WS-RATE * 1500
               COMPUTE WS-GROSS = WS-HOURS * WS-RATE + WS-OVERTIME
           ELSE
               COMPUTE WS-GROSS = WS-HOURS * WS-RATE
           END-IF.

       CALC-TAX.
           IF WS-GROSS > 500000
               COMPUTE WS-TAX = WS-GROSS * 30 / 100
           ELSE
               IF WS-GROSS > 200000
                   COMPUTE WS-TAX = WS-GROSS * 20 / 100
               ELSE
                   COMPUTE WS-TAX = WS-GROSS * 10 / 100
               END-IF
           END-IF.

       CALC-NET.
           COMPUTE WS-NET-PAY = WS-GROSS - WS-TAX.
