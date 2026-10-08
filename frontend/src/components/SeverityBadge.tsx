import React from 'react';
import { SeverityLevel } from '../types';

interface SeverityBadgeProps {
  severity: SeverityLevel;
  large?: boolean;
}

const SEVERITY_CONFIG = {
  CRITICAL: {
    emoji: '🔴',
    label: 'CRÍTICO',
    bg: 'bg-red-500/15 border-red-500/40',
    text: 'text-red-400',
    dot: 'bg-red-500',
    ring: 'ring-red-500/30',
    glow: 'shadow-red-500/20',
  },
  MODERATE: {
    emoji: '🟡',
    label: 'MODERADO',
    bg: 'bg-amber-500/15 border-amber-500/40',
    text: 'text-amber-400',
    dot: 'bg-amber-500',
    ring: 'ring-amber-500/30',
    glow: 'shadow-amber-500/20',
  },
  LOW: {
    emoji: '🟢',
    label: 'BAJO',
    bg: 'bg-emerald-500/15 border-emerald-500/40',
    text: 'text-emerald-400',
    dot: 'bg-emerald-500',
    ring: 'ring-emerald-500/30',
    glow: 'shadow-emerald-500/20',
  },
} as const;

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, large = false }) => {
  const cfg = SEVERITY_CONFIG[severity];

  if (large) {
    return (
      <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-bold uppercase tracking-widest ${cfg.bg} ${cfg.text} shadow-lg ${cfg.glow}`}>
        <span className={`w-2 h-2 rounded-full ${cfg.dot} ${severity === 'CRITICAL' ? 'animate-pulse' : ''}`} />
        {cfg.emoji} {cfg.label}
      </div>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider ${cfg.bg} ${cfg.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
};
