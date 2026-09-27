# XAUUSD AI Trading Signal Pipeline

An AI-assisted, RAG-gated signal generator for XAUUSD, built for local-first operation on an
Acer Aspire 7 (16GB RAM, RTX 3050 Ti 4GB VRAM) with $0 recurring cost. Generates trade signals
from live MT5 data, your own strategy documents, and current news — but never places an order
without explicit human approval.

## What this is (and isn't)

**Is:** a signal-generation and risk-calculation pipeline. It reads the market, matches conditions
against strategy rules you wrote, and produces an exact entry/SL/TP/lot-size plan.

**Isn't:** an autonomous trading bot. No component in this system calls `mt5.order_send()` on its
own. Every order requires you to run `approve_trade.py` and type `y`.

---

## Architecture

```
MT5 (live data) ─┐
                  ├─▶ Market snapshot ─┐
News/Calendar ────┘                    │
                                        ├─▶ RAG-retrieved strategy rules ─▶ LLM signal engine
Your strategy .md files ───────────────┘         (qwen3:4b local, Gemini confirms)
                                                              │
                                                              ▼
                                                   Risk Manager (deterministic —
                                                   entry/SL/TP/lot-size, 1% risk, 2:1 R:R)
                                                              │
                                                              ▼
                                                   latest_signal.json (pending)
                                                              │
                                                              ▼
                                          approve_trade.py — YOU decide, y/N
                                                              │
                                                              ▼
                                             trade_executor.py — places the order
```

The reasoning layer (LLM) and the execution layer (order placement) are deliberately separate.
The AI proposes; a human, plus deterministic risk math, disposes.

---

## Project structure

```
xauusd_ai_pipeline/
├── venv/
├── strategies/                  # your strategy docs, one .md per strategy
│   ├── avocl_gold_strategy.md
│   └── msnr_crt_tbs.md
├── strategy_db/                 # auto-created by chromadb — don't edit manually
├── mt5_bridge.py                 # MT5 connection, OHLC + tick data
├── data_pipeline.py              # raw OHLC → compact feature snapshot
├── news_fetcher.py                # ForexFactory calendar + Finnhub headlines
├── strategy_rag.py                # chunk, embed, and retrieve strategy rules
├── signal_engine.py               # local LLM draft + cloud confirmation
├── risk_manager.py                # entry/SL/TP/lot-size calculation
├── trade_executor.py              # deterministic MT5 order placement
├── ingest_strategies.py           # one-time/occasional: load strategies/*.md into RAG
├── main.py                        # orchestrator loop — runs every 15 minutes
├── approve_trade.py               # run manually — review + approve/reject the pending signal
├── .env                            # credentials, never commit this
├── pipeline.log                    # full run history
├── latest_signal.json              # most recent signal + execution plan
└── trade_history.jsonl             # append-only log of every approve/reject decision
```

---

## Setup

### 1. Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install MetaTrader5 pandas numpy chromadb sentence-transformers ollama google-genai pydantic python-dotenv apscheduler requests
```

### 2. Local models (Ollama)

```powershell
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

### 3. `.env`

Quote every value. Use the exact terminal path from your MT5 shortcut's Properties → Target,
and the exact server name from the terminal's login dropdown — don't retype either from memory.

```
MT5_LOGIN=12345678
MT5_PASSWORD="YourActualPassword"
MT5_SERVER="ExactServerName-Demo"
MT5_PATH="C:\Program Files\YourBrokerMT5\terminal64.exe"
GEMINI_API_KEY="your_key"
FINNHUB_API_KEY="your_key"
```

### 4. Ingest your strategies

Write one `.md` file per strategy in `strategies/`, one rule/condition per markdown header
(`### Entry: bullish AVOCL reclaim`, `### Invalidation`, etc.) so retrieval can match against
atomic rules rather than long paragraphs. Then:

```powershell
python ingest_strategies.py
```

Re-run this any time you edit a strategy file — ingestion uses `upsert`, so it's always safe to
re-run without creating duplicates.

---

## Running it

**Start the signal-generation loop** (background, generates a signal every 15 minutes, never
trades):

```powershell
python main.py
```

Watch `pipeline.log` or the console for each cycle's output. Check `latest_signal.json` for the
current signal and, if one was produced, its full execution plan.

**Review and act on a signal** (run on demand, in a separate terminal, whenever you want):

```powershell
python approve_trade.py
```

This shows you the pending signal, flags if it's gone stale (>5 min old) or if price has drifted
from the generation-time entry, and asks for explicit `y` confirmation before sending anything
to the broker. Reject with anything else, including just Enter.

---

## Risk model

- **Risk per trade:** 1% of account balance
- **Reward:Risk:** fixed 2:1 — take-profit is mechanically derived as 2× the stop-loss distance,
  never negotiated by the LLM
- **Stop-loss source:** the AI's `invalidation_price` is used *only* if it's on the correct side
  of entry and respects the broker's minimum stop distance; otherwise falls back to an
  ATR-based stop (1.2× ATR14)
- **Lot size:** computed from account balance, SL distance, and the symbol's actual
  `trade_tick_value`/`trade_tick_size` — never a fixed or guessed lot size

None of this math is done by the LLM. `risk_manager.py` is plain deterministic Python specifically
so the risk on every trade is exact and auditable.

---

## Safety notes

- **News veto is hardcoded**, not LLM-judged: if a high-impact USD event falls inside the next
  cycle's window, the cycle is skipped outright.
- **Cloud confirmation degrades gracefully.** If Gemini is unreachable, rate-limited, or the model
  name goes stale (Google has retired several Gemini model generations in 2026 — check
  [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) if you see
  a 404), the pipeline falls back to trusting the local signal rather than crashing.
- **Never let `approve_trade.py` become a rubber stamp.** The stale-signal and price-drift
  warnings exist because the plan you're approving was calculated at generation time, not the
  moment you press `y`. Read them.
- **Run on a demo account for 2–4 weeks minimum** before ever pointing this at a live account,
  and log every signal against what price actually did afterward.

---

## Troubleshooting quick reference

| Symptom | Likely cause |
|---|---|
| `MT5 initialize/login failed: (-6, ...)` | Wrong server name, or `.env` password truncated by an unquoted `#`/space |
| `IPC initialize failed, Process create failed` | `MT5_PATH` malformed — check for stray `r"..."` syntax or unescaped `\t`-style sequences from double-quoting |
| `models/gemini-X is no longer available` | Google retired that model generation — check current model names at ai.google.dev |
| Finnhub `403 Forbidden` | Endpoint moved behind a paid plan — economic calendar now uses the free ForexFactory feed instead |
| `DLL load failed ... Application Control policy` | Windows Smart App Control blocking a compiled dependency — see setup notes on disabling it |