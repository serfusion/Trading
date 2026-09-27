export enum Timeframe {
  DAILY = 'D1',
  H1 = 'H1',
  M15 = 'M15',
  M5 = 'M5',
}

export enum MarketBias {
  BULLISH = 'BULLISH',
  BEARISH = 'BEARISH',
  NEUTRAL = 'NEUTRAL',
}

export enum SignalType {
  BOS = 'BOS',
  CHOCH = 'CHOCH',
  IDM = 'IDM',
  OB = 'OB',
  FVG = 'FVG',
  LIQUIDITY_SWEEP = 'LIQUIDITY_SWEEP',
  EMA200 = 'EMA200',
}

export interface PricePoint {
  time: Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface SMCMarking {
  type: SignalType;
  price: number;
  priceEnd?: number;
  startTime: Date;
  endTime?: Date;
  isMitigated: boolean;
  label: string;
  barIndex?: number;
}

export interface TradingSetup {
  id: string;
  name: string;
  type: 'BUY' | 'SELL';
  confluences: string[];
  entry: number;
  sl: number;
  tp1: number;
  tp2: number;
  tp3: number;
  lotSize: number;
  riskReward: number;
  timestamp: Date;
  status: 'PENDING' | 'ACTIVE' | 'TP1' | 'TP2' | 'TP3' | 'SL' | 'BE';
}

export interface NewsEvent {
  id: string;
  time: Date;
  currency: string;
  impact: 'LOW' | 'MEDIUM' | 'HIGH';
  event: string;
  countdown?: string;
}

export type KillzoneSession = 'LONDON' | 'NEW_YORK' | 'OVERLAP' | 'ASIAN' | 'OFF';

export interface EngineStatus {
  macroBias: MarketBias;
  killzone: KillzoneSession;
  isKillzoneActive: boolean;
  newsShield: boolean;
  newsCountdown: string;
  idmSwept: boolean;
  chochConfirmed: boolean;
  ema200: number;
  currentPrice: number;
  structure: 'HH/HL' | 'LH/LL' | 'RANGE';
  engineOnline: boolean;
}

export interface LogEntry {
  id: string;
  timestamp: Date;
  module: 'DAILY_BIAS' | 'H1_ANALYSIS' | 'M15_TRIGGER' | 'NEWS_SHIELD' | 'EXECUTION' | 'RISK_ENGINE' | 'KILLZONE' | 'IDM_ENGINE';
  message: string;
  level: 'INFO' | 'WARN' | 'SIGNAL' | 'CRITICAL';
}

export interface RiskConfig {
  accountBalance: number;
  riskPercent: number;
  maxDailyDrawdown: number;
  lotSize: number;
  stopDistancePips: number;
  tp1Ratio: number;
  tp2Ratio: number;
  breakEvenRR: number;
  partialCloseRR: number;
  partialClosePercent: number;
}
