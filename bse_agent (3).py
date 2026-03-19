import google.generativeai as genai
import requests
import schedule
import time
import os
import json
import threading
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

# TRACK LAST MESSAGE ID TO AVOID DUPLICATES
last_update_id = 0

def send_telegram(message, chat_id=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id or TELEGRAM_CHAT_ID,
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
        "news_sentiment": "BULLISH/BEARISH/NEUTRAL",
        "key_reason": "One line reason for signal",
        "strengths": ["Point 1", "Point 2", "Point 3"],
        "risks": ["Risk 1", "Risk 2"],
        "latest_news": ["News 1", "News 2"],
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
            "stop_loss": "N/A", "key_reason": "Analysis failed",
            "strengths": [], "risks": [], "latest_news": [], "risk": "HIGH"
        }

def format_stock_report(data):
    signal = data.get("signal", "HOLD")
    emoji = "🟢" if "BUY" in signal else ("🔴" if "SELL" in signal else "🟡")
    inf_sent = data.get("influencer_sentiment", "NEUTRAL")
    inf_emoji = "👍" if inf_sent == "BULLISH" else ("👎" if inf_sent == "BEARISH" else "😐")

    report = f"""
{emoji} *{data.get('stock', 'N/A')} ANALYSIS*
━━━━━━━━━━━━━━━
💰 Price: {data.get('price', 'N/A')} ({data.get('change', 'N/A')})
📊 Signal: *{signal}*
🎯 Confidence: {data.get('confidence', 'N/A')}
📈 Target: {data.get('target', 'N/A')}
🛑 Stop Loss: {data.get('stop_loss', 'N/A')}
━━━━━━━━━━━━━━━
📉 RSI: {data.get('rsi', 'N/A')}
📊 MACD: {data.get('macd', 'N/A')}
🏦 FII: {data.get('fii', 'N/A')}
📦 Volume: {data.get('volume', 'N/A')}
{inf_emoji} Influencers: {inf_sent}
━━━━━━━━━━━━━━━
✅ *STRENGTHS*"""

    for s in data.get("strengths", [])[:3]:
        report += f"\n+ {s}"

    report += "\n\n⚠️ *RISKS*"
    for r in data.get("risks", [])[:2]:
        report += f"\n- {r}"

    report += "\n\n📰 *LATEST NEWS*"
    for n in data.get("latest_news", [])[:2]:
        report += f"\n• {n}"

    report += f"""
━━━━━━━━━━━━━━━
⚡ *VERDICT*
{data.get('key_reason', 'N/A')}
🔰 Risk Level: {data.get('risk', 'N/A')}"""

    return report

# ============================================================
# TELEGRAM BOT LISTENER
# Listens for incoming messages and replies instantly
# ============================================================
def listen_for_commands():
    global last_update_id
    print("Telegram command listener started...")

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {"offset": last_update_id + 1, "timeout": 30}
            response = requests.get(url, params=params, timeout=35)
            data = response.json()

            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    last_update_id = update["update_id"]
                    message = update.get("message", {})
                    text = message.get("text", "").strip()
                    chat_id = message.get("chat", {}).get("id")

                    if not text or not chat_id:
                        continue

                    print(f"Received: {text}")

                    # HANDLE /start command
                    if text.lower() == "/start":
                        send_telegram("""👋 *Welcome to BSE AI Analyst Bot*

I analyze any BSE stock instantly for you.

*HOW TO USE:*
Just type any stock name and I will send you a full report.

Examples:
• Reliance Industries
• TCS
• HDFC Bank
• Infosys
• Tata Motors

Or type /help to see all commands.""", chat_id)

                    # HANDLE /help command
                    elif text.lower() == "/help":
                        send_telegram("""📖 *BSE AI Bot Commands*

Type any stock name to get instant analysis.

*/start* - Welcome message
*/help* - Show this menu
*/nifty* - Top Nifty 50 signals right now
*/breakout* - Current breakout stocks
*/sectors* - Sector wise outlook
*/schedule* - Your daily report times

Or just type a stock name like:
*Reliance Industries*
*TCS*
*SBI*""", chat_id)

                    # HANDLE /nifty command
                    elif text.lower() == "/nifty":
                        send_telegram("🔍 Scanning top Nifty 50 stocks. Please wait 2 minutes...", chat_id)
                        threading.Thread(target=run_quick_nifty_scan, args=(chat_id,)).start()

                    # HANDLE /breakout command
                    elif text.lower() == "/breakout":
                        send_telegram("⚡ Scanning BSE for breakouts. Please wait...", chat_id)
                        threading.Thread(target=run_quick_breakout, args=(chat_id,)).start()

                    # HANDLE /sectors command
                    elif text.lower() == "/sectors":
                        send_telegram("🏭 Scanning all sectors. Please wait 1 minute...", chat_id)
                        threading.Thread(target=run_quick_sectors, args=(chat_id,)).start()

                    # HANDLE /schedule command
                    elif text.lower() == "/schedule":
                        send_telegram("""📅 *YOUR DAILY REPORT SCHEDULE*

🌅 *8:15 AM* - Pre-market battle plan
📈 *9:15 AM* - Live market scan
📈 *10:15 AM* - Live market scan
📈 *11:15 AM* - Live market scan
📈 *12:15 PM* - Live market scan
📈 *1:15 PM* - Live market scan
📈 *2:15 PM* - Live market scan
📈 *3:15 PM* - Live market scan
🌆 *6:00 PM* - After market FII report
🌙 *12:00 AM* - Midnight global report

Plus instant analysis anytime you type a stock name.""", chat_id)

                    # HANDLE STOCK NAME - any other text treated as stock query
                    elif not text.startswith("/"):
                        stock_name = text.strip()
                        send_telegram(f"🔍 Analyzing *{stock_name}*...\nSearching internet, BSE data, and influencer signals. Please wait 30 seconds...", chat_id)
                        threading.Thread(target=send_stock_report, args=(stock_name, chat_id)).start()

        except Exception as e:
            print(f"Listener error: {e}")
            time.sleep(5)

