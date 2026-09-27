import React, { useState } from 'react';
import { EngineStatus } from '../types/trading';
import { 
  Activity, Clock, TrendingUp, Shield, Zap, Radio, 
  Crosshair, BarChart3, Eye, ChevronDown, ChevronUp 
} from 'lucide-react';
import { motion } from 'motion/react';

interface EngineStatusPanelProps {
  status: EngineStatus;
}

const BIAS_COLORS = {
  BULLISH: { color: '#10b981', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.2)' },
  BEARISH: { color: '#ef4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.2)' },
  NEUTRAL: { color: '#64748b', bg: 'rgba(100,116,139,0.08)', border: 'rgba(100,116,139,0.2)' },
};

export const EngineStatusPanel: React.FC<EngineStatusPanelProps> = ({ status }) => {
  const [expanded, setExpanded] = useState(true);
  const biasStyle = BIAS_COLORS[status.macroBias];

  const statusItems = [
    {
      icon: Activity,
      label: 'Macro Bias',
      value: `${status.macroBias} (D1)`,
      detail: `Structure: ${status.structure}`,
      color: biasStyle.color,
      active: true,
    },
    {
      icon: Clock,
      label: 'Killzone',
      value: status.isKillzoneActive ? status.killzone.replace('_', ' ') : 'Off-Session',
      detail: status.isKillzoneActive ? 'Engine Armed' : 'Engine Standby',
      color: status.isKillzoneActive ? '#fbbf24' : '#64748b',
      active: status.isKillzoneActive,
    },
    {
      icon: TrendingUp,
      label: 'Structure',
      value: status.structure === 'HH/HL' ? 'BOS Confirmed' : status.structure === 'LH/LL' ? 'Bearish BOS' : 'Ranging',
      detail: `200 EMA: ${status.ema200.toFixed(2)}`,
      color: status.structure === 'HH/HL' ? '#818cf8' : '#f87171',
      active: true,
    },
    {
      icon: Crosshair,
      label: 'IDM Status',
      value: status.idmSwept ? 'IDM Swept ✓' : 'Awaiting Sweep',
      detail: status.idmSwept ? 'Retail liquidity captured' : 'Monitoring minor pullbacks',
      color: status.idmSwept ? '#2dd4bf' : '#64748b',
      active: status.idmSwept,
    },
    {
      icon: Zap,
      label: 'CHOCH',
      value: status.chochConfirmed ? 'Confirmed ✓' : 'Pending',
      detail: status.chochConfirmed ? 'Internal BOS detected' : 'Awaiting structure shift',
      color: status.chochConfirmed ? '#60a5fa' : '#64748b',
      active: status.chochConfirmed,
    },
    {
      icon: Shield,
      label: 'News Shield',
      value: status.newsShield ? `Active (${status.newsCountdown})` : 'Disabled',
      detail: status.newsShield ? 'High impact event approaching' : 'No high-impact events',
      color: status.newsShield ? '#f87171' : '#10b981',
      active: status.newsShield,
    },
  ];

  return (
    <div className="space-y-3">
      {/* Main Engine Status */}
      <div 
        className="rounded-2xl p-4 cursor-pointer transition-all hover:border-white/10"
        style={{
          background: status.engineOnline 
            ? 'linear-gradient(135deg, rgba(16,185,129,0.04), rgba(16,185,129,0.01))' 
            : 'linear-gradient(135deg, rgba(239,68,68,0.04), rgba(239,68,68,0.01))',
          border: `1px solid ${status.engineOnline ? 'rgba(16,185,129,0.15)' : 'rgba(239,68,68,0.15)'}`,
        }}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.div
              animate={status.engineOnline ? { scale: [1, 1.15, 1] } : {}}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ backgroundColor: status.engineOnline ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)' }}
            >
              <Radio className="w-4.5 h-4.5" style={{ color: status.engineOnline ? '#10b981' : '#ef4444' }} />
            </motion.div>
            <div>
              <div className="text-[11px] font-bold uppercase tracking-wider" style={{ color: status.engineOnline ? '#10b981' : '#ef4444' }}>
                {status.engineOnline ? 'Logic Engine Online' : 'Engine Offline'}
              </div>
              <div className="text-[9px] text-white/30">
                XAUUSD · {status.currentPrice.toFixed(2)} · v4.2.0
              </div>
            </div>
          </div>
          {expanded ? <ChevronUp className="w-4 h-4 text-white/20" /> : <ChevronDown className="w-4 h-4 text-white/20" />}
        </div>
      </div>

      {/* Status Grid */}
      {expanded && (
        <motion.div 
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="grid grid-cols-2 gap-2.5"
        >
          {statusItems.map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-[#0c0d10] border border-white/[0.06] rounded-xl p-3.5 hover:border-white/10 transition-all group"
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: item.color + '15' }}>
                  <item.icon className="w-3.5 h-3.5" style={{ color: item.color }} />
                </div>
              </div>
              <div className="text-[9px] text-white/25 uppercase font-mono tracking-[0.15em] mb-0.5">{item.label}</div>
              <div className="text-[11px] font-bold uppercase" style={{ color: item.color }}>{item.value}</div>
              <div className="text-[8px] text-white/20 mt-1">{item.detail}</div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
};
