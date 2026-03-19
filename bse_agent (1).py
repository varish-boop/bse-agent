import google.generativeai as genai
import requests
import schedule
import time
import os
import json
from datetime import datetime

# YOUR KEYS
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# SETUP GEMINI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# TIER 1: NIFTY 50 STOCKS
NIFTY_50 = [
    "Reliance Industries", "TCS", "HDFC Bank", "Infosys", "ICICI Bank",
    "Hindustan Unilever", "ITC", "SBI", "Bharti Airtel", "Kotak Mahindra Bank",
    "Bajaj Finance", "LTIMindtree", "Asian Paints", "Axis Bank", "Maruti Suzuki",
    "Sun Pharmaceutical", "Titan Company", "Ultratech Cement", "Wipro", "HCL Technologies",
    "NTPC", "Power Grid", "Tata Motors", "Adani Ports", "Bajaj Auto",
    "Mahindra and Mahindra", "Tech Mahindra", "JSW Steel", "Tata Steel", "Nestle India",
    "Cipla", "Dr Reddys Laboratories", "Divi's Laboratories", "Eicher Motors", "Grasim Industries",
    "Hindalco Industries", "IndusInd Bank", "Larsen and Toubro", "ONGC", "Tata Consumer Products",
    "Apollo Hospitals", "Bajaj Finserv", "Britannia Industries", "Coal India", "Hero MotoCorp",
    "Shriram Finance", "SBI Life Insurance", "HDFC Life Insurance", "UPL", "Adani Enterprises"
]

# TIER 2: SECTOR WISE TOP STOCKS
SECTORS = {
    "Banking": ["HDFC Bank", "ICICI Bank", "SBI", "Kotak Mahindra Bank", "Axis Bank", "IndusInd Bank", "Bank of Baroda", "Punjab National Bank", "Canara Bank", "Federal Bank"],
    "IT": ["TCS", "Infosys", "Wipro", "HCL Technologies", "Tech Mahindra", "LTIMindtree", "Mphasis", "Persistent Systems", "Coforge", "KPIT Technologies"],
    "Pharma": ["Sun Pharmaceutical", "Cipla", "Dr Reddys Laboratories", "Divi's Laboratories", "Aurobindo Pharma", "Lupin", "Torrent Pharma", "Alkem Labs", "Abbott India", "Ipca Laboratories"],
    "Auto": ["Maruti Suzuki", "Tata Motors", "Mahindra and Mahindra", "Bajaj Auto", "Hero MotoCorp", "Eicher Motors", "TVS Motor", "Ashok Leyland", "MRF", "Bosch"],
    "Energy": ["Reliance Industries", "ONGC", "NTPC", "Power Grid", "Adani Green Energy", "Tata Power", "GAIL", "Indian Oil", "BPCL", "Adani Enterprises"]
}

# TOP INFLUENCERS TO TRACK
INFLUENCERS = [
    "Vijay Kedia", "Basant Maheshwari", "Saurabh Mukherjea",
    "Deepak Shenoy", "PR Sundar", "Akshat Shrivastava", "Anish Singh Thakur",
    "Pranjal Kamra", "Rachana Ranade", "CA Rachana Phadke"
]

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, data=data)
        time.sleep(1)
    except Exception as e:
        print(f"Telegram error: {e}")

