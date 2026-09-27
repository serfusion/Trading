import json
import ollama
from pydantic import BaseModel, ValidationError
from google import genai

class TradeSignal(BaseModel):
    direction: str          # "LONG" | "SHORT" | "NO_TRADE"
    confidence: float       # 0.0 - 1.0
    reasoning: str
    matched_strategy: str
    invalidation_price: float | None = None
    news_veto: bool

SYSTEM_PROMPT = """You are a signal-generation assistant for XAUUSD. You must ONLY use the
strategy rules provided in the context block below — never invent your own trading logic.
If the market snapshot doesn't clearly match any provided rule, output NO_TRADE.
Respond with ONLY a JSON object matching this schema, no prose, no markdown fences:
{"direction": "LONG|SHORT|NO_TRADE", "confidence": 0.0-1.0, "reasoning": "...",
 "matched_strategy": "...", "invalidation_price": number or null, "news_veto": true|false}"""

class SignalEngine:
    def __init__(self, gemini_api_key: str | None = None):
        self.gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

    def generate(
        self, market_snapshot: dict, strategy_rules: list[str],
        news_events: list[dict], headlines: list[str],
    ) -> TradeSignal | None:
        context = self._build_context(market_snapshot, strategy_rules, news_events, headlines)
        raw = self._call_local(context)
        signal = self._parse(raw)
        if signal is None:
            return None
        if signal.confidence >= 0.7 and self.gemini_client:
            confirmed = self._confirm_with_cloud(context, signal)
            if not confirmed:
                signal.direction = "NO_TRADE"
                signal.reasoning += " | Cloud confirmation disagreed — downgraded to NO_TRADE."
        return signal

    def _call_local(self, context: str) -> str:
        response = ollama.chat(
            model="qwen3:4b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            options={"temperature": 0.2},
            think=False,
        )
        return response["message"]["content"]

    def _confirm_with_cloud(self, context: str, draft_signal: TradeSignal) -> bool:
        prompt = (
            f"{SYSTEM_PROMPT}\n\nA local model produced this draft signal:\n"
            f"{draft_signal.model_dump_json()}\n\nContext it used:\n{context}\n\n"
            "Do you agree with this direction given the same strategy rules and context? "
            "Respond with only the word AGREE or DISAGREE."
        )
        result = self.gemini_client.models.generate_content(
            model="gemini-3.5-flash-lite", contents=prompt
        )
        return "AGREE" in result.text.upper()

    @staticmethod
    def _parse(raw: str) -> TradeSignal | None:
        try:
            cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
            return TradeSignal(**json.loads(cleaned))
        except (json.JSONDecodeError, ValidationError):
            return None

    @staticmethod
    def _build_context(snapshot, rules, news_events, headlines) -> str:
        rules_block = "\n---\n".join(rules)
        news_block = "\n".join(
            f"- {e.get('event', 'unknown')} at {e.get('time', 'unknown')}" for e in news_events
        ) or "No high-impact USD events in window."
        headlines_block = "\n".join(f"- {h}" for h in headlines) or "No relevant headlines."
        return (
            f"STRATEGY RULES (use only these):\n{rules_block}\n\n"
            f"MARKET SNAPSHOT:\n{json.dumps(snapshot, indent=2)}\n\n"
            f"UPCOMING HIGH-IMPACT NEWS:\n{news_block}\n\n"
            f"RECENT HEADLINES:\n{headlines_block}"
        )

