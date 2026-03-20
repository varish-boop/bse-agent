import google.generativeai as genai
import requests
import schedule
import time
import os
import json
import threading
import math
import yfinance as yf
import numpy as np
from datetime import datetime

# YOUR KEYS
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# SETUP GEMINI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# BSE STOCK SYMBOLS
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

NIFTY_50 = list(STOCK_SYMBOLS.keys())

SECTORS = {
    "Banking": ["HDFC Bank", "ICICI Bank", "SBI", "Kotak Mahindra Bank", "Axis Bank", "IndusInd Bank"],
    "IT": ["TCS", "Infosys", "Wipro", "HCL Technologies", "Tech Mahindra", "LTIMindtree"],
    "Pharma": ["Sun Pharmaceutical", "Cipla", "Dr Reddys Laboratories", "Divi's Laboratories"],
    "Auto": ["Maruti Suzuki", "Tata Motors", "Bajaj Auto", "Hero MotoCorp", "Eicher Motors"],
    "Energy": ["Reliance Industries", "ONGC", "NTPC", "Power Grid", "Coal India"]
}

INFLUENCERS = [
    "Vijay Kedia", "Basant Maheshwari", "Saurabh Mukherjea",
    "Deepak Shenoy", "PR Sundar", "Akshat Shrivastava",
    "Pranjal Kamra", "Rachana Ranade"
]

last_update_id = 0

# ─────────────────────────────────────────────
# FIX 1: send_telegram now splits long messages,
#         adds a timeout, and logs errors properly
# ─────────────────────────────────────────────
def send_telegram(message, chat_id=None):
    try:
        target_chat = chat_id or TELEGRAM_CHAT_ID
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        MAX_LEN = 4000  # Telegram hard limit is 4096 chars

        chunks = [message[i:i+MAX_LEN] for i in range(0, len(message), MAX_LEN)]

        for chunk in chunks:
            payload = {
                "chat_id": target_chat,
                "text": chunk,
                "parse_mode": "Markdown"
            }
            resp = requests.post(url, data=payload, timeout=15)
            if not resp.ok:
                print(f"Telegram API error: {resp.status_code} - {resp.text}")
            time.sleep(0.5)

    except Exception as e:
        print(f"Telegram error: {e}")


def get_live_stock_data(stock_name):
    try:
        symbol = STOCK_SYMBOLS.get(stock_name, stock_name.upper().replace(" ", "") + ".BO")
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # ─────────────────────────────────────────────
        # FIX 2: Use 1 year of data so 52-week high/low
        #         are actually 52-week values
        # ─────────────────────────────────────────────
        hist = ticker.history(period="1y")

        if hist.empty:
            return {"found": False}

        last_close = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last_close
        change = ((last_close - prev_close) / prev_close * 100) if prev_close else 0
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"

        volume = int(hist["Volume"].iloc[-1]) if not hist["Volume"].empty else 0
        avg_volume = int(hist["Volume"].mean()) if not hist["Volume"].empty else 1
        volume_signal = "High" if volume > avg_volume * 1.5 else ("Low" if volume < avg_volume * 0.5 else "Normal")

        # Now uses full 1 year for real 52-week values
        week52_high = float(hist["High"].max())
        week52_low = float(hist["Low"].min())

        # RSI calculation
        closes = hist["Close"]
        delta = closes.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))

        # ─────────────────────────────────────────────
        # FIX 3: Handle NaN in RSI and MACD so they
        #         never show as "nan" in the Telegram
        #         message
        # ─────────────────────────────────────────────
        rsi_val = float(rsi_series.iloc[-1])
        if math.isnan(rsi_val):
            rsi_val = 50.0
        rsi_signal = "Overbought" if rsi_val > 70 else ("Oversold" if rsi_val < 30 else "Neutral")

        # MACD calculation
        ema12 = closes.ewm(span=12).mean()
        ema26 = closes.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        macd_val = float(macd_line.iloc[-1])
        signal_val = float(signal_line.iloc[-1])

        if math.isnan(macd_val) or math.isnan(signal_val):
            macd_signal = "Neutral"
            macd_val = 0.0
        else:
            macd_signal = "Bullish" if macd_val > signal_val else "Bearish"

        recent_high = float(hist["High"].tail(20).max())
        recent_low = float(hist["Low"].tail(20).min())

        market_cap = info.get("marketCap", 0)
        market_cap_str = f"Rs.{market_cap/10000000:.0f} Cr" if market_cap else "N/A"
        pe_ratio = info.get("trailingPE", "N/A")
        pe_str = f"{pe_ratio:.2f}" if isinstance(pe_ratio, float) else "N/A"

        return {
            "found": True,
            "symbol": symbol,
            "price": f"Rs.{last_close:.2f}",
            "prev_close": f"Rs.{prev_close:.2f}",
            "change": change_str,
            "is_positive": change >= 0,
            "volume": f"{volume:,}",
            "volume_signal": volume_signal,
            "week52_high": f"Rs.{week52_high:.2f}",
            "week52_low": f"Rs.{week52_low:.2f}",
            "rsi": f"{rsi_val:.1f}",
            "rsi_signal": rsi_signal,
            "macd": macd_signal,
            "macd_value": f"{macd_val:.2f}",
            "support": f"Rs.{recent_low:.2f}",
            "resistance": f"Rs.{recent_high:.2f}",
            "market_cap": market_cap_str,
            "pe_ratio": pe_str
        }

    except Exception as e:
        print(f"yfinance error for {stock_name}: {e}")
        return {"found": False}


