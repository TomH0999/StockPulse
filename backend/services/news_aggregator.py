import yfinance as yf
from datetime import datetime
from schemas import NewsItem

def analyze_sentiment(text: str) -> str:
    text_lower = text.lower()
    
    bullish_words = ['surge', 'jump', 'gain', 'beat', 'up', 'soar', 'buy', 'growth', 'record', 'high', 'rally']
    bearish_words = ['plunge', 'drop', 'miss', 'down', 'crash', 'sell', 'loss', 'decline', 'lawsuit', 'fear', 'low']
    
    bullish_score = sum(1 for w in bullish_words if w in text_lower)
    bearish_score = sum(1 for w in bearish_words if w in text_lower)
    
    if bullish_score > bearish_score:
        return "Buy"
    elif bearish_score > bullish_score:
        return "Sell"
    else:
        return "Hold"

def fetch_news(symbol: str) -> list[NewsItem]:
    try:
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news
        
        if not raw_news:
            return []
            
        news_items = []
        for item in raw_news:
            title = item.get("title", "No Title")
            publisher = item.get("publisher", "Unknown Source")
            link = item.get("link", "")
            provider_publish_time = item.get("providerPublishTime", 0)
            
            if provider_publish_time:
                pub_date = datetime.utcfromtimestamp(provider_publish_time).isoformat() + "Z"
            else:
                pub_date = datetime.utcnow().isoformat() + "Z"
                
            sentiment = analyze_sentiment(title)

            news_items.append(NewsItem(
                headline=title,
                summary=item.get("type", "Article"),
                url=link,
                source=publisher,
                published_at=pub_date,
                sentiment=sentiment
            ))
            
        return news_items
    except Exception as e:
        print(f"Error fetching news for {symbol}: {e}")
        return []