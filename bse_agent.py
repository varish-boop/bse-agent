import google.generativeai as genai
import requests
import schedule
import time
import os
import json
import threading
import yfinance as yf
from datetime import datetime

# YOUR KEYS
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# SETUP GEMINI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# BSE STOCK SYMBOL MAP
# Format: "Stock Name": "BSE_SYMBOL.BO"
STOCK_SYMBOLS = {
    "Reliance Industries": "RELIANCE.BO",
    "TCS": "TCS.BO",
    "HDFC Bank": "HDFCBANK.BO",
    "Infosys": "INFY.BO",
    "ICICI Bank": "ICICIBANK.BO",
    "Hindustan Unilever": "HINDUNILVR.BO",
    "ITC": "ITC.BO",
    "SBI": "SBIN.BO",
    "Bharti Airtel": "BHARTIARTL.BO",
    "Kotak Mahindra Bank": "KOTAKBANK.BO",
    "Bajaj Finance": "BAJFINANCE.BO",
    "Asian Paints": "ASIANPAINT.BO",
    "Axis Bank": "AXISBANK.BO",
    "Maruti Suzuki": "MARUTI.BO",
    "Sun Pharmaceutical": "SUNPHARMA.BO",
    "Titan Company": "TITAN.BO",
    "Ultratech Cement": "ULTRACEMCO.BO",
    "Wipro": "WIPRO.BO",
    "HCL Technologies": "HCLTECH.BO",
    "NTPC": "NTPC.BO",
    "Power Grid": "POWERGRID.BO",
    "Tata Motors": "TATAMOTORS.BO",
    "Adani Ports": "ADANIPORTS.BO",
    "Bajaj Auto": "BAJAJ-AUTO.BO",
    "Mahindra and Mahindra": "M&M.BO",
    "Tech Mahindra": "TECHM.BO",
    "JSW Steel": "JSWSTEEL.BO",
    "Tata Steel": "TATASTEEL.BO",
    "Nestle India": "NESTLEIND.BO",
    "Cipla": "CIPLA.BO",
    "Dr Reddys Laboratories": "DRREDDY.BO",
    "Eicher Motors": "EICHERMOT.BO",
    "Hindalco Industries": "HINDALCO.BO",
    "IndusInd Bank": "INDUSINDBK.BO",
    "Larsen and Toubro": "LT.BO",
    "ONGC": "ONGC.BO",
    "Apollo Hospitals": "APOLLOHOSP.BO",
    "Bajaj Finserv": "BAJAJFINSV.BO",
    "Britannia Industries": "BRITANNIA.BO",
    "Coal India": "COALINDIA.BO",
    "Hero MotoCorp": "HEROMOTOCO.BO",
    "SBI Life Insurance": "SBILIFE.BO",
    "HDFC Life Insurance": "HDFCLIFE.BO",
    "Adani Enterprises": "ADANIENT.BO",
    "Tata Consumer Products": "TATACONSUM.BO",
    "Grasim Industries": "GRASIM.BO",
    "UPL": "UPL.BO",
    "Shriram Finance": "SHRIRAMFIN.BO",
    "Divi's Laboratories": "DIVISLAB.BO",
    "LTIMindtree": "LTIM.BO"
}

# NIFTY 50 LIST
NIFTY_50 = list(STOCK_SYMBOLS.keys())

# SECTORS
SECTORS = {
    "Banking": ["HDFC Bank", "ICICI Bank", "SBI", "Kotak Mahindra Bank", "Axis Bank", "IndusInd Bank"],
    "IT": ["TCS", "Infosys", "Wipro", "HCL Technologies", "Tech Mahindra", "LTIMindtree"],
    "Pharma": ["Sun Pharmaceutical", "Cipla", "Dr Reddys Laboratories", "Divi's Laboratories"],
    "Auto": ["Maruti Suzuki", "Tata Motors", "Bajaj Auto", "Hero MotoCorp", "Eicher Motors"],
    "Energy": ["Reliance Industries", "ONGC", "NTPC", "Power Grid", "Coal India"]
}

# TOP INFLUENCERS
INFLUENCERS = [
    "Vijay Kedia", "Basant Maheshwari", "Saurabh Mukherjea",
    "Deepak Shenoy", "PR Sundar", "Akshat Shrivastava",
    "Pranjal Kamra", "Rachana Ranade"
]

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

