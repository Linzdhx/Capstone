import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  variant?: 'default' | 'danger' | 'success' | 'warning' | 'info';
  percentage?: number;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  variant = 'default',
  percentage,
}) => {
  const variantStyles = {
    default: {
      card: 'bg-slate-900/60 border-slate-800 text-slate-100',
      iconBg: 'bg-slate-800 text-slate-300',
      bar: 'bg-blue-500',
    },
    danger: {
      card: 'bg-rose-950/20 border-rose-900/40 text-rose-100 shadow-lg shadow-rose-950/20',
      iconBg: 'bg-rose-900/40 text-rose-400',
      bar: 'bg-rose-500',
    },
    success: {
      card: 'bg-emerald-950/20 border-emerald-900/40 text-emerald-100',
      iconBg: 'bg-emerald-900/40 text-emerald-400',
      bar: 'bg-emerald-500',
    },
    warning: {
      card: 'bg-amber-950/20 border-amber-900/40 text-amber-100',
      iconBg: 'bg-amber-900/40 text-amber-400',
      bar: 'bg-amber-500',
    },
    info: {
      card: 'bg-blue-950/20 border-blue-900/40 text-blue-100',
      iconBg: 'bg-blue-900/40 text-blue-400',
      bar: 'bg-blue-500',
    },
  }[variant];

  return (
    <div className={`p-4 rounded-xl border backdrop-blur-sm transition-all duration-200 hover:border-slate-700 ${variantStyles.card}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-slate-400">{title}</span>
        <div className={`p-2 rounded-lg ${variantStyles.iconBg}`}>
          {icon}
        </div>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold font-mono tracking-tight">{value}</span>
        {subtitle && <span className="text-xs text-slate-400">{subtitle}</span>}
      </div>
      {percentage !== undefined && (
        <div className="mt-3">
          <div className="w-full bg-slate-800/80 rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ${variantStyles.bar}`}
              style={{ width: `${Math.min(100, Math.max(0, percentage))}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