def call_gemini_with_retry(prompt, retries=3):
    for attempt in range(retries):
        try:
            time.sleep(3)
            response = model.generate_content(prompt)
            text = response.text.strip().replace("```json", "").replace("```", "").strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON found")
            return json.loads(text[start:end])
        except Exception as e:
            print(f"Gemini attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(10)
    return None


def analyze_with_gemini(stock_name, live_data):
    influencer_names = ", ".join(INFLUENCERS)
    prompt = f"""
    You are an expert BSE Indian stock market analyst.
    
    Stock: {stock_name}
    
    REAL LIVE DATA FROM BSE:
    Price: {live_data.get('price')}
    Change: {live_data.get('change')}
    RSI: {live_data.get('rsi')} ({live_data.get('rsi_signal')})
    MACD: {live_data.get('macd')}
    Support: {live_data.get('support')}
    Resistance: {live_data.get('resistance')}
    52W High: {live_data.get('week52_high')}
    52W Low: {live_data.get('week52_low')}
    Volume: {live_data.get('volume')} ({live_data.get('volume_signal')})
    Market Cap: {live_data.get('market_cap')}
    PE Ratio: {live_data.get('pe_ratio')}
    
    Based on this real data, search internet for:
    1. Latest news about {stock_name} in last 48 hours from Economic Times, Moneycontrol, Mint
    2. What these influencers said about {stock_name}: {influencer_names}
    3. FII and DII activity for {stock_name}
    4. Analyst target prices from brokers
    
    Give BUY signal if RSI is below 40 and MACD is Bullish.
    Give SELL signal if RSI is above 70 and MACD is Bearish.
    Give HOLD otherwise.
    
    Calculate target price as 8 to 15 percent above current price for BUY.
    Calculate stop loss as 4 to 6 percent below current price for BUY.
    
    Return ONLY a valid JSON object:
    {{
        "signal": "STRONG BUY/BUY/HOLD/SELL/STRONG SELL",
        "confidence": "XX%",
        "target": "Rs.XXX",
        "stop_loss": "Rs.XXX",
        "fii": "Buying/Selling/Neutral",
        "influencer_sentiment": "BULLISH/BEARISH/NEUTRAL",
        "latest_news": ["News headline 1", "News headline 2"],
        "strengths": ["Strength 1", "Strength 2", "Strength 3"],
        "risks": ["Risk 1", "Risk 2"],
        "key_reason": "One clear reason for this signal",
        "risk_level": "LOW/MEDIUM/HIGH",
        "time_horizon": "X to Y weeks"
    }}
    """

    result = call_gemini_with_retry(prompt)

    if result:
        return result

    # Rule-based fallback when Gemini fails
    rsi_val = float(live_data.get("rsi", 50))
    macd = live_data.get("macd", "Neutral")
    price_str = live_data.get("price", "Rs.0").replace("Rs.", "").replace(",", "")

    try:
        price = float(price_str)
        target = f"Rs.{price * 1.10:.2f}"
        stop_loss = f"Rs.{price * 0.95:.2f}"
    except:
        target = "N/A"
        stop_loss = "N/A"

    if rsi_val < 40 and macd == "Bullish":
        signal = "BUY"
        confidence = "65%"
        reason = f"RSI at {rsi_val:.1f} is oversold and MACD is bullish. Good entry point."
    elif rsi_val > 70 and macd == "Bearish":
        signal = "SELL"
        confidence = "65%"
        reason = f"RSI at {rsi_val:.1f} is overbought and MACD is bearish. Consider booking profit."
    elif rsi_val < 50 and macd == "Bullish":
        signal = "BUY"
        confidence = "55%"
        reason = f"MACD is bullish with RSI at {rsi_val:.1f}. Moderate buy opportunity."
    else:
        signal = "HOLD"
        confidence = "50%"
        reason = f"RSI at {rsi_val:.1f} and MACD {macd}. Wait for clearer signal."

    return {
        "signal": signal,
        "confidence": confidence,
        "target": target,
        "stop_loss": stop_loss,
        "fii": "Data unavailable",
        "influencer_sentiment": "NEUTRAL",
        "latest_news": ["Could not fetch news. Check Moneycontrol for latest updates."],
        "strengths": [
            f"RSI at {rsi_val:.1f}",
            f"MACD is {macd}",
            f"Support at {live_data.get('support', 'N/A')}"
        ],
        "risks": [
            "Market volatility",
            "Global cues may affect performance"
        ],
        "key_reason": reason,
        "risk_level": "MEDIUM",
        "time_horizon": "2 to 4 weeks"
    }


def get_full_report(stock_name, chat_id=None):
    send_telegram(f"Fetching live BSE data for *{stock_name}*...", chat_id)
    live_data = get_live_stock_data(stock_name)

    if not live_data.get("found"):
        send_telegram(f"Could not find BSE data for *{stock_name}*\nCheck the spelling and try again.\nExample: Reliance Industries, TCS, HDFC Bank", chat_id)
        return

    send_telegram(f"Running AI analysis...", chat_id)
    analysis = analyze_with_gemini(stock_name, live_data)

    signal = analysis.get("signal", "HOLD")
    emoji = "BUY" if "BUY" in signal else ("SELL" if "SELL" in signal else "HOLD")
    inf_sent = analysis.get("influencer_sentiment", "NEUTRAL")
    change_emoji = "UP" if live_data.get("is_positive") else "DOWN"

    report = f"""
*{stock_name.upper()}*
Price: *{live_data.get('price')}* ({live_data.get('change')}) {change_emoji}
Prev Close: {live_data.get('prev_close')}
Volume: {live_data.get('volume')} ({live_data.get('volume_signal')})
Market Cap: {live_data.get('market_cap')}
P/E Ratio: {live_data.get('pe_ratio')}

*SIGNAL: {signal}*
Confidence: {analysis.get('confidence')}
Target: {analysis.get('target')}
Stop Loss: {analysis.get('stop_loss')}
Horizon: {analysis.get('time_horizon')}

RSI: {live_data.get('rsi')} ({live_data.get('rsi_signal')})
MACD: {live_data.get('macd')}
Support: {live_data.get('support')}
Resistance: {live_data.get('resistance')}
FII: {analysis.get('fii')}
Influencers: {inf_sent}

52W High: {live_data.get('week52_high')}
52W Low: {live_data.get('week52_low')}

*STRENGTHS*"""

    for s in analysis.get("strengths", [])[:3]:
        report += f"\n+ {s}"

    report += "\n\n*RISKS*"
    for r in analysis.get("risks", [])[:2]:
        report += f"\n- {r}"

    report += "\n\n*LATEST NEWS*"
    for n in analysis.get("latest_news", [])[:2]:
        report += f"\n- {n}"

    report += f"""

*AI VERDICT*
{analysis.get('key_reason')}
Risk Level: {analysis.get('risk_level')}

Real BSE data via yfinance"""

    send_telegram(report, chat_id)


def listen_for_commands():
    global last_update_id
    print("Telegram listener started...")
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
                        send_telegram("""*Welcome to BSE AI Analyst*

Real live BSE data for any stock instantly.

Just type any stock name:
- Reliance Industries
- TCS
- HDFC Bank
- SBI
- Tata Motors

Commands:
/nifty - Top Nifty signals
/breakout - Breakout stocks
/sectors - Sector outlook
/schedule - Report timings""", chat_id)

                    elif text.lower() == "/schedule":
                        send_telegram("""*DAILY SCHEDULE (IST)*

8:15 AM - Pre-market battle plan
9:15 AM - Live market scan
10:15 AM - Live market scan
11:15 AM - Live market scan
12:15 PM - Live market scan
1:15 PM - Live market scan
2:15 PM - Live market scan
3:15 PM - Live market scan
6:00 PM - After market report
12:00 AM - Midnight global report

Type any stock name anytime for instant analysis.""", chat_id)

                    elif text.lower() == "/nifty":
                        send_telegram("Fetching top Nifty signals. Takes 2 minutes...", chat_id)
                        threading.Thread(target=run_quick_nifty, args=(chat_id,)).start()

                    elif text.lower() == "/breakout":
                        send_telegram("Scanning for breakouts...", chat_id)
                        threading.Thread(target=run_quick_breakout, args=(chat_id,)).start()

                    elif text.lower() == "/sectors":
                        send_telegram("Scanning sectors...", chat_id)
                        threading.Thread(target=run_quick_sectors, args=(chat_id,)).start()

                    elif text.lower() == "/help":
                        send_telegram("""*Commands*

Type any stock name for instant analysis.
/nifty - Top Nifty 50 signals
/breakout - BSE breakout stocks
/sectors - Sector wise outlook
/schedule - Daily report times
/start - Welcome message""", chat_id)

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
                rsi = float(live.get("rsi", 50))
                macd = live.get("macd", "Neutral")
                price = live.get("price", "N/A")
                change = live.get("change", "N/A")
                if rsi < 45 and macd == "Bullish":
                    buy_list.append(f"BUY *{stock}*\n   {price} ({change}) RSI:{rsi}")
                elif rsi > 65 and macd == "Bearish":
                    sell_list.append(f"SELL *{stock}*\n   {price} ({change}) RSI:{rsi}")
            time.sleep(2)
        except:
            time.sleep(1)

    msg = "*TOP BUY SIGNALS*\n"
    msg += "\n\n".join(buy_list[:5]) if buy_list else "No strong buy signals right now"
    if sell_list:
        msg += "\n\n*AVOID THESE*\n"
        msg += "\n\n".join(sell_list[:3])
    send_telegram(msg, chat_id)


def run_quick_breakout(chat_id):
    breakout_list = []
    for stock in NIFTY_50[:20]:
        try:
            live = get_live_stock_data(stock)
            if live.get("found"):
                change_str = live.get("change", "0%")
                change_val = float(change_str.replace("%", "").replace("+", ""))
                vol = live.get("volume_signal", "Normal")
                rsi = float(live.get("rsi", 50))
                if change_val > 2.0 or vol == "High" or rsi < 35:
                    breakout_list.append({
                        "stock": stock,
                        "price": live.get("price"),
                        "change": change_str,
                        "rsi": live.get("rsi"),
                        "macd": live.get("macd"),
                        "volume": vol
                    })
            time.sleep(2)
        except:
            time.sleep(1)

    if breakout_list:
        msg = "*BREAKOUT STOCKS*\n"
        for b in breakout_list[:8]:
            msg += f"\n*{b['stock']}*"
            msg += f"\n{b['price']} ({b['change']})"
            msg += f"\nRSI: {b['rsi']} | MACD: {b['macd']} | Vol: {b['volume']}\n"
    else:
        msg = "No major breakouts right now."
    send_telegram(msg, chat_id)


def run_quick_sectors(chat_id):
    for sector, stocks in SECTORS.items():
        gains = []
        losses = []
        bull_count = 0
        bear_count = 0
        for stock in stocks[:4]:
            try:
                live = get_live_stock_data(stock)
                if live.get("found"):
                    change = live.get("change", "0%")
                    val = float(change.replace("%", "").replace("+", ""))
                    if val > 0:
                        gains.append(f"{stock} {change}")
                        bull_count += 1
                    else:
                        losses.append(f"{stock} {change}")
                        bear_count += 1
                time.sleep(2)
            except:
                time.sleep(1)

        sentiment = "BULLISH" if bull_count > bear_count else ("BEARISH" if bear_count > bull_count else "NEUTRAL")
        msg = f"*{sector}* - {sentiment}\n"
        if gains:
            msg += "UP: " + " | ".join(gains[:3]) + "\n"
        if losses:
            msg += "DOWN: " + " | ".join(losses[:3])
        send_telegram(msg, chat_id)
        time.sleep(3)


def run_market_scan():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"*LIVE MARKET SCAN*\n{now}")
    run_quick_breakout(TELEGRAM_CHAT_ID)
    time.sleep(5)
    run_quick_nifty(TELEGRAM_CHAT_ID)
    send_telegram("Scan done. Next scan in 1 hour.\n\nType any stock name for instant analysis.")


