import React from 'react';
import { AppState } from '../types';

interface StatusBadgeProps {
  state: AppState;
  text?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ state, text, size = 'md' }) => {
  const configs: Record<AppState, { bg: string; text: string; dot: string; pulse: boolean }> = {
    CONNECTED: {
      bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
      dot: 'bg-emerald-400',
      text: 'CONNECTED',
      pulse: false,
    },
    DISCONNECTED: {
      bg: 'bg-slate-700/20 border-slate-600/30 text-slate-400',
      dot: 'bg-slate-400',
      text: 'DISCONNECTED',
      pulse: false,
    },
    RUNNING: {
      bg: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
      dot: 'bg-blue-400',
      text: 'RUNNING',
      pulse: true,
    },
    TRAINING: {
      bg: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
      dot: 'bg-purple-400',
      text: 'TRAINING',
      pulse: true,
    },
    VALIDATING: {
      bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
      dot: 'bg-amber-400',
      text: 'VALIDATING',
      pulse: true,
    },
    ALERT: {
      bg: 'bg-rose-500/20 border-rose-500/40 text-rose-300 shadow-lg shadow-rose-950/40',
      dot: 'bg-rose-500',
      text: 'ALERT',
      pulse: true,
    },
  };

  const current = configs[state] || configs.DISCONNECTED;
  const displayText = text || current.text;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
    lg: 'px-3 py-1.5 text-sm',
  }[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold tracking-wider uppercase rounded-full border ${current.bg} ${sizeClasses}`}
    >
      <span className="relative flex h-2 w-2">
        {current.pulse && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${current.dot}`}
          />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${current.dot}`} />
      </span>
      {displayText}
    </span>
  );
};