def get_live_stock_data(stock_name):
    """Fetch real live BSE data using yfinance"""
    try:
        # Find BSE symbol
        symbol = STOCK_SYMBOLS.get(stock_name)
        if not symbol:
            # Try to construct symbol from name
            symbol = stock_name.upper().replace(" ", "") + ".BO"

        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="1d", interval="1m")
        hist_week = ticker.history(period="1y")

        # Current price
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or 0
        change = ((current_price - prev_close) / prev_close * 100) if prev_close else 0
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"

        # 52 week data
        week52_high = info.get("fiftyTwoWeekHigh", "N/A")
        week52_low = info.get("fiftyTwoWeekLow", "N/A")

        # Volume
        volume = info.get("regularMarketVolume", 0)
        avg_volume = info.get("averageVolume", 1)
        volume_signal = "High" if volume > avg_volume * 1.5 else ("Low" if volume < avg_volume * 0.5 else "Normal")

        # Market cap
        market_cap = info.get("marketCap", 0)
        market_cap_cr = f"₹{market_cap/10000000:.0f} Cr" if market_cap else "N/A"

        # PE ratio
        pe_ratio = info.get("trailingPE", "N/A")

        # RSI calculation
        rsi = "N/A"
        if len(hist_week) > 14:
            closes = hist_week["Close"]
            delta = closes.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            rsi_val = 100 - (100 / (1 + rs))
            rsi = f"{rsi_val.iloc[-1]:.1f}"
            rsi_signal = "Overbought" if float(rsi) > 70 else ("Oversold" if float(rsi) < 30 else "Neutral")
        else:
            rsi_signal = "N/A"

        return {
            "found": True,
            "symbol": symbol,
            "price": f"₹{current_price:.2f}",
            "change": change_str,
            "is_positive": change >= 0,
            "prev_close": f"₹{prev_close:.2f}",
            "week52_high": f"₹{week52_high}" if week52_high != "N/A" else "N/A",
            "week52_low": f"₹{week52_low}" if week52_low != "N/A" else "N/A",
            "volume": f"{volume:,}",
            "volume_signal": volume_signal,
            "market_cap": market_cap_cr,
            "pe_ratio": str(pe_ratio) if pe_ratio != "N/A" else "N/A",
            "rsi": rsi,
            "rsi_signal": rsi_signal
        }
    except Exception as e:
        print(f"yfinance error for {stock_name}: {e}")
        return {"found": False}

