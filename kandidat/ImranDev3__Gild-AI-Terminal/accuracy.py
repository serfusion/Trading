def analyze_gold_accuracy(rates):
    # ক্লোজ প্রাইস লিস্ট
    close_prices = [x[4] for x in rates]
    last_price = close_prices[-1]
    
    # SMA 20 ক্যালকুলেশন
    sma_20 = sum(close_prices[-20:]) / 20 if len(close_prices) >= 20 else last_price
    
    signal = "অপেক্ষা করুন"
    if last_price > sma_20:
        signal = "এখনই কিনুন (BUY)"
    elif last_price < sma_20:
        signal = "এখনই বিক্রি করুন (SELL)"
        
    return {
        "price": round(last_price, 2),
        "signal": signal,
        "trend": "মার্কেট উপরে যাচ্ছে" if last_price > sma_20 else "মার্কেট নিচে নামছে"
    }