def send_stock_report(stock_name, chat_id):
    try:
        data = analyze_single_stock(stock_name)
        report = format_stock_report(data)
        send_telegram(report, chat_id)
    except Exception as e:
        send_telegram(f"Could not analyze {stock_name}. Please check the stock name and try again.", chat_id)

def run_quick_nifty_scan(chat_id):
    buy_stocks = []
    sell_stocks = []
    for stock in NIFTY_50[:15]:
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

    send_telegram(f"🟢 *TOP BUY SIGNALS*", chat_id)
    for stock in buy_stocks[:5]:
        send_telegram(format_stock_report(stock), chat_id)
        time.sleep(2)

    if sell_stocks:
        send_telegram(f"🔴 *AVOID THESE*", chat_id)
        for stock in sell_stocks[:3]:
            send_telegram(format_stock_report(stock), chat_id)
            time.sleep(2)

def run_quick_breakout(chat_id):
    prompt = f"""
    Search BSE right now for top 5 breakout stocks.
    Find stocks with volume spike, 52 week high, strong FII buying, or major news.
    Return ONLY JSON:
    {{
        "breakouts": [
            {{"stock": "Name", "price": "RXXX", "change": "+XX%", "reason": "Why", "target": "RXXX"}}
        ],
        "market_mood": "BULLISH/BEARISH/NEUTRAL"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])

        mood = data.get("market_mood", "NEUTRAL")
        mood_emoji = "🟢" if mood == "BULLISH" else ("🔴" if mood == "BEARISH" else "🟡")
        send_telegram(f"{mood_emoji} Market Mood: *{mood}*\n\n🚨 *BREAKOUT STOCKS*", chat_id)

        for stock in data.get("breakouts", [])[:5]:
            send_telegram(f"""
