import { PricePoint, Timeframe, SMCMarking, SignalType, LogEntry, EngineStatus, MarketBias, KillzoneSession, NewsEvent, RiskConfig } from '../types/trading';

const BASE_PRICE = 2342.50;

export function generateMockData(count: number, timeframe: Timeframe): PricePoint[] {
  const data: PricePoint[] = [];
  let currentPrice = BASE_PRICE;
  const currentTime = new Date();

  const step =
    timeframe === Timeframe.DAILY ? 24 * 60 * 60 * 1000 :
    timeframe === Timeframe.H1 ? 60 * 60 * 1000 :
    timeframe === Timeframe.M15 ? 15 * 60 * 1000 : 5 * 60 * 1000;

  // Create a slight bullish bias for realistic gold movement
  const drift = 0.0001;

  for (let i = 0; i < count; i++) {
    const volatility = currentPrice * 0.0018;
    const open = currentPrice;
    const rand = Math.random();
    const direction = rand > 0.45 ? 1 : -1; // slight bullish bias
    const impulse = Math.random() > 0.92 ? 2.5 : 1; // occasional impulse candles
    
    const high = open + Math.random() * volatility * impulse;
    const low = open - Math.random() * volatility * impulse;
    const close = direction > 0 
      ? low + (Math.random() * 0.4 + 0.55) * (high - low)
      : low + Math.random() * 0.45 * (high - low);

    data.push({
      time: new Date(currentTime.getTime() - (count - i) * step),
      open,
      high,
      low,
      close,
      volume: Math.floor(Math.random() * 15000 + 2000),
    });

    currentPrice = close + currentPrice * drift;
  }

  return data;
}

export function calculateEMA(data: PricePoint[], period: number): number[] {
  const k = 2 / (period + 1);
  let ema = data[0].close;
  const results = [ema];

  for (let i = 1; i < data.length; i++) {
    ema = data[i].close * k + ema * (1 - k);
    results.push(ema);
  }

  return results;
}

export function detectSMCMarkings(data: PricePoint[]): SMCMarking[] {
  const markings: SMCMarking[] = [];
  if (data.length < 20) return markings;

  const emaValues = calculateEMA(data, 20);
  
  // Detect Order Blocks
  for (let i = 3; i < data.length - 1; i++) {
    const prev = data[i - 1];
    const curr = data[i];
    const next = data[i + 1] || curr;

    // Bullish OB: bearish candle followed by strong bullish move
    if (prev.close < prev.open && curr.close > curr.open) {
      const moveSize = Math.abs(curr.close - curr.open);
      const avgBody = data.slice(Math.max(0, i - 10), i).reduce((sum, d) => sum + Math.abs(d.close - d.open), 0) / 10;
      if (moveSize > avgBody * 1.8) {
        markings.push({
          type: SignalType.OB,
          price: prev.low,
          priceEnd: prev.high,
          startTime: prev.time,
          isMitigated: false,
          label: 'H1 OB',
          barIndex: i - 1,
        });
      }
    }

    // Bearish OB
    if (prev.close > prev.open && curr.close < curr.open) {
      const moveSize = Math.abs(curr.close - curr.open);
      const avgBody = data.slice(Math.max(0, i - 10), i).reduce((sum, d) => sum + Math.abs(d.close - d.open), 0) / 10;
      if (moveSize > avgBody * 1.8) {
        markings.push({
          type: SignalType.OB,
          price: prev.high,
          priceEnd: prev.low,
          startTime: prev.time,
          isMitigated: false,
          label: 'H1 OB (Bear)',
          barIndex: i - 1,
        });
      }
    }
  }

  // Detect FVGs (Fair Value Gaps)
  for (let i = 2; i < data.length; i++) {
    const bar0 = data[i - 2];
    const bar2 = data[i];

    // Bullish FVG
    if (bar0.high < bar2.low) {
      markings.push({
        type: SignalType.FVG,
        price: bar0.high,
        priceEnd: bar2.low,
        startTime: data[i - 1].time,
        isMitigated: false,
        label: 'FVG',
        barIndex: i - 1,
      });
    }

    // Bearish FVG
    if (bar0.low > bar2.high) {
      markings.push({
        type: SignalType.FVG,
        price: bar0.low,
        priceEnd: bar2.high,
        startTime: data[i - 1].time,
        isMitigated: false,
        label: 'FVG (Bear)',
        barIndex: i - 1,
      });
    }
  }

  // Detect BOS (Break of Structure)
  let swingHigh = data[0].high;
  let swingLow = data[0].low;
  for (let i = 5; i < data.length; i++) {
    const currentHigh = data[i].high;
    const currentLow = data[i].low;

    if (currentHigh > swingHigh) {
      markings.push({
        type: SignalType.BOS,
        price: swingHigh,
        startTime: data[i].time,
        isMitigated: false,
        label: 'BOS ▲',
        barIndex: i,
      });
      swingHigh = currentHigh;
    }
    if (currentLow < swingLow) {
      markings.push({
        type: SignalType.BOS,
        price: swingLow,
        startTime: data[i].time,
        isMitigated: false,
        label: 'BOS ▼',
        barIndex: i,
      });
      swingLow = currentLow;
    }
  }

  // Keep only last few of each type to avoid clutter
  const obMarkings = markings.filter(m => m.type === SignalType.OB).slice(-3);
  const fvgMarkings = markings.filter(m => m.type === SignalType.FVG).slice(-4);
  const bosMarkings = markings.filter(m => m.type === SignalType.BOS).slice(-4);

  return [...obMarkings, ...fvgMarkings, ...bosMarkings];
}