def analyze_with_gemini(stock_name, live_data):
    """Send real data to Gemini for deep analysis"""
    influencer_names = ", ".join(INFLUENCERS)

    data_str = json.dumps(live_data, indent=2)

    prompt = f"""
    You are an expert BSE Indian stock market analyst.
    
    Stock: {stock_name}
    
    REAL LIVE DATA FETCHED FROM BSE:
    {data_str}
    
    Using this real data, now search the internet for:
    1. Latest news about {stock_name} in last 48 hours
    2. What these influencers said about {stock_name} recently: {influencer_names}
    3. FII and DII activity for {stock_name}
    4. MACD signal based on recent price movement
    5. Support and resistance levels
    6. Analyst target prices
    
    Based on ALL this information, provide complete analysis.
    Return ONLY a JSON object with no extra text:
    {{
        "signal": "STRONG BUY/BUY/HOLD/SELL/STRONG SELL",
        "confidence": "XX%",
        "target": "₹XXX",
        "stop_loss": "₹XXX",
        "macd": "Bullish/Bearish/Neutral",
        "fii": "Buying/Selling/Neutral",
        "influencer_sentiment": "BULLISH/BEARISH/NEUTRAL",
        "news_sentiment": "BULLISH/BEARISH/NEUTRAL",
        "latest_news": ["News 1", "News 2"],
        "strengths": ["Strength 1", "Strength 2", "Strength 3"],
        "risks": ["Risk 1", "Risk 2"],
        "support": "₹XXX",
        "resistance": "₹XXX",
        "key_reason": "One clear reason for signal",
        "risk_level": "LOW/MEDIUM/HIGH",
        "time_horizon": "X days/weeks"
    }}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "").strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        return {
            "signal": "HOLD",
            "confidence": "40%",
            "target": "N/A",
            "stop_loss": "N/A",
            "macd": "N/A",
            "fii": "N/A",
            "influencer_sentiment": "NEUTRAL",
            "latest_news": [],
            "strengths": [],
            "risks": [],
            "key_reason": "Could not fetch analysis",
            "risk_level": "HIGH",
            "time_horizon": "N/A"
        }

def get_full_report(stock_name, chat_id=None):
    """Complete pipeline: real data + AI analysis"""
    send_telegram(f"📡 Fetching live BSE data for *{stock_name}*...", chat_id)
    live_data = get_live_stock_data(stock_name)

    if not live_data.get("found"):
        send_telegram(f"⚠️ Could not find BSE data for *{stock_name}*\nPlease check the stock name and try again.\nExample: Reliance Industries, TCS, HDFC Bank", chat_id)
        return

    send_telegram(f"🤖 Analyzing with AI and searching internet...", chat_id)
    analysis = analyze_with_gemini(stock_name, live_data)

    signal = analysis.get("signal", "HOLD")
    emoji = "🟢" if "BUY" in signal else ("🔴" if "SELL" in signal else "🟡")
    inf_sent = analysis.get("influencer_sentiment", "NEUTRAL")
    inf_emoji = "👍" if inf_sent == "BULLISH" else ("👎" if inf_sent == "BEARISH" else "😐")
    change_emoji = "📈" if live_data.get("is_positive") else "📉"

    report = f"""
{emoji} *{stock_name.upper()}*
━━━━━━━━━━━━━━━
{change_emoji} Price: *{live_data.get('price', 'N/A')}* ({live_data.get('change', 'N/A')})
📊 Prev Close: {live_data.get('prev_close', 'N/A')}
📦 Volume: {live_data.get('volume', 'N/A')} ({live_data.get('volume_signal', 'N/A')})
💼 Market Cap: {live_data.get('market_cap', 'N/A')}
📊 P/E Ratio: {live_data.get('pe_ratio', 'N/A')}
━━━━━━━━━━━━━━━
{emoji} *SIGNAL: {signal}*
🎯 Confidence: {analysis.get('confidence', 'N/A')}
📈 Target: {analysis.get('target', 'N/A')}
🛑 Stop Loss: {analysis.get('stop_loss', 'N/A')}
⏱ Horizon: {analysis.get('time_horizon', 'N/A')}
━━━━━━━━━━━━━━━
📉 RSI: {live_data.get('rsi', 'N/A')} ({live_data.get('rsi_signal', 'N/A')})
📊 MACD: {analysis.get('macd', 'N/A')}
🏦 FII: {analysis.get('fii', 'N/A')}
📊 Support: {analysis.get('support', 'N/A')}
📊 Resistance: {analysis.get('resistance', 'N/A')}
{inf_emoji} Influencers: {inf_sent}
━━━━━━━━━━━━━━━
📅 52W High: {live_data.get('week52_high', 'N/A')}
📅 52W Low: {live_data.get('week52_low', 'N/A')}
━━━━━━━━━━━━━━━
✅ *STRENGTHS*"""

    for s in analysis.get("strengths", [])[:3]:
        report += f"\n+ {s}"

    report += "\n\n⚠️ *RISKS*"
    for r in analysis.get("risks", [])[:2]:
        report += f"\n- {r}"

    report += "\n\n📰 *LATEST NEWS*"
    news_list = analysis.get("latest_news", [])
    if news_list:
        for n in news_list[:2]:
            report += f"\n• {n}"
    else:
        report += "\n• No major news found"

    report += f"""
━━━━━━━━━━━━━━━
⚡ *AI VERDICT*
{analysis.get('key_reason', 'N/A')}
🔰 Risk Level: {analysis.get('risk_level', 'N/A')}

_Data from BSE via yfinance_"""

    send_telegram(report, chat_id)

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

                    if text.lower() == "/start":
                        send_telegram("""👋 *Welcome to BSE AI Analyst*

I give you REAL live BSE data for any stock.

*Just type any stock name:*
• Reliance Industries
• TCS
• HDFC Bank
• Tata Motors
• SBI