🚨 *{stock.get('stock', 'N/A')}*
💰 {stock.get('price', 'N/A')} ({stock.get('change', 'N/A')})
🎯 Target: {stock.get('target', 'N/A')}
⚡ {stock.get('reason', 'N/A')}
━━━━━━━━━━━━━━━""", chat_id)
            time.sleep(2)
    except Exception as e:
        send_telegram(f"Breakout scan error: {str(e)}", chat_id)

def run_quick_sectors(chat_id):
    for sector_name, stocks in SECTORS.items():
        try:
            stocks_str = ", ".join(stocks[:5])
            prompt = f"""
            Analyze {sector_name} sector on BSE. Stocks: {stocks_str}
            Return ONLY JSON:
            {{
                "signal": "BULLISH/BEARISH/NEUTRAL",
                "top_pick": "Best stock",
                "top_pick_target": "RXXX",
                "avoid": "Worst stock",
                "summary": "One line"
            }}
            """
            response = model.generate_content(prompt)
            text = response.text.strip().replace("```json", "").replace("```", "").strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            data = json.loads(text[start:end])

            signal = data.get("signal", "NEUTRAL")
            emoji = "🟢" if signal == "BULLISH" else ("🔴" if signal == "BEARISH" else "🟡")

            send_telegram(f"""
{emoji} *{sector_name}* - {signal}
⭐ Top Pick: *{data.get('top_pick', 'N/A')}* | Target: {data.get('top_pick_target', 'N/A')}
❌ Avoid: {data.get('avoid', 'N/A')}
💡 {data.get('summary', 'N/A')}
━━━━━━━━━━━━━━━""", chat_id)
            time.sleep(4)
        except:
            time.sleep(3)

# ============================================================
# SCHEDULED REPORTS
# ============================================================
def run_market_hours_scan():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"📈 *LIVE MARKET SCAN*\n🕐 {now}\nScanning Nifty 50 and breakouts...")
    run_quick_breakout(TELEGRAM_CHAT_ID)
    time.sleep(5)
    run_quick_nifty_scan(TELEGRAM_CHAT_ID)
    send_telegram("✅ *Live Scan Done*\nNext scan in 1 hour.\n\nTip: Type any stock name anytime for instant analysis.")

def run_after_market_report():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"🌆 *AFTER MARKET REPORT*\n🕐 {now}\nFetching FII data and closing analysis...")

    prompt = f"""
    BSE market closed today. Search and provide:
    FII net buying or selling today, DII activity, top 5 gainers, top 5 losers,
    corporate announcements, stocks to watch tomorrow, global market outlook.
    Return ONLY JSON:
    {{
        "fii_net": "Bought/Sold RXXXX Cr",
        "dii_net": "Bought/Sold RXXXX Cr",
        "top_gainers": [{{"stock": "Name", "change": "+XX%"}}],
        "top_losers": [{{"stock": "Name", "change": "-XX%"}}],
        "announcements": ["Ann 1", "Ann 2"],
        "watch_tomorrow": [{{"stock": "Name", "reason": "Why"}}],
        "global_outlook": "Positive/Negative with reason",
        "verdict": "One line summary"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])

        report = f"""
🏦 *FII:* {data.get('fii_net', 'N/A')}
🏦 *DII:* {data.get('dii_net', 'N/A')}

📈 *TOP GAINERS*"""
        for g in data.get("top_gainers", [])[:5]:
            report += f"\n🟢 {g.get('stock')} {g.get('change')}"

        report += "\n\n📉 *TOP LOSERS*"
        for l in data.get("top_losers", [])[:5]:
            report += f"\n🔴 {l.get('stock')} {l.get('change')}"

        report += "\n\n👀 *WATCH TOMORROW*"
        for s in data.get("watch_tomorrow", [])[:5]:
            report += f"\n• *{s.get('stock')}* - {s.get('reason')}"

        report += f"\n\n🌍 {data.get('global_outlook', 'N/A')}"
        report += f"\n\n💡 *{data.get('verdict', 'N/A')}*"
        report += "\n\n🌙 Next: Midnight global report at 12 AM"

        send_telegram(report)
    except Exception as e:
        send_telegram(f"After market error: {str(e)}")

def run_midnight_report():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"🌙 *MIDNIGHT GLOBAL REPORT*\n🕐 {now}")

    prompt = """
    It is midnight India time. Search and provide:
    US markets Dow, NASDAQ, S&P500 closing today, SGX Nifty direction,
    crude oil price, gold price, USD INR rate, major global news,
    top 5 Indian stocks likely to gap up tomorrow,
    top 5 Indian stocks likely to gap down tomorrow,
    expected Nifty opening tomorrow.
    Return ONLY JSON:
    {
        "dow": "Level change",
        "nasdaq": "Level change",
        "sp500": "Level change",
        "sgx_nifty": "Level direction",
        "crude": "Price direction",
        "gold": "Price direction",
        "usdinr": "Rate",
        "global_news": ["News 1", "News 2"],
        "gap_up": [{"stock": "Name", "reason": "Why"}],
        "gap_down": [{"stock": "Name", "reason": "Why"}],
        "nifty_opening": "Gap up/down XX points",
        "verdict": "One line"
    }
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])

        report = f"""
🇺🇸 Dow: {data.get('dow', 'N/A')}
💻 NASDAQ: {data.get('nasdaq', 'N/A')}
📈 S&P 500: {data.get('sp500', 'N/A')}
🌏 SGX Nifty: {data.get('sgx_nifty', 'N/A')}
🛢 Crude: {data.get('crude', 'N/A')}
🪙 Gold: {data.get('gold', 'N/A')}
💵 USD/INR: {data.get('usdinr', 'N/A')}

