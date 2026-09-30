from services.news_aggregator import fetch_news

def evaluate_portfolio_sentiment(assets: list) -> dict:
    if not assets:
        return {"overall": "Neutral", "score": 0, "details": {}}

    total_score = 0
    asset_details = {}

    for asset in assets:
        if asset.quantity <= 0:
            continue
            
        news_items = fetch_news(asset.symbol)
        asset_score = 0
        
        for item in news_items:
            if item.sentiment == "Buy":
                asset_score += 1
            elif item.sentiment == "Sell":
                asset_score -= 1
                
        normalized_score = asset_score / len(news_items) if news_items else 0
        total_score += normalized_score
        
        if normalized_score > 0.3:
            asset_status = "Bullish"
        elif normalized_score < -0.3:
            asset_status = "Bearish"
        else:
            asset_status = "Neutral"
            
        asset_details[asset.symbol] = {
            "sentiment": asset_status,
            "raw_score": round(normalized_score, 2),
            "articles_analyzed": len(news_items)
        }
        
    avg_score = total_score / len(asset_details) if asset_details else 0
    
    if avg_score > 0.2:
        overall = "Bullish"
    elif avg_score < -0.2:
        overall = "Bearish"
    else:
        overall = "Neutral"
        
    return {
        "overall": overall,
        "score": round(avg_score, 2),
        "details": asset_details
    }