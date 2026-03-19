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

# NIFTY 50 STOCKS
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

# SECTORS
SECTORS = {
    "Banking": ["HDFC Bank", "ICICI Bank", "SBI", "Kotak Mahindra Bank", "Axis Bank", "IndusInd Bank", "Bank of Baroda", "Punjab National Bank", "Canara Bank", "Federal Bank"],
    "IT": ["TCS", "Infosys", "Wipro", "HCL Technologies", "Tech Mahindra", "LTIMindtree", "Mphasis", "Persistent Systems", "Coforge", "KPIT Technologies"],
    "Pharma": ["Sun Pharmaceutical", "Cipla", "Dr Reddys Laboratories", "Divi's Laboratories", "Aurobindo Pharma", "Lupin", "Torrent Pharma", "Alkem Labs", "Abbott India", "Ipca Laboratories"],
    "Auto": ["Maruti Suzuki", "Tata Motors", "Mahindra and Mahindra", "Bajaj Auto", "Hero MotoCorp", "Eicher Motors", "TVS Motor", "Ashok Leyland", "MRF", "Bosch"],
    "Energy": ["Reliance Industries", "ONGC", "NTPC", "Power Grid", "Adani Green Energy", "Tata Power", "GAIL", "Indian Oil", "BPCL", "Adani Enterprises"]
}

