import React, { useState, useEffect } from 'react';
import { NewsEvent } from '../types/trading';
import { AlertTriangle, ShieldAlert, Calendar, ChevronRight, Clock, Shield, Power } from 'lucide-react';
import { motion } from 'motion/react';

interface NewsShieldProps {
  events: NewsEvent[];
}

const IMPACT_STYLES = {
  HIGH: { color: '#ef4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.15)', label: 'RED FOLDER' },
  MEDIUM: { color: '#f59e0b', bg: 'rgba(245,158,11,0.06)', border: 'rgba(245,158,11,0.12)', label: 'ORANGE' },
  LOW: { color: '#64748b', bg: 'rgba(100,116,139,0.05)', border: 'rgba(100,116,139,0.1)', label: 'LOW' },
};

export const NewsShield: React.FC<NewsShieldProps> = ({ events }) => {
  const [shieldArmed, setShieldArmed] = useState(true);
  const [countdowns, setCountdowns] = useState<Record<string, string>>({});

  useEffect(() => {
    const update = () => {
      const now = Date.now();
      const cd: Record<string, string> = {};
      events.forEach(e => {
        const diff = e.time.getTime() - now;
        if (diff > 0) {
          const hrs = Math.floor(diff / 3600000);
          const mins = Math.floor((diff % 3600000) / 60000);
          const secs = Math.floor((diff % 60000) / 1000);
          cd[e.id] = hrs > 0 ? `${hrs}h ${String(mins).padStart(2, '0')}m` : `${mins}m ${String(secs).padStart(2, '0')}s`;
        } else {
          cd[e.id] = 'NOW';
        }
      });
      setCountdowns(cd);
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, [events]);

  const highImpact = events.filter(e => e.impact === 'HIGH');
  const nextHighImpact = highImpact[0];
  const isBlackout = nextHighImpact && (nextHighImpact.time.getTime() - Date.now()) < 30 * 60 * 1000;

  return (
    <div className="bg-[#0c0d10] border border-white/[0.06] rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-white/[0.06]">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-rose-500/10 flex items-center justify-center">
              <ShieldAlert className="text-rose-400 w-4 h-4" />
            </div>
            <div>
              <h2 className="text-[11px] font-bold uppercase tracking-[0.15em] text-white/60">News Shield</h2>
              <p className="text-[8px] text-white/25 mt-0.5">ForexFactory Red Folder Protocol</p>
            </div>
          </div>
          <button
            onClick={() => setShieldArmed(!shieldArmed)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all ${
              shieldArmed
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
            }`}
          >
            <Power className="w-3 h-3" />
            {shieldArmed ? 'Armed' : 'Disabled'}
          </button>
        </div>

        {/* Blackout Warning */}
        {isBlackout && shieldArmed && (
          <motion.div
            animate={{ opacity: [1, 0.7, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className="flex items-center gap-2 p-2.5 rounded-xl bg-rose-500/[0.08] border border-rose-500/20"
          >
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span className="text-[10px] text-rose-300 font-medium">
              BLACKOUT ACTIVE — High impact event in {countdowns[nextHighImpact.id]}. Engine auto-disabled.
            </span>
          </motion.div>
        )}
      </div>

      {/* Events List */}
      <div className="p-4 space-y-2.5">
        {events.map(event => {
          const style = IMPACT_STYLES[event.impact];
          return (
            <div
              key={event.id}
              className="flex items-center justify-between p-3 rounded-xl transition-all hover:scale-[1.01]"
              style={{ backgroundColor: style.bg, border: `1px solid ${style.border}` }}
            >
              <div className="flex items-center gap-3">
                <div className="w-1 h-10 rounded-full" style={{ backgroundColor: style.color }} />
                <div>
                  <div className="text-[11px] font-semibold text-white/80">{event.event}</div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[9px] font-mono text-white/30 uppercase">{event.currency}</span>
                    <span className="text-[8px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider" style={{ backgroundColor: style.color + '15', color: style.color }}>
                      {style.label}
                    </span>
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-mono font-black" style={{ color: style.color }}>
                  {countdowns[event.id] || event.countdown}
                </div>
                <div className="text-[8px] text-white/20 uppercase tracking-wider">Countdown</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Protocol Rules */}
      <div className="px-4 pb-4">
        <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
          <div className="text-[8px] text-white/20 uppercase tracking-[0.2em] mb-2">Protocol Rules</div>
          <div className="space-y-1.5">
            <div className="flex items-start gap-2">
              <span className="w-1 h-1 rounded-full bg-rose-400/40 mt-1.5 shrink-0" />
              <span className="text-[9px] text-white/30 leading-relaxed">CPI / NFP / FOMC → Toggle engine OFF 30m prior</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="w-1 h-1 rounded-full bg-amber-400/40 mt-1.5 shrink-0" />
              <span className="text-[9px] text-white/30 leading-relaxed">100+ pip wick during news → OB marked Invalid</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="w-1 h-1 rounded-full bg-blue-400/40 mt-1.5 shrink-0" />
              <span className="text-[9px] text-white/30 leading-relaxed">Manual calendar check at 12:00 BST mandatory</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
