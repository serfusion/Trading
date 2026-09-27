import React, { useState, useEffect } from 'react';
import { KillzoneSession } from '../types/trading';
import { getKillzoneSession, formatTimeBST } from '../utils/marketData';
import { Clock, Radio } from 'lucide-react';
import { motion } from 'motion/react';

const SESSION_CONFIG: Record<KillzoneSession, { label: string; color: string; bgColor: string; borderColor: string; glow: string }> = {
  LONDON: { label: 'London Open', color: '#fbbf24', bgColor: 'rgba(251,191,36,0.08)', borderColor: 'rgba(251,191,36,0.25)', glow: '0 0 30px rgba(251,191,36,0.15)' },
  NEW_YORK: { label: 'New York', color: '#3b82f6', bgColor: 'rgba(59,130,246,0.08)', borderColor: 'rgba(59,130,246,0.25)', glow: '0 0 30px rgba(59,130,246,0.15)' },
  OVERLAP: { label: 'LDN / NY Overlap', color: '#a855f7', bgColor: 'rgba(168,85,247,0.08)', borderColor: 'rgba(168,85,247,0.25)', glow: '0 0 30px rgba(168,85,247,0.15)' },
  ASIAN: { label: 'Asian Session', color: '#64748b', bgColor: 'rgba(100,116,139,0.06)', borderColor: 'rgba(100,116,139,0.15)', glow: 'none' },
  OFF: { label: 'Off-Session', color: '#475569', bgColor: 'rgba(71,85,105,0.05)', borderColor: 'rgba(71,85,105,0.1)', glow: 'none' },
};

// BST session times visualized as 24h ring
const SESSIONS = [
  { start: 7, end: 10, label: 'LDN', color: '#fbbf24' },
  { start: 10, end: 12, label: 'OVL', color: '#a855f7' },
  { start: 12, end: 16, label: 'NY', color: '#3b82f6' },
];

export const KillzoneClock: React.FC = () => {
  const [session, setSession] = useState<KillzoneSession>(getKillzoneSession());
  const [bstTime, setBstTime] = useState(formatTimeBST(new Date()));
  const [seconds, setSeconds] = useState(new Date().getSeconds());

  useEffect(() => {
    const interval = setInterval(() => {
      setSession(getKillzoneSession());
      setBstTime(formatTimeBST(new Date()));
      setSeconds(new Date().getSeconds());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const config = SESSION_CONFIG[session];
  const isActive = session === 'LONDON' || session === 'NEW_YORK' || session === 'OVERLAP';
  const utcHour = new Date().getUTCHours();
  const utcMinute = new Date().getUTCMinutes();
  const hourAngle = ((utcHour % 24) / 24) * 360 - 90;
  const minuteAngle = (utcMinute / 60) * 360 - 90;

  return (
    <div
      className="rounded-2xl p-5 transition-all duration-500"
      style={{
        background: config.bgColor,
        border: `1px solid ${config.borderColor}`,
        boxShadow: config.glow,
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4" style={{ color: config.color }} />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-white/50">Gold Clock</span>
        </div>
        {isActive && (
          <motion.div
            animate={{ opacity: [1, 0.4, 1] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="flex items-center gap-1.5"
          >
            <Radio className="w-3 h-3" style={{ color: config.color }} />
            <span className="text-[9px] font-mono uppercase tracking-widest" style={{ color: config.color }}>Live</span>
          </motion.div>
        )}
      </div>

      {/* Clock Ring */}
      <div className="flex items-center justify-center mb-4">
        <div className="relative w-32 h-32">
          <svg viewBox="0 0 100 100" className="w-full h-full">
            {/* Background ring */}
            <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
            
            {/* Session arcs */}
            {SESSIONS.map((s, i) => {
              const startAngle = (s.start / 24) * 360 - 90;
              const endAngle = (s.end / 24) * 360 - 90;
              const startRad = (startAngle * Math.PI) / 180;
              const endRad = (endAngle * Math.PI) / 180;
              const x1 = 50 + 42 * Math.cos(startRad);
              const y1 = 50 + 42 * Math.sin(startRad);
              const x2 = 50 + 42 * Math.cos(endRad);
              const y2 = 50 + 42 * Math.sin(endRad);
              const largeArc = endAngle - startAngle > 180 ? 1 : 0;
              return (
                <path
                  key={i}
                  d={`M ${x1} ${y1} A 42 42 0 ${largeArc} 1 ${x2} ${y2}`}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="6"
                  opacity={0.6}
                  strokeLinecap="round"
                />
              );
            })}

            {/* Hour hand */}
            <line
              x1="50" y1="50"
              x2={50 + 24 * Math.cos((hourAngle * Math.PI) / 180)}
              y2={50 + 24 * Math.sin((hourAngle * Math.PI) / 180)}
              stroke={config.color}
              strokeWidth="2.5"
              strokeLinecap="round"
            />
            {/* Minute hand */}
            <line
              x1="50" y1="50"
              x2={50 + 32 * Math.cos((minuteAngle * Math.PI) / 180)}
              y2={50 + 32 * Math.sin((minuteAngle * Math.PI) / 180)}
              stroke="rgba(255,255,255,0.5)"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
            {/* Center dot */}
            <circle cx="50" cy="50" r="3" fill={config.color} />
            <circle cx="50" cy="50" r="1.5" fill="#0a0a0a" />
          </svg>
        </div>
      </div>

      {/* Time Display */}
      <div className="text-center mb-4">
        <div className="text-2xl font-mono font-black tracking-tighter" style={{ color: config.color }}>
          {bstTime}
        </div>
        <div className="text-[9px] text-white/30 uppercase tracking-[0.3em] mt-1">BST (UTC+1)</div>
      </div>

      {/* Session Badge */}
      <div
        className="text-center py-2.5 rounded-xl"
        style={{
          background: `linear-gradient(135deg, ${config.bgColor}, transparent)`,
          border: `1px solid ${config.borderColor}`,
        }}
      >
        <div className="text-xs font-bold uppercase tracking-wider" style={{ color: config.color }}>
          {config.label}
        </div>
        <div className="text-[9px] text-white/30 mt-0.5">
          {isActive ? 'Engine Armed & Scanning' : 'Engine Standby'}
        </div>
      </div>

      {/* Session Timeline */}
      <div className="mt-4 space-y-1.5">
        {SESSIONS.map((s, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: s.color, opacity: 0.6 }} />
            <span className="text-[9px] font-mono text-white/40 flex-1">{s.label}</span>
            <span className="text-[9px] font-mono text-white/25">{String(s.start).padStart(2, '0')}:00 – {String(s.end).padStart(2, '0')}:00</span>
          </div>
        ))}
      </div>
    </div>
  );
};
