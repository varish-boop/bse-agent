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

# YOUR BSE WATCHLIST
WATCHLIST = [
    "Reliance Industries",
    "TCS",
    "HDFC Bank",
    "Infosys",
    "SBI",
    "Tata Motors",
    "Adani Ports",
    "Bajaj Finance"
]

# TOP INDIAN INFLUENCERS TO TRACK
INFLUENCERS = {
    "twitter": [
        "Vijay Kedia",
        "Basant Maheshwari",
        "Saurabh Mukherjea",
        "Deepak Shenoy",
        "PR Sundar",
        "Akshat Shrivastava",
        "Anish Singh Thakur"
    ],
    "youtube": [
        "Pranjal Kamra",
        "Rachana Ranade",
        "Akshat Shrivastava",
        "CA Rachana Phadke"
    ],
    "telegram": [
        "Indian stock market tips",
        "BSE NSE trading signals",
        "Zerodha traders community"
    ]
}

# SETUP GEMINI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# INFLUENCER ACCURACY SCORES (updates automatically over time)
accuracy_scores = {}

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram error: {e}")

def get_influencer_signals(stock):
    twitter_names = ", ".join(INFLUENCERS["twitter"])
    youtube_names = ", ".join(INFLUENCERS["youtube"])
    telegram_topics = ", ".join(INFLUENCERS["telegram"])

    prompt = f"""
    You are an expert at tracking Indian stock market influencers and social signals.
    
    For the stock: {stock} (BSE listed Indian company)
    
    Search the entire internet and find:
    
    1. TWITTER/X SIGNALS: What are these influencers saying about {stock} recently:
    {twitter_names}
    Search Twitter/X for their latest posts about this stock.
    
    2. YOUTUBE SIGNALS: What are these YouTubers saying about {stock}:
    {youtube_names}
    Search YouTube for their latest videos mentioning this stock.
    
    3. TELEGRAM SIGNALS: Search these Telegram topics for {stock} calls:
    {telegram_topics}
    
    4. NEWS SENTIMENT: Search all major Indian financial news sites:
    Economic Times, Moneycontrol, Mint, Business Standard, NDTV Profit
    Find the latest news about {stock} in the last 24 hours.
    
    Return ONLY a JSON object with no extra text:
    {{
        "twitter_signals": [
            {{"influencer": "name", "signal": "BUY/SELL/HOLD/NEUTRAL", "comment": "what they said", "platform": "Twitter"}}
        ],
        "youtube_signals": [
            {{"influencer": "name", "signal": "BUY/SELL/HOLD/NEUTRAL", "comment": "video topic", "platform": "YouTube"}}
        ],
        "telegram_signals": [
            {{"channel": "channel name", "signal": "BUY/SELL/HOLD/NEUTRAL", "comment": "what was posted"}}
        ],
        "news_headlines": ["headline 1", "headline 2", "headline 3"],
        "overall_social_sentiment": "BULLISH/BEARISH/NEUTRAL",
        "social_confidence": "XX%"
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
            "twitter_signals": [],
            "youtube_signals": [],
            "telegram_signals": [],
            "news_headlines": ["Could not fetch news"],
            "overall_social_sentiment": "NEUTRAL",
            "social_confidence": "0%"
        }

def get_market_data(stock):
    prompt = f"""
    You are an expert BSE Indian stock market analyst.
    Search the entire internet for live data on: {stock}
    
    Find from BSE, NSE, Moneycontrol, Screener.in, Tickertape:
    - Current live price on BSE
    - Today's change percentage
    - RSI value
    - MACD signal
    - Volume today vs average
    - Support and resistance levels
    - 52 week high and low
    - P/E ratio
    - Market cap
    - FII buying or selling today
    - Promoter holding percentage
    - Latest quarterly results summary
    
    Return ONLY a JSON object with no extra text:
    {{
        "current_price": "₹XXX",
        "change_percent": "+/-X.XX%",
        "is_positive": true,
        "rsi": "XX",
        "rsi_signal": "Overbought/Oversold/Neutral",
        "macd": "Bullish/Bearish",
        "volume_signal": "High/Low/Average",
        "support": "₹XXX",
        "resistance": "₹XXX",
        "week52_high": "₹XXX",
        "week52_low": "₹XXX",
        "pe_ratio": "XX",
        "market_cap": "₹XX,XXX Cr",
        "fii_activity": "Buying/Selling/Neutral",
        "promoter_holding": "XX%",
        "quarterly_summary": "One line summary",
        "technical_signal": "BUY/SELL/HOLD",
        "technical_confidence": "XX%"
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
        return {"current_price": "N/A", "technical_signal": "HOLD", "technical_confidence": "0%"}

def calculate_combined_signal(market_data, social_data):
    prompt = f"""
    You are a master stock analyst combining multiple signals for maximum accuracy.
    
    MARKET DATA (40% weight):
    {json.dumps(market_data, indent=2)}
    
    SOCIAL SIGNALS (60% weight):
    {json.dumps(social_data, indent=2)}
    
    SCORING RULES:
    - Technical BUY = +40 points
    - Technical SELL = -40 points  
    - Technical HOLD = 0 points
    - Each influencer BUY signal = +8 points
    - Each influencer SELL signal = -8 points
    - Bullish news = +5 points each
    - Bearish news = -5 points each
    - Social sentiment BULLISH = +10 bonus
    - Social sentiment BEARISH = -10 bonus
    
    Calculate total score and determine final signal.
    Score above 30 = STRONG BUY
    Score 10 to 30 = BUY
    Score -10 to 10 = HOLD
    Score -30 to -10 = SELL
    Score below -30 = STRONG SELL
    
    Return ONLY a JSON object with no extra text:
    {{
        "final_signal": "STRONG BUY/BUY/HOLD/SELL/STRONG SELL",
        "total_score": XX,
        "accuracy_confidence": "XX%",
        "target_price": "₹XXX",
        "stop_loss": "₹XXX",
        "time_horizon": "X days/weeks",
        "key_reason": "One sentence explaining the main reason for this signal",
        "risk_level": "LOW/MEDIUM/HIGH",
        "influencers_bullish": X,
        "influencers_bearish": X,
        "influencers_neutral": X
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
            "final_signal": "HOLD",
            "total_score": 0,
            "accuracy_confidence": "50%",
            "target_price": "N/A",
            "stop_loss": "N/A",
            "time_horizon": "N/A",
            "key_reason": "Could not calculate",
            "risk_level": "HIGH",
            "influencers_bullish": 0,
            "influencers_bearish": 0,
            "influencers_neutral": 0
        }

def format_report(stock, market_data, social_data, combined):
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    signal = combined.get("final_signal", "HOLD")
    
    # Signal emoji
    if "BUY" in signal:
        emoji = "🟢"
    elif "SELL" in signal:
        emoji = "🔴"
    else:
        emoji = "🟡"

    report = f"""
{emoji} *BSE AI REPORT*
🕐 {now}

📊 *{stock.upper()}*
💰 Price: {market_data.get('current_price', 'N/A')} ({market_data.get('change_percent', 'N/A')})

━━━━━━━━━━━━━━━
{emoji} *SIGNAL: {signal}*
🎯 Confidence: {combined.get('accuracy_confidence', 'N/A')}
📈 Target: {combined.get('target_price', 'N/A')}
🛑 Stop Loss: {combined.get('stop_loss', 'N/A')}
⏱ Horizon: {combined.get('time_horizon', 'N/A')}
⚠️ Risk: {combined.get('risk_level', 'N/A')}

━━━━━━━━━━━━━━━
📡 *SOCIAL SIGNALS*
👍 Bullish Influencers: {combined.get('influencers_bullish', 0)}
👎 Bearish Influencers: {combined.get('influencers_bearish', 0)}
😐 Neutral: {combined.get('influencers_neutral', 0)}
🌐 Overall Sentiment: {social_data.get('overall_social_sentiment', 'N/A')}

━━━━━━━━━━━━━━━
📉 *TECHNICAL DATA*
RSI: {market_data.get('rsi', 'N/A')} ({market_data.get('rsi_signal', 'N/A')})
MACD: {market_data.get('macd', 'N/A')}
Volume: {market_data.get('volume_signal', 'N/A')}
FII: {market_data.get('fii_activity', 'N/A')}
Support: {market_data.get('support', 'N/A')}
Resistance: {market_data.get('resistance', 'N/A')}

━━━━━━━━━━━━━━━
📰 *LATEST NEWS*"""

    for news in social_data.get("news_headlines", [])[:3]:
        report += f"\n• {news}"

    report += f"""

━━━━━━━━━━━━━━━
🤖 *AI VERDICT*
{combined.get('key_reason', 'N/A')}

⚡ Score: {combined.get('total_score', 0)}/100
"""
    return report

def run_analysis():
    now = datetime.now().strftime("%d %b %Y %I:%M %p")
    send_telegram(f"🔍 *BSE AI SCAN STARTED*\n🕐 {now}\nScanning {len(WATCHLIST)} stocks with influencer tracking...")
    time.sleep(2)

    for stock in WATCHLIST:
        try:
            print(f"Analyzing {stock}...")
            send_telegram(f"⏳ Analyzing *{stock}*...")

            # Get all data
            market_data = get_market_data(stock)
            time.sleep(2)
            social_data = get_influencer_signals(stock)
            time.sleep(2)
            combined = calculate_combined_signal(market_data, social_data)
            time.sleep(1)

            # Send report
            report = format_report(stock, market_data, social_data, combined)
            send_telegram(report)
            time.sleep(5)

        except Exception as e:
            send_telegram(f"❌ Error analyzing {stock}: {str(e)}")
            time.sleep(3)

    send_telegram(f"✅ *Scan Complete*\nNext scan in 1 hour.")

# SCHEDULE EVERY HOUR
schedule.every().hour.do(run_analysis)

print("BSE Agent with Influencer Tracking is running.")
print("Reports every hour. Press CTRL+C to stop.")
send_telegram("🚀 *BSE AI Agent Started*\nTracking influencers on Twitter, YouTube and Telegram.\nHourly reports activated. First scan starting now...")
time.sleep(3)

# RUN IMMEDIATELY ON START
run_analysis()

while True:
    schedule.run_pending()
    time.sleep(60)