def run_after_market():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    gainers = []
    losers = []
    for stock in NIFTY_50[:20]:
        try:
            live = get_live_stock_data(stock)
            if live.get("found"):
                change_str = live.get("change", "0%")
                val = float(change_str.replace("%", "").replace("+", ""))
                if val > 1.5:
                    gainers.append({"stock": stock, "change": change_str, "price": live.get("price")})
                elif val < -1.5:
                    losers.append({"stock": stock, "change": change_str, "price": live.get("price")})
            time.sleep(2)
        except:
            time.sleep(1)

    gainers.sort(key=lambda x: float(x["change"].replace("%","").replace("+","")), reverse=True)
    losers.sort(key=lambda x: float(x["change"].replace("%","").replace("+","")))

    report = f"*AFTER MARKET REPORT*\n{now}\n\n"
    report += "*TOP GAINERS TODAY*\n"
    for g in gainers[:5]:
        report += f"UP *{g['stock']}* {g['price']} ({g['change']})\n"
    report += "\n*TOP LOSERS TODAY*\n"
    for l in losers[:5]:
        report += f"DOWN *{l['stock']}* {l['price']} ({l['change']})\n"
    report += "\nNext: Midnight global report at 12 AM\n"
    report += "\nType any stock name for instant analysis anytime."
    send_telegram(report)


