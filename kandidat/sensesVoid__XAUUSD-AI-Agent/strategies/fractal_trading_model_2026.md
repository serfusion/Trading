# TTrades Fractal Trading Model (2026 Strategy Framework)

> **Source:** TTrades YouTube Channel — *[The Only Trading Strategy You Need For 2026](http://www.youtube.com/watch?v=9AL41xON3hA)*

---

## 1. Executive Summary & Core Philosophy
The **TTrades Fractal Model** is an ICT-inspired mechanical framework built on a foundational market premise: **Price cannot reverse without forming a swing point.** 

To avoid bouncing between strategy models, this framework provides a structured multi-timeframe alignment process to systematically identify high-probability expansion candles by leveraging:
1. **Daily Bias** via daily candle closures.
2. **Structural POIs (Points of Interest)** on higher/intermediate timeframes.
3. **Change in State of Delivery (CSD)** and **Continuation Order Blocks (COB)** for execution on lower timeframes.

---

## 2. The Core Mechanics & Terminology

### A. Daily Bias Determination
Daily direction is established strictly using the prior day's daily candle closure:

| Bias Type | Daily Candle Pattern / Closure | Expected Next Day Action |
| :--- | :--- | :--- |
| **Bullish Continuation** | Closes ABOVE the previous day's high (PDH) | Continued expansion higher |
| **Bearish Continuation** | Closes BELOW the previous day's low (PDL) | Continued expansion lower |
| **Bullish Reversal** | Sweeps below PDL, but closes BACK ABOVE that low | Expansion higher (reversal off low) |
| **Bearish Reversal** | Sweeps above PDH, but closes BACK BELOW that high | Expansion lower (reversal off high) |

---

### B. Points of Interest (POIs)
Points of Interest are defined within the previous day's/range's structure:
* **Bullish POI:** Fair Value Gap (FVG) or prior key swing low.
* **Bearish POI:** Fair Value Gap (FVG) or prior key swing high.

---

### C. Candle Closures (Confirmation Types)
* **Candle 2 Closure:** Reversal or reaction candle closing back inside/in favor of the direction.
* **Candle 3 Closure:** Confirmation candle establishing the swing point after reaching the POI.

---

## 3. Multi-Timeframe Pairing Framework (Fractal Nature)

The model scales across multiple timeframe tiers depending on trader preference and market structure:

```
+-----------------------------------------------------------------------+
|                        TIMEFRAME ALIGNMENT                            |
+--------------------------+--------------------+-----------------------+
| Higher Timeframe (Bias)  | Intermediate (POI) | Lower Timeframe (Entry)|
+--------------------------+--------------------+-----------------------+
| Monthly / Weekly         | Daily              | 1-Hour                |
| Daily                    | 1-Hour / 30-Min    | 5-Minute / 3-Minute   |
| 1-Hour                   | 15-Minute          | 1-Minute              |
+--------------------------+--------------------+-----------------------+
```

---

## 4. Execution Rules & Entry Process

### Step 1: Confirm High-Timeframe Bias & POI
1. Identify Daily Bias (e.g., Bullish Continuation or Bearish Reversal).
2. Mark out the key POI (FVG or Swing Point) on the intermediate timeframe.
3. Wait for price to reach the POI and form a **Candle 2 or Candle 3 closure**.

### Step 2: Validate Swing Point via CSD
* Confirm a **Change in State of Delivery (CSD)** on the entry/structure timeframe (e.g., closing through a series of up-close/down-close candles after sweeping liquidity).
* **Crucial Rule:** Do NOT enter immediately on the first CSD. Wait for a continuation confirmation.

### Step 3: Enter via Continuation Order Block (COB)
1. Wait for price to form a **Continuation Order Block (COB)** on the lower timeframe.
2. **Entry Point:** Enter on the candle closure through the series of candles, or on a direct retest of the COB / FVG.
3. **Stop Loss (SL):** Placed at the protected swing high/low or candle body high/low.
4. **Take Profit (TP):** 
   * **Base Target:** Standard **2.0 R** (2:1 Risk-to-Reward).
   * **Extended HTF Target:** Draw-on-liquidity (Previous Day High/Low, HTF FVG, or Equal Highs/Lows).

---

## 5. Walkthrough Examples

### Example 1: Daily/Hourly/5m Bearish Reversal Setup
1. **Daily:** Price takes out previous highs, then forms a bearish reversal closure (closes back under previous high). Bias = Bearish.
2. **Hourly (Intermediate):** Price experiences a CSD and forms an hourly FVG retest.
3. **5-Minute (Entry):** 
   * Sweeps a short-term high into the hourly FVG.
   * Closes below down-close candles to confirm a 5m COB.
   * Entry taken on retest, SL above the body/high, target set to 2R or the Daily FVG below (PDL).

### Example 2: Monthly/Daily/1-Hour Macro Alignment (USD/JPY)
1. **Monthly:** Monthly candle forms a Candle 2 closure bullish in an FVG.
2. **Daily:** Price respects the daily FVG and closes back above.
3. **1-Hour (Entry):** Price consolidates, sweeps a short-term low, and closes above down-close candles forming an 1h COB. Entry on retest targeting equal highs for 2R+.

---

## 6. Invalidations & Edge Cases (Consolidation Handling)

* **Failed Continuations:** If price repeatedly fails to close through down-close/up-close candles inside a POI, **do not force a trade**. The market is in a consolidation/range.
* **Range Protocol:** Wait for one side of the consolidation range (e.g., Previous Day High/Low) to be swept first. Only enter after a clear V-shaped reversal and a subsequent CSD/COB on the lower timeframe.

---

## 7. Key RAG Retrieval Tags
`#TTrades` `#FractalModel` `#DailyBias` `#ChangeInStateOfDelivery` `#ContinuationOrderBlock` `#FairValueGap` `#RiskToReward` `#PriceAction` `#ICT`