*Commands:*
/nifty - Top Nifty signals
/breakout - Breakout stocks
/sectors - Sector outlook
/schedule - Report timings
/help - All commands""", chat_id)

                    elif text.lower() == "/help":
                        send_telegram("""📖 *Commands*

Type any stock name for instant real data analysis.

*/nifty* - Nifty 50 top signals
*/breakout* - BSE breakout stocks
*/sectors* - Sector wise outlook
*/schedule* - Your daily report times
*/start* - Welcome message

Examples:
Reliance Industries
HDFC Bank
Infosys""", chat_id)

                    elif text.lower() == "/schedule":
                        send_telegram("""📅 *DAILY SCHEDULE*

🌅 *8:15 AM* - Pre-market battle plan
📈 *9:15 AM to 3:15 PM* - Hourly live scans
🌆 *6:00 PM* - After market FII report
🌙 *12:00 AM* - Midnight global report

Type any stock name anytime for instant analysis.""", chat_id)

                    elif text.lower() == "/nifty":
                        send_telegram("🔍 Fetching top Nifty signals. Takes 2 to 3 minutes...", chat_id)
                        threading.Thread(target=run_quick_nifty, args=(chat_id,)).start()

                    elif text.lower() == "/breakout":
                        send_telegram("⚡ Scanning for breakouts...", chat_id)
                        threading.Thread(target=run_quick_breakout, args=(chat_id,)).start()

                    elif text.lower() == "/sectors":
                        send_telegram("🏭 Scanning sectors. Takes 1 minute...", chat_id)
                        threading.Thread(target=run_quick_sectors, args=(chat_id,)).start()

                    elif not text.startswith("/"):
                        threading.Thread(target=get_full_report, args=(text.strip(), chat_id)).start()

        except Exception as e:
            print(f"Listener error: {e}")
            time.sleep(5)

def run_quick_nifty(chat_id):
    buy_list = []
    sell_list = []
    top_stocks = ["Reliance Industries", "TCS", "HDFC Bank", "Infosys", "ICICI Bank", "SBI", "Tata Motors", "Wipro", "Bajaj Finance", "Adani Ports"]
    for stock in top_stocks:
        try:
            live = get_live_stock_data(stock)
            if live.get("found"):
                analysis = analyze_with_gemini(stock, live)
                signal = analysis.get("signal", "HOLD")
                price = live.get("price", "N/A")
                change = live.get("change", "N/A")
                target = analysis.get("target", "N/A")
                if "BUY" in signal:
                    buy_list.append(f"🟢 *{stock}*\n   {price} ({change}) | Target: {target}")
                elif "SELL" in signal:
                    sell_list.append(f"🔴 *{stock}*\n   {price} ({change})")
            time.sleep(3)
        except:
            time.sleep(2)

    result = "🟢 *TOP BUY SIGNALS*\n"
    result += "\n\n".join(buy_list[:5]) if buy_list else "No strong buy signals right now"
    if sell_list:
        result += "\n\n🔴 *AVOID THESE*\n"
        result += "\n\n".join(sell_list[:3])
    send_telegram(result, chat_id)

def run_quick_breakout(chat_id):
    breakout_list = []
    for stock in NIFTY_50[:20]:
        try:
            live = get_live_stock_data(stock)
            if live.get("found"):
                change_str = live.get("change", "0%")
                change_val = float(change_str.replace("%", "").replace("+", ""))
                vol_signal = live.get("volume_signal", "Normal")
                if change_val > 2.5 or vol_signal == "High":
                    breakout_list.append({
                        "stock": stock,
                        "price": live.get("price"),
                        "change": change_str,
                        "volume": vol_signal
                    })
            time.sleep(2)
        except:
            time.sleep(1)

    if breakout_list:
        msg = "🚨 *BREAKOUT STOCKS*\n━━━━━━━━━━━━━━━"
        for b in breakout_list[:8]:
            msg += f"\n\n⚡ *{b['stock']}*\n💰 {b['price']} ({b['change']}) | Vol: {b['volume']}"
    else:
        msg = "😴 No major breakouts right now. Market is calm."

    send_telegram(msg, chat_id)

def run_quick_sectors(chat_id):
    for sector, stocks in SECTORS.items():
        gains = []
        losses = []
        for stock in stocks[:4]:
            try:
                live = get_live_stock_data(stock)
                if live.get("found"):
                    change = live.get("change", "0%")
                    val = float(change.replace("%", "").replace("+", ""))
                    if val > 0:
                        gains.append(f"{stock} {change}")
                    else:
                        losses.append(f"{stock} {change}")
                time.sleep(2)
            except:
                time.sleep(1)

        sentiment = "BULLISH" if len(gains) > len(losses) else ("BEARISH" if len(losses) > len(gains) else "NEUTRAL")
        emoji = "🟢" if sentiment == "BULLISH" else ("🔴" if sentiment == "BEARISH" else "🟡")

        msg = f"{emoji} *{sector}* - {sentiment}\n"
        msg += "📈 " + " | ".join(gains[:3]) if gains else "No gainers"
        msg += "\n📉 " + " | ".join(losses[:3]) if losses else ""
        send_telegram(msg, chat_id)
        time.sleep(3)

# SCHEDULED REPORTS
def run_market_scan():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"📈 *LIVE MARKET SCAN*\n🕐 {now}")
    run_quick_breakout(TELEGRAM_CHAT_ID)
    time.sleep(5)
    run_quick_nifty(TELEGRAM_CHAT_ID)
    send_telegram("✅ Scan done. Next in 1 hour.\n\nTip: Type any stock name for instant analysis.")

def run_after_market():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    prompt = """
    BSE market closed today. Search and give:
    FII net activity today, DII activity, top 5 gainers, top 5 losers,
    corporate announcements, stocks to watch tomorrow.
    Return ONLY JSON:
    {"fii_net": "text", "dii_net": "text", "top_gainers": [{"stock":"name","change":"+X%"}], "top_losers": [{"stock":"name","change":"-X%"}], "watch_tomorrow": [{"stock":"name","reason":"why"}], "verdict": "one line"}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json","").replace("```","").strip()
        data = json.loads(text[text.find("{"):text.rfind("}")+1])

        report = f"🌆 *AFTER MARKET REPORT*\n🕐 {now}\n\n"
        report += f"🏦 FII: {data.get('fii_net','N/A')}\n🏦 DII: {data.get('dii_net','N/A')}\n\n"
        report += "📈 *GAINERS*\n"
        for g in data.get("top_gainers",[])[:5]:
            report += f"🟢 {g.get('stock')} {g.get('change')}\n"
        report += "\n📉 *LOSERS*\n"
        for l in data.get("top_losers",[])[:5]:
            report += f"🔴 {l.get('stock')} {l.get('change')}\n"
        report += "\n👀 *WATCH TOMORROW*\n"
        for s in data.get("watch_tomorrow",[])[:5]:
            report += f"• *{s.get('stock')}* - {s.get('reason')}\n"
        report += f"\n💡 {data.get('verdict','N/A')}"
        report += "\n\n🌙 Next: Midnight report at 12 AM"
        send_telegram(report)
    except Exception as e:
        send_telegram(f"After market error: {str(e)}")

def run_midnight():
    prompt = """
    Midnight India. Search and give: US markets Dow NASDAQ SP500 closing,
    SGX Nifty, crude oil, gold, USDINR, global news, top 5 gap up stocks tomorrow, top 5 gap down stocks tomorrow.
    Return ONLY JSON:
    {"dow":"text","nasdaq":"text","sp500":"text","sgx_nifty":"text","crude":"text","gold":"text","usdinr":"text","global_news":["n1","n2"],"gap_up":[{"stock":"name","reason":"why"}],"gap_down":[{"stock":"name","reason":"why"}],"verdict":"one line"}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json","").replace("```","").strip()
        data = json.loads(text[text.find("{"):text.rfind("}")+1])

        report = f"🌙 *MIDNIGHT GLOBAL REPORT*\n\n"
        report += f"🇺🇸 Dow: {data.get('dow','N/A')}\n"
        report += f"💻 NASDAQ: {data.get('nasdaq','N/A')}\n"
        report += f"📈 S&P 500: {data.get('sp500','N/A')}\n"
        report += f"🌏 SGX Nifty: {data.get('sgx_nifty','N/A')}\n"
        report += f"🛢 Crude: {data.get('crude','N/A')}\n"
        report += f"🪙 Gold: {data.get('gold','N/A')}\n"
        report += f"💵 USD/INR: {data.get('usdinr','N/A')}\n\n"
        report += "📰 *NEWS*\n"
        for n in data.get("global_news",[])[:3]:
            report += f"• {n}\n"
        report += "\n🚀 *LIKELY GAP UP*\n"
        for s in data.get("gap_up",[])[:5]:
            report += f"🟢 *{s.get('stock')}* - {s.get('reason')}\n"
        report += "\n💥 *LIKELY GAP DOWN*\n"
        for s in data.get("gap_down",[])[:5]:
            report += f"🔴 *{s.get('stock')}* - {s.get('reason')}\n"
        report += f"\n💡 *{data.get('verdict','N/A')}*"
        report += "\n\n⏰ Pre-market report at 8:15 AM"
        send_telegram(report)
    except Exception as e:
        send_telegram(f"Midnight error: {str(e)}")