def run_midnight():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    prompt = """
    It is midnight India time. Search and give:
    US markets Dow NASDAQ SP500 closing today,
    SGX Nifty current direction, crude oil price, gold price, USD INR rate,
    top 3 global news affecting Indian markets tomorrow,
    top 5 Indian stocks likely to gap up tomorrow with reasons,
    top 5 Indian stocks likely to gap down tomorrow with reasons,
    expected Nifty opening tomorrow.
    Return ONLY JSON:
    {"dow":"text","nasdaq":"text","sp500":"text","sgx_nifty":"text","crude":"text","gold":"text","usdinr":"text","news":["n1","n2","n3"],"gap_up":[{"stock":"name","reason":"why"}],"gap_down":[{"stock":"name","reason":"why"}],"nifty_open":"text","verdict":"one line"}
    """
    result = call_gemini_with_retry(prompt)
    if result:
        report = f"*MIDNIGHT GLOBAL REPORT*\n{now}\n\n"
        report += f"Dow: {result.get('dow','N/A')}\n"
        report += f"NASDAQ: {result.get('nasdaq','N/A')}\n"
        report += f"S&P 500: {result.get('sp500','N/A')}\n"
        report += f"SGX Nifty: {result.get('sgx_nifty','N/A')}\n"
        report += f"Crude: {result.get('crude','N/A')}\n"
        report += f"Gold: {result.get('gold','N/A')}\n"
        report += f"USD/INR: {result.get('usdinr','N/A')}\n\n"
        report += "*NEWS*\n"
        for n in result.get("news", [])[:3]:
            report += f"- {n}\n"
        report += "\n*LIKELY GAP UP*\n"
        for s in result.get("gap_up", [])[:5]:
            report += f"UP *{s.get('stock')}* - {s.get('reason')}\n"
        report += "\n*LIKELY GAP DOWN*\n"
        for s in result.get("gap_down", [])[:5]:
            report += f"DOWN *{s.get('stock')}* - {s.get('reason')}\n"
        report += f"\nNifty Opening: *{result.get('nifty_open','N/A')}*"
        report += f"\n*{result.get('verdict','N/A')}*"
        report += "\n\nPre-market report at 8:15 AM"
        send_telegram(report)
    else:
        send_telegram(f"*MIDNIGHT REPORT*\n{now}\n\nCould not fetch global data. Check US markets on your own.\n\nPre-market report at 8:15 AM")


