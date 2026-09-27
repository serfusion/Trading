import requests
from datetime import datetime, timedelta

class NewsFetcher:
    FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    FINNHUB_URL = "https://finnhub.io/api/v1"

    def __init__(self, finnhub_api_key: str):
        self.finnhub_api_key = finnhub_api_key

    def get_upcoming_high_impact_events(self, hours_ahead: int = 1) -> list[dict]:
        try:
            resp = requests.get(self.FF_CALENDAR_URL, timeout=10)
            resp.raise_for_status()
            events = resp.json()
        except requests.RequestException as e:
            # Don't crash the trading cycle over a calendar fetch failure —
            # treat "can't confirm it's safe" the same as "high-impact event nearby"
            print(f"Calendar fetch failed, defaulting to cautious mode: {e}")
            return [{"event": "UNKNOWN — calendar unavailable", "impact": "high"}]

        now = datetime.utcnow()
        window_end = now + timedelta(hours=hours_ahead)
        relevant = []
        for e in events:
            if e.get("country") != "USD" or e.get("impact") != "High":
                continue
            try:
                event_time = datetime.strptime(e["date"], "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None)
            except (KeyError, ValueError):
                continue
            if now <= event_time <= window_end:
                relevant.append({"event": e.get("title", "unknown"), "time": e["date"]})
        return relevant

    def get_gold_headlines(self, limit: int = 5) -> list[str]:
        try:
            resp = requests.get(
                f"{self.FINNHUB_URL}/news",
                params={"category": "forex", "token": self.finnhub_api_key},
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Headline fetch failed, continuing without news context: {e}")
            return []

        items = resp.json()
        keywords = ("gold", "xau", "fed", "fomc", "cpi", "nfp", "dollar")
        matches = [
            it["headline"] for it in items
            if any(k in it.get("headline", "").lower() for k in keywords)
        ]
        return matches[:limit]