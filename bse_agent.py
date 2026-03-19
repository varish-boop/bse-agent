import google.generativeai as genai
import requests
import schedule
import time
from datetime import datetime

# YOUR KEYS - FILL THESE IN
GEMINI_API_KEY = "AIzaSyDQ1BI1GYq2OHgM2vyVfiOVRSAAjtAkx0A"
TELEGRAM_TOKEN = "8645635403:AAF6YTi8tgvQsmyoojF7bOZ04cCijYsdB10"
TELEGRAM_CHAT_ID = "7607187136"

# YOUR BSE WATCHLIST - ADD OR REMOVE STOCKS
WATCHLIST = [
    "Reliance Industries",
    "TCS",
    "HDFC Bank",
    "Infosys",
    "SBI"
]

# SETUP GEMINI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def analyze_stock(stock):
    prompt = f"""
    You are an expert BSE Indian stock market analyst.
    Analyze the BSE listed stock: {stock}
    Search and include the latest data available.
    
    Give me a report with exactly this format:
    
    STOCK: {stock}
    SIGNAL: BUY or SELL or HOLD
    CONFIDENCE: XX%
    CURRENT PRICE: ₹XXX
    TARGET PRICE: ₹XXX
    STOP LOSS: ₹XXX
    RSI: XX
    TREND: Bullish or Bearish or Neutral
    FII ACTIVITY: Buying or Selling
    TOP NEWS: One recent news line
    SUMMARY: One line expert opinion
    """
    response = model.generate_content(prompt)
    return response.text

def run_analysis():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"*BSE AI REPORT*\n{now}\nAnalyzing {len(WATCHLIST)} stocks...")
    
    for stock in WATCHLIST:
        try:
            print(f"Analyzing {stock}...")
            report = analyze_stock(stock)
            send_telegram(f"```\n{report}\n```")
            time.sleep(3)
        except Exception as e:
            send_telegram(f"Error analyzing {stock}: {str(e)}")
    
    send_telegram("Analysis complete. Next report tomorrow 8 AM.")

# SCHEDULE DAILY AT 8 AM
schedule.every().day.at("08:00").do(run_analysis)

print("BSE Agent is running. Press CTRL+C to stop.")
send_telegram("BSE Agent started successfully. You will get daily reports at 8 AM.")

while True:
    schedule.run_pending()
    time.sleep(60)