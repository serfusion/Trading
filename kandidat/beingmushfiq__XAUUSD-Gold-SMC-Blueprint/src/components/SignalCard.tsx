import React from 'react';
import { TradingSetup } from '../types/trading';
import { format } from 'date-fns';
import { TrendingUp, TrendingDown, Target, Crosshair, ChevronRight } from 'lucide-react';
import { motion } from 'motion/react';

interface SignalCardProps {
  setup: TradingSetup;
}

export const SignalCard: React.FC<SignalCardProps> = ({ setup }) => {
  const isBuy = setup.type === 'BUY';
  const accentColor = isBuy ? '#10b981' : '#ef4444';
  const accentBg = isBuy ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)';
  const accentBorder = isBuy ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)';

  const rrRatio = ((setup.tp1 - setup.entry) / Math.abs(setup.entry - setup.sl)).toFixed(1);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl p-5 transition-all duration-300 group cursor-pointer"
      style={{
        background: `linear-gradient(135deg, ${accentBg}, rgba(12,13,16,1))`,
        border: `1px solid ${accentBorder}`,
      }}
      whileHover={{ scale: 1.01, borderColor: accentColor }}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span
              className="px-2.5 py-1 rounded-lg text-[10px] font-black uppercase tracking-wider"
              style={{ backgroundColor: accentColor + '15', color: accentColor }}
            >
              {setup.type}
            </span>
            <span className="text-white/25 text-[9px] font-mono">
              {format(setup.timestamp, 'HH:mm:ss')}
            </span>
            <span
              className="px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider"
              style={{
                backgroundColor: setup.status === 'PENDING' ? 'rgba(251,191,36,0.1)' : 'rgba(16,185,129,0.1)',
                color: setup.status === 'PENDING' ? '#fbbf24' : '#10b981',
              }}
            >
              {setup.status}
            </span>
          </div>
          <h3 className="text-white font-semibold text-base tracking-tight group-hover:text-amber-400 transition-colors">
            {setup.name}
          </h3>
        </div>
        <div className="text-right">
          <div className="font-mono text-sm font-black" style={{ color: accentColor }}>
            LOT {setup.lotSize.toFixed(2)}
          </div>
          <div className="text-white/20 text-[9px] uppercase font-mono tracking-widest">
            1:{rrRatio} RR
          </div>
        </div>
      </div>

      {/* Price Levels */}
      <div className="grid grid-cols-2 gap-x-6 gap-y-3 mb-5">
        <PriceLevel label="Entry" value={setup.entry} color="#3b82f6" icon={Crosshair} />
        <PriceLevel label="Stop Loss" value={setup.sl} color="#ef4444" icon={TrendingDown} />
        <PriceLevel label="Target 1 (1:2)" value={setup.tp1} color="#10b981" icon={Target} />
        <PriceLevel label="Target 2 (1:3)" value={setup.tp2} color="#10b981" icon={TrendingUp} opacity={0.6} />
      </div>

      {/* Confluences */}
      <div className="border-t border-white/[0.05] pt-3.5">
        <div className="text-[8px] text-white/20 uppercase tracking-[0.2em] mb-2">Confluences</div>
        <div className="flex flex-wrap gap-1.5">
          {setup.confluences.map((c, i) => (
            <span
              key={i}
              className="bg-white/[0.04] text-white/45 text-[9px] px-2.5 py-1 rounded-lg border border-white/[0.05] uppercase tracking-tight font-medium"
            >
              {c}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  );
};

// Sub-component for price levels
const PriceLevel: React.FC<{
  label: string;
  value: number;
  color: string;
  icon: React.FC<{ className?: string; style?: React.CSSProperties }>;
  opacity?: number;
}> = ({ label, value, color, icon: Icon, opacity = 1 }) => (
  <div className="flex items-center gap-2" style={{ opacity }}>
    <Icon className="w-3 h-3 shrink-0" style={{ color }} />
    <div>
      <div className="text-[8px] uppercase font-mono tracking-[0.15em]" style={{ color: color + '80' }}>{label}</div>
      <div className="text-[13px] font-mono font-bold" style={{ color }}>{value.toFixed(2)}</div>
    </div>
  </div>
);
