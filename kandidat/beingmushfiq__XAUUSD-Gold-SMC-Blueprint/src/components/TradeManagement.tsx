import React, { useState } from 'react';
import { RiskConfig } from '../types/trading';
import { calculateRisk } from '../utils/marketData';
import { Shield, Lock, Gauge, ArrowUpDown, Target, Crosshair } from 'lucide-react';

interface TradeManagementProps {
  config: RiskConfig;
  onConfigChange: (config: RiskConfig) => void;
}

export const TradeManagement: React.FC<TradeManagementProps> = ({ config, onConfigChange }) => {
  const risk = calculateRisk(config);

  const updateConfig = (key: keyof RiskConfig, value: number) => {
    onConfigChange({ ...config, [key]: value });
  };

  const riskProgress = (config.riskPercent / config.maxDailyDrawdown) * 100;

  return (
    <div className="space-y-5">
      {/* Fortress Header */}
      <div className="bg-[#0c0d10] border border-white/[0.06] rounded-2xl p-5">
        <div className="flex items-center gap-2.5 mb-5">
          <div className="w-8 h-8 rounded-xl bg-indigo-500/10 flex items-center justify-center">
            <Shield className="text-indigo-400 w-4 h-4" />
          </div>
          <div>
            <h2 className="text-[11px] font-bold uppercase tracking-[0.15em] text-white/70">Fortress of Capital</h2>
            <p className="text-[9px] text-white/30 mt-0.5">Risk Engine v4.2</p>
          </div>
        </div>

        {/* Account & Risk */}
        <div className="grid grid-cols-2 gap-3 mb-5">
          <div className="bg-white/[0.03] rounded-xl p-3">
            <label className="text-[9px] text-white/30 uppercase font-mono tracking-widest block mb-1.5">Equity</label>
            <div className="flex items-baseline gap-1">
              <span className="text-[10px] text-white/40">$</span>
              <input
                type="number"
                value={config.accountBalance}
                onChange={(e) => updateConfig('accountBalance', Number(e.target.value))}
                className="text-lg font-mono font-black text-amber-500 bg-transparent w-full outline-none focus:ring-0 p-0 m-0 border-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
              />
            </div>
          </div>
          <div className="bg-white/[0.03] rounded-xl p-3">
            <label className="text-[9px] text-white/30 uppercase font-mono tracking-widest block mb-1.5">Risk / Trade</label>
            <div className="flex items-baseline gap-1">
              <input
                type="number"
                step="0.1"
                value={config.riskPercent}
                onChange={(e) => updateConfig('riskPercent', Number(e.target.value))}
                className="text-lg font-mono font-black text-white bg-transparent w-10 outline-none focus:ring-0 p-0 m-0 border-none text-right [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
              />
              <span className="text-lg font-mono font-black text-white">%</span>
              <span className="text-[10px] text-white/30 ml-1">(${risk.riskAmount})</span>
            </div>
          </div>
        </div>

        {/* Risk Meter */}
        <div className="mb-5">
          <div className="flex justify-between items-center mb-2">
            <span className="text-[9px] text-white/30 uppercase font-mono tracking-widest">Daily Risk Used</span>
            <span className="text-[10px] font-mono font-bold text-white/50">{riskProgress.toFixed(0)}% of {config.maxDailyDrawdown}%</span>
          </div>
          <div className="h-2 bg-white/[0.04] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${Math.min(riskProgress, 100)}%`,
                background: riskProgress < 50 ? 'linear-gradient(90deg, #10b981, #34d399)' :
                           riskProgress < 80 ? 'linear-gradient(90deg, #fbbf24, #f59e0b)' :
                           'linear-gradient(90deg, #ef4444, #dc2626)',
              }}
            />
          </div>
        </div>

        {/* Parameters Grid */}
        <div className="space-y-2.5">
          <div className="flex justify-between items-center py-2 px-3 bg-white/[0.02] rounded-lg">
            <div className="flex items-center gap-2">
              <Crosshair className="w-3 h-3 text-blue-400/50" />
              <span className="text-[10px] text-white/40 uppercase tracking-wider">Lot Size</span>
            </div>
            <span className="text-sm font-mono font-bold text-blue-400">{risk.lotSize}</span>
          </div>
          <div className="flex justify-between items-center py-2 px-3 bg-white/[0.02] rounded-lg">
            <div className="flex items-center gap-2">
              <Lock className="w-3 h-3 text-rose-400/50" />
              <span className="text-[10px] text-white/40 uppercase tracking-wider">Stop Distance</span>
            </div>
            <span className="text-sm font-mono font-bold text-rose-400">{config.stopDistancePips} pips</span>
          </div>
          <div className="flex justify-between items-center py-2 px-3 bg-white/[0.02] rounded-lg">
            <div className="flex items-center gap-2">
              <Target className="w-3 h-3 text-emerald-400/50" />
              <span className="text-[10px] text-white/40 uppercase tracking-wider">TP1 (1:{config.tp1Ratio})</span>
            </div>
            <span className="text-sm font-mono font-bold text-emerald-400">+{risk.tp1Price.toFixed(1)} pts</span>
          </div>
          <div className="flex justify-between items-center py-2 px-3 bg-white/[0.02] rounded-lg">
            <div className="flex items-center gap-2">
              <Target className="w-3 h-3 text-emerald-400/30" />
              <span className="text-[10px] text-white/40 uppercase tracking-wider">TP2 (1:{config.tp2Ratio})</span>
            </div>
            <span className="text-sm font-mono font-bold text-emerald-400/70">+{risk.tp2Price.toFixed(1)} pts</span>
          </div>
        </div>
      </div>

      {/* Trade Management Rules */}
      <div className="bg-[#0c0d10] border border-white/[0.06] rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Gauge className="w-4 h-4 text-amber-400/50" />
          <h3 className="text-[10px] font-bold uppercase tracking-[0.15em] text-white/50">Management Protocol</h3>
        </div>

        <div className="space-y-3">
          <div className="flex gap-3 items-start p-3 rounded-xl bg-amber-500/[0.04] border border-amber-500/10">
            <div className="w-5 h-5 rounded-full bg-amber-500/10 flex items-center justify-center shrink-0 mt-0.5">
              <ArrowUpDown className="w-3 h-3 text-amber-400" />
            </div>
            <div>
              <div className="text-[10px] font-bold text-amber-400 mb-0.5">Break-Even Trigger</div>
              <p className="text-[9px] text-white/35 leading-relaxed">At 1:1.5 RR → Move SL to entry. Push notification fired automatically.</p>
            </div>
          </div>

          <div className="flex gap-3 items-start p-3 rounded-xl bg-emerald-500/[0.04] border border-emerald-500/10">
            <div className="w-5 h-5 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0 mt-0.5">
              <span className="text-[9px] font-bold text-emerald-400">50%</span>
            </div>
            <div>
              <div className="text-[10px] font-bold text-emerald-400 mb-0.5">The 50% Rule</div>
              <p className="text-[9px] text-white/35 leading-relaxed">At 1:2 RR → Close 50% position. Trail remaining behind latest M15 Higher Low.</p>
            </div>
          </div>

          <div className="flex gap-3 items-start p-3 rounded-xl bg-rose-500/[0.04] border border-rose-500/10">
            <div className="w-5 h-5 rounded-full bg-rose-500/10 flex items-center justify-center shrink-0 mt-0.5">
              <Shield className="w-3 h-3 text-rose-400" />
            </div>
            <div>
              <div className="text-[10px] font-bold text-rose-400 mb-0.5">Max Daily Drawdown</div>
              <p className="text-[9px] text-white/35 leading-relaxed">{config.maxDailyDrawdown}% limit (${(config.accountBalance * config.maxDailyDrawdown / 100).toFixed(0)}). Engine auto-disables on breach.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
