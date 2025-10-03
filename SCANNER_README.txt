MULTI-SYMBOL SCANNER (equities only)
------------------------------------
1) In VS Code terminal (venv active):
   pip install yahooquery

2) Run with auto-movers:
   python multi_scan.py --auto --equity 500 --risk 10

   Optional filters:
   --penny-ceil 1.0 --min-vol-penny 80000 --relvol 1.2

3) Or run with explicit symbols:
   python multi_scan.py --symbols AAPL NVDA QQQ

The script prints a table with entry/stop/target/RSI/ATR/units for each symbol.
