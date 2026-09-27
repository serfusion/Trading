# 🛡️ XAU/USD Gold Blueprint: Institutional Logic Engine

![Dashboard Preview](https://img.shields.io/badge/Status-Field%20Ready-success?style=for-the-badge) ![React](https://img.shields.io/badge/React_19-20232A?style=for-the-badge&logo=react&logoColor=61DAFB) ![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white) 

An enterprise-grade, standalone algorithmic trading dashboard specifically engineered for the XAU/USD (Gold) market. This platform completely bypasses external script engines like TradingView's PineScript by running complex Smart Money Concept (SMC) mathematics locally in the browser securely against a live institutional data feed.

---

## 📖 Core Architecture

1. **The Brain (Zustand & LogicCore.ts):** A custom TypeScript algorithmic engine capable of parsing thousands of OHLCV ticks to programmatically identify:
   - 200-Period Exponential Moving Average (EMA) for Macro Bias.
   - Market Structure Shifts (BOS / CHOCH).
   - Institutional Order Blocks (OB) and Fair Value Gaps (FVG).
   - Inducement (IDM) Liquidity Sweeps.
2. **The Data Pipe (Twelve Data WebSocket):** An autonomous data service that seamlessly bootstraps 150 historical 15M candles via REST, and seamlessly stitches them into a live TCP WebSocket stream for zero-latency tick updates.
3. **The Canvas (TradingView Lightweight Charts):** A fully interactive, hardware-accelerated charting SDK. Custom SMC algorithmic markers and animated Buy/Sell signals are systematically rendered natively onto the candlesticks.

---

## ✨ Features

- **Live Institutional Streaming:** Millisecond-accurate market updates powering all mathematical models without triggering heavy React DOM re-renders.
- **Dynamic Trade Fortress:** Calculate compounding lot sizing in real-time based on absolute risk percentage parameters and your maximum daily drawdown thresholds.
- **SMC Canvas Overlays:** Fully automated price lines highlighting institutional data tracking (FVG limits, active OB blocks, Break of Structure lines).
- **News Shield & Killzone Protocol:** Protective wrappers that identify highly volatile macro-economic news schedules and dangerous off-session low-liquidity zones.

---

## 🚀 Local Development (Quick Start)

### 1. Prerequisites
- Node.js (v18 or higher)
- NPM or Yarn
- A Twelve Data API Key (You can get a free one [here](https://twelvedata.com/))

### 2. Secure Environment
Clone the repository, then create a secure `.env.local` file in the root directory:
```env
VITE_TWELVEDATA_API_KEY=your_api_key_here
```

### 3. Install & Ignite
```bash
npm install
npm run dev
```
Navigate to `http://localhost:3000`. The engine will bootstrap the history, connect the WebSocket, and the chart will immediately begin tracking live order flow.

---

## 🌐 Production Deployment

Because this engine is built as a pure, static Client-Side App using Vite, deployment is incredibly fast and cheap.

### One-Click Vercel Deployment (Recommended)
1. Push your local codebase to a private secure GitHub repository.
2. Log into [Vercel](https://vercel.com/) and click **Add New Project**.
3. Import your GitHub repository.
4. Open the **Environment Variables** tab and add:
   - Key: `VITE_TWELVEDATA_API_KEY`
   - Value: `your_api_key_here`
5. Click **Deploy**. Vercel will automatically detect Vite, run `npm run build`, and issue you a live SSL-secured production URL instantly.

### Netlify Deployment
1. Import the repository into Netlify.
2. Set the Build Command to `npm run build`.
3. Set the Publish Directory to `dist`.
4. Inject your API Key into the Netlify Environment Variables.
5. Deploy.

---

## ⚙️ Automated Execution (PineConnector Webhook Bridge)

Currently, the engine alerts you visually via the interface. If you wish to route the engine's identified `activeSetup` signals directly to MetaTrader 4 or 5:

1. Ensure the **PineConnector EA** is running on your host VPS/Terminal.
2. You will need to spin up a tiny NodeJS backend or serverless edge function to receive the webhook payload from this React application (browsers cannot securely send cross-origin POST requests directly to PineConnector without exposing your license).
3. Transmit the payload in the standard PineConnector schema based on the generated Dashboard lot sizes:
```json
{
  "licenseId": "YOUR_PINECONNECTOR_LICENSE",
  "action": "Buy",
  "symbol": "XAUUSD",
  "volume": 0.33,
  "sl": 2340.50,
  "tp": 2355.00
}
```

---

## 🛠️ Stack & Dependencies
* **Framework:** React 19 + TypeScript
* **State Management:** Zustand
* **Build Tool:** Vite
* **Styling:** Tailwind CSS v4 + Lucide Icons
* **Data Provider:** Twelve Data (REST & WSS)
* **Charting Engine:** TradingView `lightweight-charts` SDK (v5.x)