def run_premarket():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    influencer_names = ", ".join(INFLUENCERS)
    prompt = f"""
    BSE market opens in 1 hour at 9:15 AM IST. Search and give complete pre-market analysis.
    Search Gift Nifty, Twitter from {influencer_names}, BSE announcements, overnight global news.
    Return ONLY JSON:
    {{"gift_nifty":"text","opening":"Gap up/down XX points or Flat","stocks_in_focus":[{{"stock":"name","move":"expected move","action":"BUY/SELL/WAIT"}}],"top_3_trades":[{{"stock":"name","entry":"RXXX","target":"RXXX","stop":"RXXX","reason":"why"}}],"sectors_to_watch":["sector reason"],"avoid":["stock reason"],"verdict":"one line battle plan"}}
    """
    result = call_gemini_with_retry(prompt)
    if result:
        report = f"*PRE-MARKET BATTLE PLAN*\n{now}\n\n"
        report += f"Gift Nifty: {result.get('gift_nifty','N/A')}\n"
        report += f"Opening Expected: *{result.get('opening','N/A')}*\n\n"
        report += "*STOCKS IN FOCUS*\n"
        for s in result.get("stocks_in_focus", [])[:6]:
            report += f"*{s.get('stock')}* - {s.get('move')} | Action: {s.get('action')}\n"
        report += "\n*TOP 3 TRADES TODAY*\n"
        for i, t in enumerate(result.get("top_3_trades", [])[:3]):
            report += f"{i+1}. *{t.get('stock')}*\n   Entry: {t.get('entry')} | Target: {t.get('target')} | Stop: {t.get('stop')}\n   {t.get('reason')}\n"
        report += "\n*SECTORS TO WATCH*\n"
        for s in result.get("sectors_to_watch", [])[:3]:
            report += f"- {s}\n"
        report += "\n*AVOID TODAY*\n"
        for a in result.get("avoid", [])[:3]:
            report += f"- {a}\n"
        report += f"\n*BATTLE PLAN*\n{result.get('verdict','N/A')}"
        report += "\n\nMarket opens at 9:15 AM. Good luck!"
        send_telegram(report)
    else:
        send_telegram(f"*PRE-MARKET*\n{now}\n\nCould not fetch pre-market data.\nCheck Gift Nifty manually.\n\nMarket opens at 9:15 AM")