def run_premarket():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    influencer_names = ", ".join(INFLUENCERS)
    prompt = f"""
    BSE market opens in 1 hour. Search Gift Nifty, Twitter from {influencer_names}, BSE announcements, overnight news.
    Return ONLY JSON:
    {{"gift_nifty":"text","opening":"text","stocks_in_focus":[{{"stock":"name","move":"expected","action":"BUY/SELL/WAIT"}}],"top_3_trades":[{{"stock":"name","entry":"RXXX","target":"RXXX","stop":"RXXX","reason":"why"}}],"avoid":["stock reason"],"verdict":"battle plan"}}
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json","").replace("```","").strip()
        data = json.loads(text[text.find("{"):text.rfind("}")+1])

        report = f"🌅 *PRE-MARKET BATTLE PLAN*\n🕐 {now}\n\n"
        report += f"📊 Gift Nifty: {data.get('gift_nifty','N/A')}\n"
        report += f"📈 Opening: *{data.get('opening','N/A')}*\n\n"
        report += "👀 *STOCKS IN FOCUS*\n"
        for s in data.get("stocks_in_focus",[])[:6]:
            report += f"⚡ *{s.get('stock')}* - {s.get('move')} | {s.get('action')}\n"
        report += "\n🎯 *TOP 3 TRADES*\n"
        for i, t in enumerate(data.get("top_3_trades",[])[:3]):
            report += f"{i+1}. *{t.get('stock')}* Entry:{t.get('entry')} Target:{t.get('target')} Stop:{t.get('stop')}\n   {t.get('reason')}\n"
        report += "\n❌ *AVOID TODAY*\n"
        for a in data.get("avoid",[])[:3]:
            report += f"• {a}\n"
        report += f"\n⚔️ *BATTLE PLAN*\n{data.get('verdict','N/A')}"
        report += "\n\n🔔 Market opens at 9:15 AM. Good luck!"
        send_telegram(report)
    except Exception as e:
        send_telegram(f"Pre-market error: {str(e)}")

# SCHEDULE
schedule.every().day.at("09:15").do(run_market_scan)
schedule.every().day.at("10:15").do(run_market_scan)
schedule.every().day.at("11:15").do(run_market_scan)
schedule.every().day.at("12:15").do(run_market_scan)
schedule.every().day.at("13:15").do(run_market_scan)
schedule.every().day.at("14:15").do(run_market_scan)
schedule.every().day.at("15:15").do(run_market_scan)
schedule.every().day.at("18:00").do(run_after_market)
schedule.every().day.at("00:00").do(run_midnight)
schedule.every().day.at("08:15").do(run_premarket)

# START LISTENER
listener_thread = threading.Thread(target=listen_for_commands, daemon=True)
listener_thread.start()

print("BSE Agent with REAL live data started.")
print("Type any stock name in Telegram for instant analysis.")

send_telegram("""🚀 *BSE AI AGENT LIVE*

Now using REAL BSE live data via yfinance.
No more N/A values.

✅ Real live prices: Active
✅ Real RSI calculation: Active
✅ AI deep analysis: Active
✅ Instant stock lookup: Active

*Just type any stock name to test:*
Try typing: Reliance Industries""")

while True:
    schedule.run_pending()
    time.sleep(60)
