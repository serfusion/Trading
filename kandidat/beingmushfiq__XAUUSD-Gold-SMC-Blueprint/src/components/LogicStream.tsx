import React, { useState } from 'react';
import { LogEntry } from '../types/trading';
import { Terminal, Filter, ChevronDown, Copy, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { formatTime } from '../utils/marketData';

interface LogicStreamProps {
  entries: LogEntry[];
}

const MODULE_COLORS: Record<string, string> = {
  DAILY_BIAS: '#818cf8',
  H1_ANALYSIS: '#fbbf24',
  M15_TRIGGER: '#34d399',
  NEWS_SHIELD: '#f87171',
  EXECUTION: '#60a5fa',
  RISK_ENGINE: '#c084fc',
  KILLZONE: '#fb923c',
  IDM_ENGINE: '#2dd4bf',
};

const LEVEL_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  INFO: { bg: 'rgba(255,255,255,0.03)', text: 'text-white/50', dot: 'bg-white/20' },
  WARN: { bg: 'rgba(251,191,36,0.04)', text: 'text-amber-400/80', dot: 'bg-amber-500' },
  SIGNAL: { bg: 'rgba(52,211,153,0.04)', text: 'text-emerald-400/80', dot: 'bg-emerald-500' },
  CRITICAL: { bg: 'rgba(96,165,250,0.06)', text: 'text-blue-400', dot: 'bg-blue-500 animate-pulse' },
};

export const LogicStream: React.FC<LogicStreamProps> = ({ entries }) => {
  const [filter, setFilter] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const filtered = filter ? entries.filter(e => e.module === filter) : entries;

  const handleCopy = () => {
    const text = filtered.map(e => `[${formatTime(e.timestamp)}] ${e.module}: ${e.message}`).join('\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-[#0c0d10] border border-white/[0.06] rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Terminal className="w-4 h-4 text-white/30" />
          <h2 className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/50">Logic Stream</h2>
        </div>
        <div className="flex items-center gap-3">
          <motion.div
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="flex items-center gap-1.5"
          >
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
            <span className="text-[9px] font-mono text-emerald-500/70 uppercase tracking-wider">Processing</span>
          </motion.div>
          <button onClick={handleCopy} className="p-1.5 rounded-lg hover:bg-white/5 transition-colors text-white/30 hover:text-white/60">
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="px-5 py-2.5 border-b border-white/[0.04] flex items-center gap-2 overflow-x-auto scrollbar-hide">
        <Filter className="w-3 h-3 text-white/20 shrink-0" />
        <button
          onClick={() => setFilter(null)}
          className={`text-[9px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wider whitespace-nowrap transition-all ${!filter ? 'bg-white/10 text-white/70' : 'text-white/25 hover:text-white/50'}`}
        >
          All
        </button>
        {Object.keys(MODULE_COLORS).map(mod => (
          <button
            key={mod}
            onClick={() => setFilter(filter === mod ? null : mod)}
            className={`text-[9px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wider whitespace-nowrap transition-all ${filter === mod ? 'text-white/80' : 'text-white/20 hover:text-white/40'}`}
            style={filter === mod ? { backgroundColor: MODULE_COLORS[mod] + '20', color: MODULE_COLORS[mod] } : {}}
          >
            {mod.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Log Entries */}
      <div className="p-3 space-y-1 max-h-[280px] overflow-y-auto scrollbar-thin">
        <AnimatePresence>
          {filtered.map((entry, i) => {
            const style = LEVEL_STYLES[entry.level];
            return (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex gap-3 px-3 py-2 rounded-lg font-mono text-[11px] leading-relaxed"
                style={{ backgroundColor: style.bg }}
              >
                <div className="flex items-start gap-2 shrink-0 pt-0.5">
                  <span className={`w-1.5 h-1.5 rounded-full mt-1 ${style.dot}`} />
                  <span className="text-white/25 w-[62px]">[{formatTime(entry.timestamp)}]</span>
                </div>
                <span className="font-bold shrink-0 w-[100px]" style={{ color: MODULE_COLORS[entry.module] }}>
                  {entry.module}:
                </span>
                <span className={style.text}>{entry.message}</span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
};
