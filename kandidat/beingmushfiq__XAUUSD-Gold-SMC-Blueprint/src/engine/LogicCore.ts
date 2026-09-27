import { PricePoint, SMCMarking, SignalType } from '../types/trading';

/**
 * Calculates the Exponential Moving Average
 */
export function calculateEMA(data: PricePoint[], period: number): number[] {
  if (data.length === 0) return [];
  const k = 2 / (period + 1);
  let ema = data[0].close;
  const results = [ema];

  for (let i = 1; i < data.length; i++) {
    ema = data[i].close * k + ema * (1 - k);
    results.push(ema);
  }

  return results;
}

/**
 * Detects Market Structure Breaks (BOS)
 */
export function detectStructure(data: PricePoint[]): SMCMarking[] {
  const markings: SMCMarking[] = [];
  if (data.length < 5) return markings;

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

  return markings;
}

/**
 * Detects Unmitigated Order Blocks (OB)
 */
export function detectOrderBlocks(data: PricePoint[]): SMCMarking[] {
  const markings: SMCMarking[] = [];
  if (data.length < 10) return markings;

  for (let i = 3; i < data.length - 1; i++) {
    const prev = data[i - 1];
    const curr = data[i];

    const moveSize = Math.abs(curr.close - curr.open);
    const avgBody = data.slice(Math.max(0, i - 10), i).reduce((sum, d) => sum + Math.abs(d.close - d.open), 0) / 10;

    // Bullish OB
    if (prev.close < prev.open && curr.close > curr.open && moveSize > avgBody * 1.8) {
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

    // Bearish OB
    if (prev.close > prev.open && curr.close < curr.open && moveSize > avgBody * 1.8) {
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

  return markings;
}

/**
 * Detects Fair Value Gaps (FVG)
 */
export function detectFVG(data: PricePoint[]): SMCMarking[] {
  const markings: SMCMarking[] = [];
  if (data.length < 3) return markings;

  for (let i = 2; i < data.length; i++) {
    const bar0 = data[i - 2];
    const bar2 = data[i];

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

  return markings;
}

/**
 * Sweeps the previous N candles to find an IDM sweep logic
 * Simulates a sweep rule (wicking past a recent fractal)
 */
export function checkIDMSweep(data: PricePoint[]): boolean {
  if (data.length < 10) return false;
  // Simplified mathematical IDM logic for demonstration
  const recentHighs = data.slice(-10, -1).map(d => d.high);
  const recentLows = data.slice(-10, -1).map(d => d.low);
  const maxHigh = Math.max(...recentHighs);
  const minLow = Math.min(...recentLows);
  const lastBar = data[data.length - 1];
  
  // Sweep occurs if price wicks past the recent high/low but closes inside
  const sweepLow = lastBar.low < minLow && lastBar.close > minLow;
  const sweepHigh = lastBar.high > maxHigh && lastBar.close < maxHigh;
  
  return sweepLow || sweepHigh;
}

export function buildSMCMarkings(data: PricePoint[]): SMCMarking[] {
  const ob = detectOrderBlocks(data).slice(-3); // Keep latest 3
  const fvg = detectFVG(data).slice(-4);
  const bos = detectStructure(data).slice(-4);
  return [...ob, ...fvg, ...bos];
}
