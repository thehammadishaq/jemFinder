import yfinance as yf

# Choose your ticker
ticker = "AAPL"
stock = yf.Ticker(ticker)

# Analyst recommendations (historical table)
recommendations = stock.recommendations
print("=== Analyst Recommendations ===")
print(recommendations)

# Recommendation summary (newer yfinance attribute)
rec_summary = stock.recommendations_summary
print("\n=== Recommendation Summary ===")
print(rec_summary)