# ─────────────────────────────────────────────
# FIX 4 (CRITICAL): Run every scheduled job in a
#         background thread so the main scheduler
#         loop NEVER blocks. This is the root cause
#         of missed and delayed reports.
# ─────────────────────────────────────────────
def in_thread(func):
    """Wraps a function so it runs in a daemon thread when called by scheduler."""
    def wrapper():
        t = threading.Thread(target=func, daemon=True)
        t.start()
    return wrapper


# SCHEDULE IN IST (TZ=Asia/Kolkata set in Railway)
schedule.every().day.at("09:15").do(in_thread(run_market_scan))
schedule.every().day.at("10:15").do(in_thread(run_market_scan))
schedule.every().day.at("11:15").do(in_thread(run_market_scan))
schedule.every().day.at("12:15").do(in_thread(run_market_scan))
schedule.every().day.at("13:15").do(in_thread(run_market_scan))
schedule.every().day.at("14:15").do(in_thread(run_market_scan))
schedule.every().day.at("15:15").do(in_thread(run_market_scan))
schedule.every().day.at("18:00").do(in_thread(run_after_market))
schedule.every().day.at("00:00").do(in_thread(run_midnight))
schedule.every().day.at("08:15").do(in_thread(run_premarket))

# START LISTENER
listener_thread = threading.Thread(target=listen_for_commands, daemon=True)
listener_thread.start()

print("BSE Agent started. All bugs fixed.")
print("Scheduled jobs now run in background threads. No more missed reports.")

send_telegram("""*BSE AI AGENT - FIXED VERSION*

All bugs resolved.

Scheduled reports fire on time (thread fix)
52-week high/low now uses real 1-year data
Long messages split automatically
RSI and MACD NaN values handled
Telegram errors now logged properly

Type any stock name to test.
Example: Reliance Industries""")

# ─────────────────────────────────────────────
# FIX 5: Reduced sleep from 60s to 30s so jobs
#         fire within 30 seconds of their scheduled
#         time instead of up to 60 seconds late
# ─────────────────────────────────────────────
while True:
    schedule.run_pending()
    time.sleep(30)
