import { create } from 'zustand';
import { EngineStatus, LogEntry, PricePoint, TradingSetup, SMCMarking, MarketBias, RiskConfig } from '../types/trading';

interface AppState {
  // Market Data
  tickData: PricePoint[];
  currentPrice: number;
  
  // Logic Engine State
  engineStatus: EngineStatus;
  logs: LogEntry[];
  smcMarkings: SMCMarking[];
  activeSetup: TradingSetup | null;
  
  // Config
  riskConfig: RiskConfig;

  // Actions
  addTick: (tick: PricePoint) => void;
  updateLastCandle: (tickPrice: number, timestamp: Date) => void;
  setTickData: (data: PricePoint[]) => void;
  updateEngineStatus: (status: Partial<EngineStatus>) => void;
  addLog: (log: Omit<LogEntry, 'id'>) => void;
  setSMCMarkings: (markings: SMCMarking[]) => void;
  setSetup: (setup: TradingSetup | null) => void;
  updateRiskConfig: (config: Partial<RiskConfig>) => void;
}

const initialRiskConfig: RiskConfig = {
  accountBalance: 100000,
  riskPercent: 1.0,
  maxDailyDrawdown: 3.0,
  lotSize: 0,
  stopDistancePips: 30, // 30 pips standard for XAUUSD swing
  tp1Ratio: 2.0, // 1:2
  tp2Ratio: 3.0, // 1:3
  breakEvenRR: 1.5,
  partialCloseRR: 2.0,
  partialClosePercent: 50,
};

const initialEngineStatus: EngineStatus = {
  macroBias: MarketBias.NEUTRAL,
  killzone: 'OFF',
  isKillzoneActive: false,
  newsShield: true,
  newsCountdown: '--',
  idmSwept: false,
  chochConfirmed: false,
  ema200: 0,
  currentPrice: 0,
  structure: 'RANGE',
  engineOnline: true,
};

export const useStore = create<AppState>((set) => ({
  tickData: [],
  currentPrice: 0,
  engineStatus: initialEngineStatus,
  logs: [],
  smcMarkings: [],
  activeSetup: null,
  riskConfig: initialRiskConfig,

  setTickData: (data) => set({ tickData: data, currentPrice: data[data.length - 1]?.close ?? 0 }),

  updateLastCandle: (tickPrice, _timestamp) => set((state) => {
    if (state.tickData.length === 0) return state;
    const data = [...state.tickData];
    const last = { ...data[data.length - 1] };
    
    // Update the OHLC of the ongoing M15 candle using the latest tick price
    last.high = Math.max(last.high, tickPrice);
    last.low = Math.min(last.low, tickPrice);
    last.close = tickPrice;
    
    data[data.length - 1] = last;
    
    return {
      tickData: data,
      currentPrice: tickPrice
    };
  }),

  addTick: (tick) => set((state) => {
    // Keep last 1000 candles for performance
    const newData = [...state.tickData, tick].slice(-1000);
    return { 
      tickData: newData,
      currentPrice: tick.close
    };
  }),

  updateEngineStatus: (status) => set((state) => ({
    engineStatus: { ...state.engineStatus, ...status }
  })),

  addLog: (log) => set((state) => ({
    logs: [{ ...log, id: Math.random().toString(36).substring(7) }, ...state.logs].slice(0, 50)
  })),

  setSMCMarkings: (markings) => set({ smcMarkings: markings }),

  setSetup: (setup) => set({ activeSetup: setup }),

  updateRiskConfig: (config) => set((state) => ({
    riskConfig: { ...state.riskConfig, ...config }
  })),
}));