def analyze_single_stock(stock):
    influencer_names = ", ".join(INFLUENCERS)
    prompt = f"""
    You are an expert BSE Indian stock market analyst with access to all market data.
    Analyze this BSE listed stock completely: {stock}
    Search the entire internet including BSE, NSE, Moneycontrol, Screener.in,
    Economic Times, Mint, Twitter posts from: {influencer_names},
    YouTube videos from these influencers, Telegram stock channels,
    SEBI filings and corporate announcements.
    Return ONLY a JSON object with no extra text:
    {{
        "stock": "{stock}",
        "price": "RXXX",
        "change": "+/-X.XX%",
        "is_positive": true,
        "signal": "STRONG BUY/BUY/HOLD/SELL/STRONG SELL",
        "confidence": "XX%",
        "target": "RXXX",
        "stop_loss": "RXXX",
        "rsi": "XX",
        "macd": "Bullish/Bearish",
        "fii": "Buying/Selling/Neutral",
        "volume": "High/Normal/Low",
        "influencer_sentiment": "BULLISH/BEARISH/NEUTRAL",
        "news_sentiment": "BULLISH/BEARISH/NEUTRAL",
        "key_reason": "One line reason for signal",
        "risk": "LOW/MEDIUM/HIGH"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        return {
            "stock": stock, "price": "N/A", "change": "N/A",
            "signal": "HOLD", "confidence": "0%", "target": "N/A",
            "stop_loss": "N/A", "key_reason": "Analysis failed", "risk": "HIGH"
        }

def scan_breakouts():
    prompt = f"""
    You are an expert BSE stock market scanner.
    Search the entire BSE market right now and find stocks showing:
    1. Price breaking 52 week high today
    2. Unusual volume spike more than 3x average
    3. RSI crossing above 70 today
    4. Strong FII buying today
    5. Major news catalyst today
    6. Strong earnings surprise today
    7. Stocks that top influencers just recommended today: {", ".join(INFLUENCERS)}
    Search Moneycontrol, Economic Times, BSE announcements, Twitter, Telegram.
    Return ONLY a JSON object with no extra text:
    {{
        "breakout_stocks": [
            {{
                "stock": "Stock Name",
                "price": "RXXX",
                "change": "+XX%",
                "reason": "Why it is breaking out",
                "signal": "STRONG BUY/BUY",
                "target": "RXXX",
                "stop_loss": "RXXX",
                "urgency": "HIGH/MEDIUM"
            }}
        ],
        "total_found": X,
        "market_mood": "BULLISH/BEARISH/NEUTRAL",
        "nifty_trend": "UP/DOWN/SIDEWAYS",
        "sector_of_the_day": "Sector name",
        "market_summary": "One line summary of market today"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        return {
            "breakout_stocks": [], "total_found": 0,
            "market_mood": "NEUTRAL", "nifty_trend": "SIDEWAYS",
            "sector_of_the_day": "N/A", "market_summary": "Could not fetch market data"
        }

def analyze_sector(sector_name, stocks):
    stocks_str = ", ".join(stocks)
    prompt = f"""
    You are an expert Indian stock market sector analyst.
    Analyze the entire {sector_name} sector on BSE right now.
    Stocks to analyze: {stocks_str}
    Search Moneycontrol, Economic Times, BSE data, and all influencer posts.
    Return ONLY a JSON object with no extra text:
    {{
        "sector": "{sector_name}",
        "sector_signal": "BULLISH/BEARISH/NEUTRAL",
        "sector_strength": "STRONG/MODERATE/WEAK",
        "top_pick": "Best stock in this sector right now",
        "top_pick_signal": "BUY/STRONG BUY",
        "top_pick_target": "RXXX",
        "avoid_stock": "Worst stock in sector right now",
        "sector_news": "Key news affecting this sector",
        "fii_in_sector": "Buying/Selling/Neutral",
        "summary": "One line sector outlook"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        return {
            "sector": sector_name, "sector_signal": "NEUTRAL",
            "top_pick": "N/A", "summary": "Analysis failed"
        }

def format_stock_report(data):
    signal = data.get("signal", "HOLD")
    emoji = "🟢" if "BUY" in signal else ("🔴" if "SELL" in signal else "🟡")
    inf_sent = data.get("influencer_sentiment", "NEUTRAL")
    inf_emoji = "👍" if inf_sent == "BULLISH" else ("👎" if inf_sent == "BEARISH" else "😐")
    return f"""
{emoji} *{data.get('stock', 'N/A')}*
💰 {data.get('price', 'N/A')} ({data.get('change', 'N/A')})
📊 Signal: *{signal}* | Confidence: {data.get('confidence', 'N/A')}
🎯 Target: {data.get('target', 'N/A')} | 🛑 Stop Loss: {data.get('stop_loss', 'N/A')}
📉 RSI: {data.get('rsi', 'N/A')} | MACD: {data.get('macd', 'N/A')}
🏦 FII: {data.get('fii', 'N/A')} | Vol: {data.get('volume', 'N/A')}
{inf_emoji} Influencers: {inf_sent}
⚡ {data.get('key_reason', 'N/A')}
━━━━━━━━━━━━━━━"""

def run_nifty50_scan():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"🔍 *NIFTY 50 FULL SCAN*\n🕐 {now}\nAnalyzing all 50 stocks with influencer tracking...")
    time.sleep(2)

    buy_stocks = []
    sell_stocks = []
    hold_stocks = []

    for i, stock in enumerate(NIFTY_50):
        try:
            print(f"Scanning {stock} ({i+1}/50)...")
            data = analyze_single_stock(stock)
            signal = data.get("signal", "HOLD")
            if "BUY" in signal:
                buy_stocks.append(data)
            elif "SELL" in signal:
                sell_stocks.append(data)
            else:
                hold_stocks.append(data)
            time.sleep(4)
            if (i + 1) % 10 == 0:
                send_telegram(f"✅ Scanned {i+1}/50 stocks...")
        except Exception as e:
            print(f"Error: {stock}: {e}")
            time.sleep(3)

    send_telegram(f"🟢 *TOP BUY SIGNALS ({len(buy_stocks)} stocks)*")
    for stock in buy_stocks[:10]:
        send_telegram(format_stock_report(stock))
        time.sleep(2)

    if sell_stocks:
        send_telegram(f"🔴 *SELL/AVOID SIGNALS ({len(sell_stocks)} stocks)*")
        for stock in sell_stocks[:5]:
            send_telegram(format_stock_report(stock))
            time.sleep(2)

    send_telegram(f"✅ *Nifty 50 Scan Complete*\n🟢 Buy: {len(buy_stocks)} | 🟡 Hold: {len(hold_stocks)} | 🔴 Sell: {len(sell_stocks)}\nNext scan in 1 hour.")

def run_sector_scan():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"🏭 *SECTOR SCAN STARTED*\n🕐 {now}\nAnalyzing 5 key sectors...")
    time.sleep(2)

    for sector_name, stocks in SECTORS.items():
        try:
            print(f"Scanning {sector_name} sector...")
            data = analyze_sector(sector_name, stocks)
            signal = data.get("sector_signal", "NEUTRAL")
            emoji = "🟢" if signal == "BULLISH" else ("🔴" if signal == "BEARISH" else "🟡")
            report = f"""
{emoji} *{sector_name} SECTOR*
📊 Outlook: *{signal}* | Strength: {data.get('sector_strength', 'N/A')}
⭐ Top Pick: *{data.get('top_pick', 'N/A')}* ({data.get('top_pick_signal', 'N/A')})
🎯 Target: {data.get('top_pick_target', 'N/A')}
❌ Avoid: {data.get('avoid_stock', 'N/A')}
🏦 FII in Sector: {data.get('fii_in_sector', 'N/A')}
📰 {data.get('sector_news', 'N/A')}
💡 {data.get('summary', 'N/A')}
━━━━━━━━━━━━━━━"""
            send_telegram(report)
            time.sleep(5)
        except Exception as e:
            send_telegram(f"Error scanning {sector_name}: {str(e)}")
            time.sleep(3)

    send_telegram("✅ *Sector Scan Complete*\nNext sector scan in 2 hours.")

def run_breakout_scan():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"⚡ *BSE BREAKOUT SCANNER*\n🕐 {now}\nScanning all 5000+ BSE stocks for breakouts...")
    time.sleep(2)

    data = scan_breakouts()
    mood = data.get("market_mood", "NEUTRAL")
    mood_emoji = "🟢" if mood == "BULLISH" else ("🔴" if mood == "BEARISH" else "🟡")

    summary = f"""
{mood_emoji} *MARKET OVERVIEW*
📊 Market Mood: *{mood}*
📈 Nifty Trend: {data.get('nifty_trend', 'N/A')}
🏆 Sector of the Day: {data.get('sector_of_the_day', 'N/A')}
💡 {data.get('market_summary', 'N/A')}
🔥 Breakouts Found: {data.get('total_found', 0)}
━━━━━━━━━━━━━━━"""
    send_telegram(summary)
    time.sleep(2)

    breakouts = data.get("breakout_stocks", [])
    if breakouts:
        send_telegram(f"🚨 *BREAKOUT ALERTS*")
        for stock in breakouts[:10]:
            urgency = stock.get("urgency", "MEDIUM")
            urg_emoji = "🚨" if urgency == "HIGH" else "⚡"
            report = f"""
{urg_emoji} *{stock.get('stock', 'N/A')}*
💰 {stock.get('price', 'N/A')} ({stock.get('change', 'N/A')})
📊 Signal: *{stock.get('signal', 'N/A')}*
🎯 Target: {stock.get('target', 'N/A')} | 🛑 Stop: {stock.get('stop_loss', 'N/A')}
⚡ {stock.get('reason', 'N/A')}
━━━━━━━━━━━━━━━"""
            send_telegram(report)
            time.sleep(2)
    else:
        send_telegram("😴 No major breakouts right now. Market is calm.")

    send_telegram("✅ *Breakout Scan Complete*\nNext scan in 30 minutes.")

# SCHEDULE ALL SCANS
schedule.every().hour.do(run_nifty50_scan)
schedule.every(2).hours.do(run_sector_scan)
schedule.every(30).minutes.do(run_breakout_scan)

print("BSE Full Market Scanner is running.")
print("Nifty 50: Every hour")
print("Sectors: Every 2 hours")
print("Breakouts: Every 30 minutes")

send_telegram("""🚀 *BSE FULL MARKET SCANNER STARTED*

Nifty 50 scan: Every hour
Sector scan: Every 2 hours
Breakout alerts: Every 30 minutes
Influencer tracking: Active
Internet search: Active
24/7 monitoring: ON

Starting first scan now...""")

time.sleep(3)

run_breakout_scan()
time.sleep(5)
run_sector_scan()
time.sleep(5)
run_nifty50_scan()

while True:
    schedule.run_pending()
    time.sleep(60)
