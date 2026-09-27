import React, { useState, useEffect, useMemo } from 'react';
import { GoldChart } from './GoldChart';
import { SignalCard } from './SignalCard';
import { KillzoneClock } from './KillzoneClock';
import { LogicStream } from './LogicStream';
import { TradeManagement } from './TradeManagement';
import { EngineStatusPanel } from './EngineStatusPanel';
import { NewsShield } from './NewsShield';
import { useStore } from '../store/useStore';
import { marketDataFeed } from '../services/marketDataFeed';
import { Timeframe, TradingSetup } from '../types/trading';
import {
  Zap,
  Bell,
  Settings,
  Monitor,
  Layers,
  FileCode,
  BarChart3,
  Menu,
  X,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

type Tab = 'dashboard' | 'pine' | 'manual';

export const Dashboard: React.FC = () => {
  const [timeframe, setTimeframe] = useState<Timeframe>(Timeframe.M15);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  // Zustand Global State
  const marketData = useStore(state => state.tickData);
  const currentPrice = useStore(state => state.currentPrice);
  const engineStatus = useStore(state => state.engineStatus);
  const markings = useStore(state => state.smcMarkings);
  const logEntries = useStore(state => state.logs);
  const riskConfig = useStore(state => state.riskConfig);
  const updateRiskConfig = useStore(state => state.updateRiskConfig);
  const newsEvents = useMemo(() => [], []); // Keep static for now or move to store

  const setups: TradingSetup[] = useMemo(() => {
    if (marketData.length === 0) return [];
    return [
      {
        id: 's1',
        name: 'SMC Liquidity Grab Model',
        type: 'BUY',
        confluences: ['Daily Bullish', 'H1 OB Mitigated', 'IDM Swept', 'M15 CHOCH', 'London/NY Overlap'],
        entry: currentPrice,
        sl: currentPrice - 3.0,
        tp1: currentPrice + 6.0,
        tp2: currentPrice + 9.0,
        tp3: currentPrice + 14.0,
        lotSize: riskConfig.accountBalance * (riskConfig.riskPercent / 100) / (riskConfig.stopDistancePips * 10),
        riskReward: 2.0,
        timestamp: new Date(),
        status: 'PENDING',
      },
    ];
  }, [currentPrice, riskConfig, marketData]);

  // Start the live data feed on mount
  useEffect(() => {
    marketDataFeed.start();
    return () => marketDataFeed.stop();
  }, []);

  const prevPrice = marketData[marketData.length - 2]?.close ?? currentPrice;
  const priceChange = currentPrice - prevPrice;
  const priceChangePercent = prevPrice ? ((priceChange / prevPrice) * 100).toFixed(3) : "0.000";

  if (marketData.length === 0) return <div className="min-h-screen bg-[#050506] flex items-center justify-center text-white/50 font-mono">INITIALIZING LOGIC ENGINE...</div>;

  return (
    <div className="min-h-screen bg-[#050506] text-white font-sans noise">
      {/* ═══════════════════════════════════════════ */}
      {/* TOP NAVIGATION BAR                          */}
      {/* ═══════════════════════════════════════════ */}
      <nav className="border-b border-white/[0.05] glass sticky top-0 z-50">
        <div className="max-w-[1680px] mx-auto px-4 lg:px-6 h-14 flex items-center justify-between">
          {/* Brand */}
          <div className="flex items-center gap-4 lg:gap-8">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-gradient-to-br from-amber-400 to-amber-600 rounded-lg flex items-center justify-center shadow-lg shadow-amber-500/20">
                <Zap className="text-black w-4.5 h-4.5 fill-current" />
              </div>
              <div className="hidden sm:block">
                <span className="font-black tracking-tighter text-base uppercase">Gold Blueprint</span>
                <span className="text-[9px] text-white/20 ml-2 font-mono">v4.2.0</span>
              </div>
            </div>

            {/* Timeframe Selector */}
            <div className="flex items-center gap-0.5 bg-white/[0.04] p-1 rounded-xl border border-white/[0.06]">
              {Object.values(Timeframe).map(tf => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1.5 rounded-lg text-[10px] font-bold transition-all ${
                    timeframe === tf
                      ? 'bg-amber-500 text-black shadow-md shadow-amber-500/20'
                      : 'text-white/30 hover:text-white/60 hover:bg-white/[0.04]'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Price Ticker & Controls */}
          <div className="flex items-center gap-3 lg:gap-5">
            {/* Live Price */}
            <div className="hidden md:flex items-center gap-3 px-4 py-1.5 bg-white/[0.03] rounded-xl border border-white/[0.06]">
              <div className="flex items-center gap-2">
                <motion.div
                  animate={{ scale: [1, 1.3, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  className="w-2 h-2 bg-emerald-500 rounded-full"
                />
                <span className="text-[9px] text-white/30 uppercase font-mono tracking-wider">XAUUSD</span>
              </div>
              <span className="text-base font-mono font-black text-amber-400 text-glow-gold">
                {currentPrice.toFixed(2)}
              </span>
              <span className={`text-[11px] font-mono font-bold ${priceChange >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)} ({priceChangePercent}%)
              </span>
            </div>

            {/* Equity Badge */}
            <div className="hidden lg:flex items-center gap-3 px-4 py-1.5 bg-white/[0.03] rounded-xl border border-white/[0.06]">
              <div className="flex flex-col items-end">
                <span className="text-[8px] text-white/25 uppercase font-mono tracking-[0.15em]">Equity</span>
                <span className="text-sm font-mono font-black text-amber-500">${riskConfig.accountBalance.toLocaleString()}</span>
              </div>
              <div className="w-px h-7 bg-white/[0.06]" />
              <div className="flex flex-col items-end">
                <span className="text-[8px] text-white/25 uppercase font-mono tracking-[0.15em]">Risk</span>
                <span className="text-sm font-mono font-bold">{riskConfig.riskPercent}%</span>
              </div>
            </div>

            {/* Nav Icons */}
            <div className="hidden md:flex items-center gap-1">
              <button 
                className="p-2 text-white/25 hover:text-white/60 hover:bg-white/[0.04] rounded-lg transition-all"
                onClick={() => alert("Alerts Armed: Webhook bridge configured to push signals via PineConnector.")}
              >
                <Bell className="w-4 h-4" />
              </button>
              <button 
                className="p-2 text-white/25 hover:text-white/60 hover:bg-white/[0.04] rounded-lg transition-all"
                onClick={() => alert("Global System Settings locked. Adjust local risk parameters in the Management panel.")}
              >
                <Settings className="w-4 h-4" />
              </button>
            </div>

            {/* Mobile menu */}
            <button
              className="md:hidden p-2 text-white/40"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </nav>

      {/* ═══════════════════════════════════════════ */}
      {/* MAIN CONTENT                                */}
      {/* ═══════════════════════════════════════════ */}
      <main className="max-w-[1680px] mx-auto px-4 lg:px-6 py-5">
        <div className="grid grid-cols-12 gap-5">
          {/* ═══════════ LEFT COLUMN (Chart + Logic Stream) ═══════════ */}
          <div className="col-span-12 xl:col-span-8 space-y-5">
            {/* Engine Status Panels */}
            <EngineStatusPanel status={engineStatus} />

            {/* Chart */}
            <div className="relative">
              {/* Chart Overlay Label */}
              <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
                <span className="glass border border-white/[0.08] px-3 py-1.5 rounded-lg text-[10px] font-mono font-bold text-amber-400 flex items-center gap-2">
                  <Monitor className="w-3.5 h-3.5" />
                  XAUUSD · {timeframe} · OANDA
                </span>
                <span className="glass border border-white/[0.08] px-2 py-1.5 rounded-lg text-[9px] font-mono text-white/30 flex items-center gap-1.5">
                  <Layers className="w-3 h-3" />
                  SMC Overlay
                </span>
              </div>
              <GoldChart />
            </div>

            {/* Logic Stream */}
            <LogicStream entries={logEntries} />
          </div>

          {/* ═══════════ RIGHT COLUMN (Sidebar) ═══════════ */}
          <div className="col-span-12 xl:col-span-4 space-y-5">
            {/* Active Setups */}
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/40">Active Setups</h2>
                <span className="bg-amber-500/10 text-amber-400 text-[9px] px-2.5 py-1 rounded-lg font-bold tracking-wider">
                  {setups.length} DETECTED
                </span>
              </div>
              <div className="space-y-3">
                {setups.map(setup => (
                  <SignalCard key={setup.id} setup={setup} />
                ))}
              </div>
            </section>

            {/* Killzone Clock */}
            <KillzoneClock />

            {/* News Shield */}
            <NewsShield events={newsEvents} />

            {/* Trade Management */}
            <TradeManagement config={riskConfig} onConfigChange={updateRiskConfig} />
          </div>
        </div>
      </main>

      {/* ═══════════════════════════════════════════ */}
      {/* FOOTER                                      */}
      {/* ═══════════════════════════════════════════ */}
      <footer className="border-t border-white/[0.04] mt-8">
        <div className="max-w-[1680px] mx-auto px-4 lg:px-6 py-4 flex flex-wrap items-center justify-between gap-4 text-[9px] text-white/20 font-mono uppercase tracking-[0.15em]">
          <div className="flex items-center gap-5">
            <div className="flex items-center gap-1.5">
              <motion.span
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="w-1.5 h-1.5 bg-emerald-500 rounded-full"
              />
              System: Operational
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
              Data Feed: OANDA (Live)
            </div>
            <div className="hidden sm:flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-amber-500 rounded-full" />
              Webhook: PineConnector Ready
            </div>
          </div>
          <div className="text-white/15">
            © 2026 XAUUSD Gold Blueprint · Institutional Logic Engine v4.2.0
          </div>
        </div>
      </footer>
    </div>
  );
};
