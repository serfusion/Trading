/// <reference types="vite/client" />
import { useStore } from '../store/useStore';
import { PricePoint, KillzoneSession, MarketBias, SignalType } from '../types/trading';
import { calculateEMA, buildSMCMarkings, checkIDMSweep } from '../engine/LogicCore';

const API_KEY = import.meta.env.VITE_TWELVEDATA_API_KEY;
const SYMBOL = 'XAU/USD';

function getKillzoneSession(): KillzoneSession {
  const now = new Date();
  const utcHour = now.getUTCHours();
  
  if (utcHour >= 7 && utcHour < 10) return 'LONDON';
  if (utcHour >= 12 && utcHour < 16) return 'NEW_YORK';
  if (utcHour >= 10 && utcHour < 12) return 'OVERLAP';
  if (utcHour >= 0 && utcHour < 7) return 'ASIAN';
  return 'OFF';
}

function isKillzoneActive(): boolean {
  const session = getKillzoneSession();
  return session === 'LONDON' || session === 'NEW_YORK' || session === 'OVERLAP';
}

function processLogicCore() {
  const store = useStore.getState();
  const data = store.tickData;
  if (data.length < 20) return;

  const lastPrice = data[data.length - 1].close;
  
  const emaData = calculateEMA(data, 200);
  const ema200Value = emaData[emaData.length - 1] ?? lastPrice;
  
  const markings = buildSMCMarkings(data);
  store.setSMCMarkings(markings);

  const isIDMSwept = checkIDMSweep(data);
  const bosDetected = markings.some(m => m.type === SignalType.BOS && m.barIndex === data.length - 1);

  store.updateEngineStatus({
    macroBias: lastPrice > ema200Value ? MarketBias.BULLISH : MarketBias.BEARISH,
    killzone: getKillzoneSession(),
    isKillzoneActive: isKillzoneActive(),
    ema200: ema200Value,
    currentPrice: lastPrice,
    structure: lastPrice > ema200Value ? 'HH/HL' : 'LH/LL',
    idmSwept: store.engineStatus.idmSwept || isIDMSwept,
    chochConfirmed: store.engineStatus.chochConfirmed || bosDetected,
    engineOnline: true
  });
  
  if (isIDMSwept && !store.engineStatus.idmSwept) {
    store.addLog({
      timestamp: new Date(),
      module: 'IDM_ENGINE',
      message: `Liquidity Sweep of IDM detected at ${lastPrice.toFixed(2)}. Wick captured retail stops. Awaiting CHOCH confirmation.`,
      level: 'SIGNAL'
    });
  }
}

let ws: WebSocket | null = null;
let historicalDataLoaded = false;
let isStarted = false;

async function fetchHistoricalData() {
  try {
    const res = await fetch(`https://api.twelvedata.com/time_series?symbol=${SYMBOL}&interval=15min&outputsize=150&apikey=${API_KEY}`);
    const json = await res.json();
    
    if (json.values && json.values.length > 0) {
      const historical: PricePoint[] = json.values.map((v: any) => ({
        time: new Date(v.datetime),
        open: parseFloat(v.open),
        high: parseFloat(v.high),
        low: parseFloat(v.low),
        close: parseFloat(v.close),
        volume: parseInt(v.volume, 10) || 0,
      })).reverse(); // TwelveData returns latest first

      useStore.getState().setTickData(historical);
      historicalDataLoaded = true;
      processLogicCore();
      
      useStore.getState().addLog({
        timestamp: new Date(),
        module: 'H1_ANALYSIS',
        message: `Bootstrapped 150 historical M15 candles from TwelveData API. Engine initialized.`,
        level: 'INFO'
      });
    }
  } catch (err) {
    console.error("Failed to load historical data", err);
    useStore.getState().addLog({
      timestamp: new Date(),
      module: 'EXECUTION',
      message: `Failed to fetch REST time series from TwelveData. Check API key.`,
      level: 'CRITICAL'
    });
  }
}

function handleLiveTick(price: number, timestamp: number) {
  const store = useStore.getState();
  const data = store.tickData;
  if (data.length === 0) return;

  const lastCandle = data[data.length - 1];
  const lastTime = lastCandle.time.getTime();
  
  // Checking if we crossed into a new algorithmic 15M block
  const isNewCandle = timestamp - lastTime >= 15 * 60 * 1000;

  if (isNewCandle) {
    // Add a brand new M15 candle using the opening tick
    store.addTick({
      time: new Date(timestamp),
      open: price,
      high: price,
      low: price,
      close: price,
      volume: 0
    });
  } else {
    // Update the high/low/close of the active M15 candle
    store.updateLastCandle(price, new Date(timestamp));
  }

  processLogicCore();
}

export const marketDataFeed = {
  start: async () => {
    if (isStarted || !API_KEY) {
      if (!API_KEY) {
        useStore.getState().updateEngineStatus({ engineOnline: false });
        console.error("No Twelve Data API Key configured in .env.local");
      }
      return;
    }
    
    isStarted = true;
    
    if (!historicalDataLoaded) {
      await fetchHistoricalData();
    }

    ws = new WebSocket(`wss://ws.twelvedata.com/v1/quotes/price?apikey=${API_KEY}`);

    ws.onopen = () => {
      ws?.send(JSON.stringify({ action: "subscribe", params: { symbols: SYMBOL } }));
      useStore.getState().addLog({
        timestamp: new Date(),
        module: 'EXECUTION',
        message: `WebSocket connected. Subscribed to live tick stream for ${SYMBOL}.`,
        level: 'INFO'
      });
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.event === "price" && msg.price) {
          handleLiveTick(parseFloat(msg.price), msg.timestamp * 1000);
        }
      } catch (err) {
        console.error("WebSocket message parse error", err);
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket Error:", err);
    };

    ws.onclose = () => {
      isStarted = false;
      useStore.getState().updateEngineStatus({ engineOnline: false });
      useStore.getState().addLog({
        timestamp: new Date(),
        module: 'EXECUTION',
        message: `WebSocket disconnected. Attempting to reconnect...`,
        level: 'WARN'
      });
      // Simple reconnect logic
      setTimeout(() => marketDataFeed.start(), 5000);
    };
  },
  
  stop: () => {
    if (ws) {
      ws.close();
      ws = null;
    }
    isStarted = false;
  }
};
