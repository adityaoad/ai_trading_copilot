import yfinance as yf

df = yf.download("AAPL", period="5d", interval="1d", auto_adjust=True)
print(df)