export function getKillzoneSession(): KillzoneSession {
  const now = new Date();
  const utcHour = now.getUTCHours();
  
  if (utcHour >= 7 && utcHour < 10) return 'LONDON';
  if (utcHour >= 12 && utcHour < 16) return 'NEW_YORK';
  if (utcHour >= 10 && utcHour < 12) return 'OVERLAP';
  if (utcHour >= 0 && utcHour < 7) return 'ASIAN';
  return 'OFF';
}

export function isKillzoneActive(): boolean {
  const session = getKillzoneSession();
  return session === 'LONDON' || session === 'NEW_YORK' || session === 'OVERLAP';
}

export function getEngineStatus(data: PricePoint[]): EngineStatus {
  const lastPrice = data[data.length - 1]?.close ?? BASE_PRICE;
  const ema200 = calculateEMA(data, Math.min(data.length, 200));
  const ema200Value = ema200[ema200.length - 1] ?? BASE_PRICE;
  const session = getKillzoneSession();

  return {
    macroBias: lastPrice > ema200Value ? MarketBias.BULLISH : MarketBias.BEARISH,
    killzone: session,
    isKillzoneActive: isKillzoneActive(),
    newsShield: true,
    newsCountdown: '45m',
    idmSwept: Math.random() > 0.5,
    chochConfirmed: Math.random() > 0.6,
    ema200: ema200Value,
    currentPrice: lastPrice,
    structure: lastPrice > ema200Value ? 'HH/HL' : 'LH/LL',
    engineOnline: true,
  };
}

export function generateLogEntries(): LogEntry[] {
  const now = new Date();
  return [
    {
      id: '1',
      timestamp: new Date(now.getTime() - 60000 * 5),
      module: 'DAILY_BIAS',
      message: `Price > 200 EMA (${BASE_PRICE.toFixed(2)}). Structure HH/HL. Macro bias → BULLISH. Sell commands disabled.`,
      level: 'INFO',
    },
    {
      id: '2',
      timestamp: new Date(now.getTime() - 60000 * 4),
      module: 'H1_ANALYSIS',
      message: `Unmitigated Order Block detected at ${(BASE_PRICE - 8.5).toFixed(2)}. Bullish FVG present between ${(BASE_PRICE - 6.2).toFixed(2)} and ${(BASE_PRICE - 4.8).toFixed(2)}.`,
      level: 'INFO',
    },
    {
      id: '3',
      timestamp: new Date(now.getTime() - 60000 * 3),
      module: 'KILLZONE',
      message: 'London/NY Overlap session active. Engine armed. Monitoring for IDM sweep.',
      level: 'INFO',
    },
    {
      id: '4',
      timestamp: new Date(now.getTime() - 60000 * 2),
      module: 'IDM_ENGINE',
      message: `Liquidity Sweep of IDM (${(BASE_PRICE - 3.2).toFixed(2)}) completed. Wick captured retail stops. Awaiting CHOCH confirmation.`,
      level: 'SIGNAL',
    },
    {
      id: '5',
      timestamp: new Date(now.getTime() - 60000),
      module: 'M15_TRIGGER',
      message: `CHOCH confirmed on M15. Internal BOS above ${(BASE_PRICE + 1.5).toFixed(2)}. All confluences aligned.`,
      level: 'SIGNAL',
    },
    {
      id: '6',
      timestamp: new Date(now.getTime() - 30000),
      module: 'EXECUTION',
      message: `▶ SIGNAL FIRED: BUY @ ${BASE_PRICE.toFixed(2)} | SL: ${(BASE_PRICE - 3.0).toFixed(2)} | TP1: ${(BASE_PRICE + 6.0).toFixed(2)} | TP2: ${(BASE_PRICE + 9.0).toFixed(2)} | Lot: 3.33`,
      level: 'CRITICAL',
    },
    {
      id: '7',
      timestamp: now,
      module: 'NEWS_SHIELD',
      message: 'High Impact USD News (NFP) in 45m. Auto-blackout triggers in 15m. Manual override available.',
      level: 'WARN',
    },
  ];
}

export function generateNewsEvents(): NewsEvent[] {
  const now = new Date();
  return [
    { id: '1', time: new Date(now.getTime() + 1000 * 60 * 45), currency: 'USD', impact: 'HIGH', event: 'NFP Employment Change', countdown: '45m' },
    { id: '2', time: new Date(now.getTime() + 1000 * 60 * 120), currency: 'USD', impact: 'HIGH', event: 'FOMC Rate Decision', countdown: '2h 00m' },
    { id: '3', time: new Date(now.getTime() + 1000 * 60 * 240), currency: 'USD', impact: 'MEDIUM', event: 'Consumer Confidence', countdown: '4h 00m' },
    { id: '4', time: new Date(now.getTime() + 1000 * 60 * 360), currency: 'EUR', impact: 'MEDIUM', event: 'ECB Press Conference', countdown: '6h 00m' },
  ];
}

export function calculateRisk(config: RiskConfig): { lotSize: number; riskAmount: number; tp1Price: number; tp2Price: number; slPrice: number } {
  const riskAmount = config.accountBalance * (config.riskPercent / 100);
  const lotSize = riskAmount / (config.stopDistancePips * 10);
  const pipsValue = config.stopDistancePips / 10;

  return {
    lotSize: Math.round(lotSize * 100) / 100,
    riskAmount: Math.round(riskAmount * 100) / 100,
    tp1Price: pipsValue * config.tp1Ratio,
    tp2Price: pipsValue * config.tp2Ratio,
    slPrice: pipsValue,
  };
}

export function formatTime(date: Date): string {
  return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function formatTimeBST(date: Date): string {
  return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Europe/London' });
}