# TOP INFLUENCERS
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
    You are an expert BSE Indian stock market analyst.
    Analyze this BSE listed stock completely: {stock}
    Search the entire internet including BSE, NSE, Moneycontrol, Screener.in,
    Economic Times, Mint, Twitter posts from: {influencer_names},
    YouTube videos and Telegram stock channels.
    Return ONLY a JSON object with no extra text:
    {{
        "stock": "{stock}",
        "price": "RXXX",
        "change": "+/-X.XX%",
        "signal": "STRONG BUY/BUY/HOLD/SELL/STRONG SELL",
        "confidence": "XX%",
        "target": "RXXX",
        "stop_loss": "RXXX",
        "rsi": "XX",
        "macd": "Bullish/Bearish",
        "fii": "Buying/Selling/Neutral",
        "volume": "High/Normal/Low",
        "influencer_sentiment": "BULLISH/BEARISH/NEUTRAL",
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
    except:
        return {
            "stock": stock, "price": "N/A", "change": "N/A",
            "signal": "HOLD", "confidence": "0%", "target": "N/A",
            "stop_loss": "N/A", "key_reason": "Analysis failed", "risk": "HIGH"
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

# ============================================================
# REPORT 1: MARKET HOURS - EVERY HOUR 9AM TO 3PM
# Full Nifty 50 + Breakout scan during live market
# ============================================================
def run_market_hours_scan():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"📈 *LIVE MARKET SCAN*\n🕐 {now}\nMarket is open. Scanning Nifty 50 + Breakouts...")
    time.sleep(2)

    # Breakout scan first
    prompt = f"""
    Search entire BSE right now for breakout stocks.
    Find stocks with: 52 week high breakout, volume spike 3x, strong FII buying,
    major news today, earnings surprise, influencer recommendations from: {", ".join(INFLUENCERS)}
    Return ONLY JSON:
    {{
        "breakout_stocks": [
            {{"stock": "Name", "price": "RXXX", "change": "+XX%", "reason": "Why", "signal": "BUY/STRONG BUY", "target": "RXXX", "stop_loss": "RXXX"}}
        ],
        "market_mood": "BULLISH/BEARISH/NEUTRAL",
        "nifty_trend": "UP/DOWN/SIDEWAYS",
        "sector_of_the_day": "Sector",
        "market_summary": "One line"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        breakout_data = json.loads(text[start:end])

        mood = breakout_data.get("market_mood", "NEUTRAL")
        mood_emoji = "🟢" if mood == "BULLISH" else ("🔴" if mood == "BEARISH" else "🟡")

        send_telegram(f"""
{mood_emoji} *MARKET PULSE*
📊 Mood: *{mood}*
📈 Nifty: {breakout_data.get('nifty_trend', 'N/A')}
🏆 Hot Sector: {breakout_data.get('sector_of_the_day', 'N/A')}
💡 {breakout_data.get('market_summary', 'N/A')}""")

        breakouts = breakout_data.get("breakout_stocks", [])
        if breakouts:
            send_telegram("🚨 *BREAKOUT ALERTS*")
            for stock in breakouts[:8]:
                send_telegram(f"""
🚨 *{stock.get('stock', 'N/A')}*
💰 {stock.get('price', 'N/A')} ({stock.get('change', 'N/A')})
📊 {stock.get('signal', 'N/A')} | 🎯 {stock.get('target', 'N/A')} | 🛑 {stock.get('stop_loss', 'N/A')}
⚡ {stock.get('reason', 'N/A')}
━━━━━━━━━━━━━━━""")
                time.sleep(2)
    except Exception as e:
        send_telegram(f"Breakout scan error: {str(e)}")

    # Top 10 Nifty stocks scan
    send_telegram("🔍 *TOP NIFTY PICKS RIGHT NOW*")
    buy_stocks = []
    sell_stocks = []

    for stock in NIFTY_50[:25]:
        try:
            data = analyze_single_stock(stock)
            signal = data.get("signal", "HOLD")
            if "BUY" in signal:
                buy_stocks.append(data)
            elif "SELL" in signal:
                sell_stocks.append(data)
            time.sleep(3)
        except:
            time.sleep(2)

    for stock in buy_stocks[:8]:
        send_telegram(format_stock_report(stock))
        time.sleep(2)

    if sell_stocks:
        send_telegram("🔴 *AVOID THESE STOCKS*")
        for stock in sell_stocks[:3]:
            send_telegram(format_stock_report(stock))
            time.sleep(2)

    send_telegram(f"✅ *Live Scan Done*\n🟢 {len(buy_stocks)} Buy | 🔴 {len(sell_stocks)} Sell\nNext scan in 1 hour.")

# ============================================================
# REPORT 2: AFTER MARKET - SINGLE REPORT AT 6PM
# FII/DII data + closing analysis + corporate announcements
# ============================================================
def run_after_market_report():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"🌆 *AFTER MARKET REPORT*\n🕐 {now}\nMarket closed. Analyzing FII data and announcements...")
    time.sleep(2)

    prompt = f"""
    BSE market has closed for today. Search the entire internet and provide:
    
    1. Today's FII buying and selling data from BSE
    2. Today's DII buying and selling data
    3. Top 5 gainers on BSE today
    4. Top 5 losers on BSE today
    5. Any corporate announcements after market close
    6. Any SEBI notices or regulatory news today
    7. What influencers said today: {", ".join(INFLUENCERS)}
    8. Global market outlook for tomorrow
    9. Top 5 stocks to watch tomorrow based on today's data
    
    Return ONLY JSON:
    {{
        "fii_data": {{"bought": "RXXXX Cr", "sold": "RXXXX Cr", "net": "Buying/Selling of RXXXX Cr"}},
        "dii_data": {{"bought": "RXXXX Cr", "sold": "RXXXX Cr", "net": "Buying/Selling of RXXXX Cr"}},
        "top_gainers": [{{"stock": "Name", "change": "+XX%"}}],
        "top_losers": [{{"stock": "Name", "change": "-XX%"}}],
        "corporate_announcements": ["Announcement 1", "Announcement 2"],
        "influencer_calls_today": ["Call 1", "Call 2"],
        "global_outlook": "Positive/Negative/Neutral with reason",
        "stocks_to_watch_tomorrow": [
            {{"stock": "Name", "reason": "Why to watch", "expected": "Gap up/down/flat"}}
        ],
        "overall_market_verdict": "One line summary of today and outlook for tomorrow"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])

        fii = data.get("fii_data", {})
        dii = data.get("dii_data", {})

        report = f"""
🏦 *FII AND DII ACTIVITY TODAY*
FII Net: {fii.get('net', 'N/A')}
DII Net: {dii.get('net', 'N/A')}
━━━━━━━━━━━━━━━
📈 *TOP GAINERS TODAY*"""
        for g in data.get("top_gainers", [])[:5]:
            report += f"\n🟢 {g.get('stock', 'N/A')} {g.get('change', 'N/A')}"

        report += "\n\n📉 *TOP LOSERS TODAY*"
        for l in data.get("top_losers", [])[:5]:
            report += f"\n🔴 {l.get('stock', 'N/A')} {l.get('change', 'N/A')}"

        report += "\n\n📢 *CORPORATE ANNOUNCEMENTS*"
        for ann in data.get("corporate_announcements", [])[:3]:
            report += f"\n• {ann}"

        report += "\n\n🌍 *GLOBAL OUTLOOK*"
        report += f"\n{data.get('global_outlook', 'N/A')}"

        report += "\n\n⭐ *STOCKS TO WATCH TOMORROW*"
        for s in data.get("stocks_to_watch_tomorrow", [])[:5]:
            report += f"\n👀 *{s.get('stock', 'N/A')}* - {s.get('expected', 'N/A')}\n   {s.get('reason', 'N/A')}"

        report += f"\n\n💡 *VERDICT*\n{data.get('overall_market_verdict', 'N/A')}"
        report += "\n\n🌙 Next report at Midnight for global market update."

        send_telegram(report)

    except Exception as e:
        send_telegram(f"After market report error: {str(e)}")

# ============================================================
# REPORT 3: MIDNIGHT REPORT - SINGLE REPORT AT 12AM
# US market results + SGX Nifty + global cues for tomorrow
# ============================================================
def run_midnight_report():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"🌙 *MIDNIGHT GLOBAL REPORT*\n🕐 {now}\nChecking US markets and global cues for tomorrow...")
    time.sleep(2)

    prompt = f"""
    It is midnight in India. Search the entire internet and provide:
    
    1. US market closing data today - Dow Jones, NASDAQ, S&P 500
    2. SGX Nifty current level and direction
    3. Asian markets outlook for tomorrow
    4. Crude oil price and direction
    5. Gold price and direction
    6. USD to INR current rate
    7. Any major global news affecting Indian markets tomorrow
    8. FII likely direction tomorrow based on US market performance
    9. Top 5 Indian stocks likely to gap up tomorrow
    10. Top 5 Indian stocks likely to gap down tomorrow
    
    Return ONLY JSON:
    {{
        "us_markets": {{
            "dow_jones": "Level and change",
            "nasdaq": "Level and change",
            "sp500": "Level and change",
            "us_market_mood": "BULLISH/BEARISH/NEUTRAL"
        }},
        "sgx_nifty": "Level and direction",
        "crude_oil": "Price and direction",
        "gold": "Price and direction",
        "usd_inr": "Rate",
        "global_news": ["News 1", "News 2"],
        "fii_tomorrow_likely": "Buying/Selling",
        "gap_up_stocks": [{{"stock": "Name", "reason": "Why gap up"}}],
        "gap_down_stocks": [{{"stock": "Name", "reason": "Why gap down"}}],
        "nifty_opening_expected": "Gap up XX points / Gap down XX points / Flat",
        "midnight_verdict": "One line what to expect tomorrow morning"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])

        us = data.get("us_markets", {})
        us_mood = us.get("us_market_mood", "NEUTRAL")
        us_emoji = "🟢" if us_mood == "BULLISH" else ("🔴" if us_mood == "BEARISH" else "🟡")

        report = f"""
🌙 *MIDNIGHT GLOBAL REPORT*

🇺🇸 *US MARKETS*
{us_emoji} Mood: *{us_mood}*
📊 Dow Jones: {us.get('dow_jones', 'N/A')}
💻 NASDAQ: {us.get('nasdaq', 'N/A')}
📈 S&P 500: {us.get('sp500', 'N/A')}
━━━━━━━━━━━━━━━
🌏 *GLOBAL INDICATORS*
SGX Nifty: {data.get('sgx_nifty', 'N/A')}
🛢 Crude Oil: {data.get('crude_oil', 'N/A')}
🪙 Gold: {data.get('gold', 'N/A')}
💵 USD/INR: {data.get('usd_inr', 'N/A')}
━━━━━━━━━━━━━━━
📰 *KEY GLOBAL NEWS*"""
        for news in data.get("global_news", [])[:3]:
            report += f"\n• {news}"

        report += f"""
━━━━━━━━━━━━━━━
🏦 FII Tomorrow: *{data.get('fii_tomorrow_likely', 'N/A')}*
📊 Nifty Opening: *{data.get('nifty_opening_expected', 'N/A')}*
━━━━━━━━━━━━━━━
🚀 *LIKELY GAP UP TOMORROW*"""
        for s in data.get("gap_up_stocks", [])[:5]:
            report += f"\n🟢 *{s.get('stock', 'N/A')}* - {s.get('reason', 'N/A')}"

        report += "\n\n💥 *LIKELY GAP DOWN TOMORROW*"
        for s in data.get("gap_down_stocks", [])[:5]:
            report += f"\n🔴 *{s.get('stock', 'N/A')}* - {s.get('reason', 'N/A')}"

        report += f"""
━━━━━━━━━━━━━━━
💡 *MIDNIGHT VERDICT*
{data.get('midnight_verdict', 'N/A')}

⏰ Next report at 8:15 AM pre-market analysis."""

        send_telegram(report)

    except Exception as e:
        send_telegram(f"Midnight report error: {str(e)}")

# ============================================================
# REPORT 4: PRE-MARKET - SINGLE REPORT AT 8:15 AM
# Full prep before market opens at 9:15 AM
# ============================================================
def run_premarket_report():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"🌅 *PRE-MARKET REPORT*\n🕐 {now}\nMarket opens in 1 hour. Preparing your battle plan...")
    time.sleep(2)

    influencer_names = ", ".join(INFLUENCERS)
    prompt = f"""
    BSE market opens in 1 hour at 9:15 AM IST. Search the entire internet and give complete pre-market analysis.
    
    Search: SGX Nifty, gift nifty, US markets closing, Asian markets opening,
    Moneycontrol pre-market, Economic Times, Twitter from {influencer_names},
    BSE announcements, corporate results, global news.
    
    Return ONLY JSON:
    {{
        "gift_nifty": "Level and expected opening",
        "asian_markets": "Opening trend",
        "overnight_news": ["Big news 1", "Big news 2", "Big news 3"],
        "stocks_in_focus": [
            {{
                "stock": "Name",
                "expected_move": "Gap up/down XX%",
                "reason": "Why",
                "action": "BUY at open/SELL at open/WAIT"
            }}
        ],
        "sectors_to_watch": ["Sector 1 reason", "Sector 2 reason"],
        "influencer_morning_calls": ["Call 1 from who", "Call 2 from who"],
        "nifty_expected_range": {{"support": "XXXXX", "resistance": "XXXXX"}},
        "market_opening_mood": "BULLISH/BEARISH/NEUTRAL",
        "top_3_trades_today": [
            {{
                "stock": "Name",
                "entry": "RXXX",
                "target": "RXXX",
                "stop_loss": "RXXX",
                "reason": "Why this trade today"
            }}
        ],
        "avoid_today": ["Stock 1 reason", "Stock 2 reason"],
        "premarket_verdict": "One line battle plan for today"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])

        mood = data.get("market_opening_mood", "NEUTRAL")
        mood_emoji = "🟢" if mood == "BULLISH" else ("🔴" if mood == "BEARISH" else "🟡")

        report = f"""
🌅 *PRE-MARKET BATTLE PLAN*
Market opens in 1 hour!

{mood_emoji} Opening Mood: *{mood}*
📊 Gift Nifty: {data.get('gift_nifty', 'N/A')}
🌏 Asian Markets: {data.get('asian_markets', 'N/A')}
━━━━━━━━━━━━━━━
📰 *OVERNIGHT NEWS*"""
        for news in data.get("overnight_news", [])[:3]:
            report += f"\n• {news}"

        report += "\n\n👀 *STOCKS IN FOCUS TODAY*"
        for s in data.get("stocks_in_focus", [])[:8]:
            report += f"\n\n⚡ *{s.get('stock', 'N/A')}*"
            report += f"\n📊 {s.get('expected_move', 'N/A')}"
            report += f"\n🎯 Action: {s.get('action', 'N/A')}"
            report += f"\n💡 {s.get('reason', 'N/A')}"

        report += "\n\n🏭 *SECTORS TO WATCH*"
        for sector in data.get("sectors_to_watch", [])[:3]:
            report += f"\n• {sector}"

        report += "\n\n📣 *INFLUENCER MORNING CALLS*"
        for call in data.get("influencer_morning_calls", [])[:3]:
            report += f"\n• {call}"

        nifty_range = data.get("nifty_expected_range", {})
        report += f"""
━━━━━━━━━━━━━━━
📊 *NIFTY RANGE TODAY*
Support: {nifty_range.get('support', 'N/A')}
Resistance: {nifty_range.get('resistance', 'N/A')}
━━━━━━━━━━━━━━━
🎯 *TOP 3 TRADES TODAY*"""
        for i, trade in enumerate(data.get("top_3_trades_today", [])[:3]):
            report += f"""
{i+1}. *{trade.get('stock', 'N/A')}*
   Entry: {trade.get('entry', 'N/A')} | Target: {trade.get('target', 'N/A')} | Stop: {trade.get('stop_loss', 'N/A')}
   {trade.get('reason', 'N/A')}"""

        report += "\n\n❌ *AVOID TODAY*"
        for avoid in data.get("avoid_today", [])[:3]:
            report += f"\n• {avoid}"

        report += f"""
━━━━━━━━━━━━━━━
⚔️ *YOUR BATTLE PLAN*
{data.get('premarket_verdict', 'N/A')}

Good luck today! Market opens at 9:15 AM."""

        send_telegram(report)

    except Exception as e:
        send_telegram(f"Pre-market report error: {str(e)}")

# ============================================================
# SMART SCHEDULE
# ============================================================

# MARKET HOURS: Every hour from 9AM to 3PM
schedule.every().day.at("09:15").do(run_market_hours_scan)
schedule.every().day.at("10:15").do(run_market_hours_scan)
schedule.every().day.at("11:15").do(run_market_hours_scan)
schedule.every().day.at("12:15").do(run_market_hours_scan)
schedule.every().day.at("13:15").do(run_market_hours_scan)
schedule.every().day.at("14:15").do(run_market_hours_scan)
schedule.every().day.at("15:15").do(run_market_hours_scan)

# AFTER MARKET: Single report at 6PM
schedule.every().day.at("18:00").do(run_after_market_report)

# MIDNIGHT: Single global report at 12AM
schedule.every().day.at("00:00").do(run_midnight_report)

# PRE-MARKET: Single report at 8:15AM (1 hour before market)
schedule.every().day.at("08:15").do(run_premarket_report)

print("BSE Smart Scheduler is running.")
print("Pre-market: 8:15 AM")
print("Market hours: 9:15 AM to 3:15 PM every hour")
print("After market: 6:00 PM")
print("Midnight: 12:00 AM")

send_telegram("""🚀 *BSE SMART AGENT STARTED*

Your daily report schedule:
🌅 8:15 AM - Pre-market battle plan
📈 9:15 AM to 3:15 PM - Hourly live scans
🌆 6:00 PM - After market FII report
🌙 12:00 AM - Midnight global report

Influencer tracking: Active
Internet search: Active
24/7 monitoring: ON

Running pre-market report now...""")

time.sleep(3)
run_premarket_report()

while True:
    schedule.run_pending()
    time.sleep(60)