📰 *NEWS*"""
        for n in data.get("global_news", [])[:3]:
            report += f"\n• {n}"

        report += "\n\n🚀 *LIKELY GAP UP*"
        for s in data.get("gap_up", [])[:5]:
            report += f"\n🟢 *{s.get('stock')}* - {s.get('reason')}"

        report += "\n\n💥 *LIKELY GAP DOWN*"
        for s in data.get("gap_down", [])[:5]:
            report += f"\n🔴 *{s.get('stock')}* - {s.get('reason')}"

        report += f"\n\n📊 Nifty Opening: *{data.get('nifty_opening', 'N/A')}*"
        report += f"\n💡 *{data.get('verdict', 'N/A')}*"
        report += "\n\n⏰ Next: Pre-market report at 8:15 AM"

        send_telegram(report)
    except Exception as e:
        send_telegram(f"Midnight report error: {str(e)}")

def run_premarket_report():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"🌅 *PRE-MARKET BATTLE PLAN*\n🕐 {now}\nMarket opens in 1 hour...")

    influencer_names = ", ".join(INFLUENCERS)
    prompt = f"""
    BSE market opens in 1 hour. Search and give complete pre-market analysis.
    Search SGX Nifty, Gift Nifty, Twitter from {influencer_names}, BSE announcements.
    Return ONLY JSON:
    {{
        "gift_nifty": "Level direction",
        "opening_expected": "Gap up/down XX points",
        "stocks_in_focus": [{{"stock": "Name", "move": "Expected move", "action": "BUY/SELL/WAIT"}}],
        "top_3_trades": [{{"stock": "Name", "entry": "RXXX", "target": "RXXX", "stop": "RXXX", "reason": "Why"}}],
        "sectors_to_watch": ["Sector reason"],
        "influencer_calls": ["Call from who"],
        "avoid_today": ["Stock reason"],
        "verdict": "One line battle plan"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])

        report = f"""
📊 Gift Nifty: {data.get('gift_nifty', 'N/A')}
📈 Opening: *{data.get('opening_expected', 'N/A')}*

👀 *STOCKS IN FOCUS*"""
        for s in data.get("stocks_in_focus", [])[:6]:
            report += f"\n⚡ *{s.get('stock')}* - {s.get('move')} | Action: {s.get('action')}"

        report += "\n\n🎯 *TOP 3 TRADES TODAY*"
        for i, t in enumerate(data.get("top_3_trades", [])[:3]):
            report += f"\n{i+1}. *{t.get('stock')}* | Entry: {t.get('entry')} | Target: {t.get('target')} | Stop: {t.get('stop')}\n   {t.get('reason')}"

        report += "\n\n📣 *INFLUENCER CALLS*"
        for c in data.get("influencer_calls", [])[:3]:
            report += f"\n• {c}"

        report += "\n\n❌ *AVOID TODAY*"
        for a in data.get("avoid_today", [])[:3]:
            report += f"\n• {a}"

        report += f"\n\n⚔️ *BATTLE PLAN*\n{data.get('verdict', 'N/A')}"
        report += "\n\nGood luck! Market opens at 9:15 AM 🔔"

        send_telegram(report)
    except Exception as e:
        send_telegram(f"Pre-market error: {str(e)}")

# SCHEDULE
schedule.every().day.at("09:15").do(run_market_hours_scan)
schedule.every().day.at("10:15").do(run_market_hours_scan)
schedule.every().day.at("11:15").do(run_market_hours_scan)
schedule.every().day.at("12:15").do(run_market_hours_scan)
schedule.every().day.at("13:15").do(run_market_hours_scan)
schedule.every().day.at("14:15").do(run_market_hours_scan)
schedule.every().day.at("15:15").do(run_market_hours_scan)
schedule.every().day.at("18:00").do(run_after_market_report)
schedule.every().day.at("00:00").do(run_midnight_report)
schedule.every().day.at("08:15").do(run_premarket_report)

# START TELEGRAM LISTENER IN BACKGROUND THREAD
listener_thread = threading.Thread(target=listen_for_commands, daemon=True)
listener_thread.start()

print("BSE Smart Agent with Command Listener started.")
print("Type any stock name in Telegram to get instant analysis.")

send_telegram("""🚀 *BSE AI AGENT STARTED*

✅ Scheduled reports: Active
✅ Influencer tracking: Active
✅ Instant stock analysis: Active

*HOW TO GET INSTANT ANALYSIS:*
Just type any stock name in this chat.

Example: Type *Reliance Industries*
I will send you a full report instantly.

Commands:
/nifty - Top Nifty signals
/breakout - Breakout stocks
/sectors - Sector outlook
/schedule - Report timings
/help - All commands""")

# SCHEDULE LOOP
while True:
    schedule.run_pending()
    time.sleep(60)
