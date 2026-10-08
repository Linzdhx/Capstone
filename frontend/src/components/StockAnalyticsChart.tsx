import React, { useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
} from 'recharts';
import {
  BarChart3,
  PieChart as PieIcon,
  AlertTriangle,
  TrendingDown,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react';
import { StockAnalyticsSummary, StockChartCategory } from '../types';

interface StockAnalyticsChartProps {
  analytics?: StockAnalyticsSummary | null;
  totalAisles: number;
}

export const StockAnalyticsChart: React.FC<StockAnalyticsChartProps> = ({
  analytics,
  totalAisles,
}) => {
  const [chartMode, setChartMode] = useState<'bar' | 'donut'>('bar');

  // Fallback si analytics no está presente
  const categories: StockChartCategory[] = analytics?.categories && analytics.categories.length > 0
    ? analytics.categories
    : [
        {
          key: 'urgent',
          name: 'Urgente',
          label: '🔴 Urgente (0% - 10% Stock)',
          range_label: '0% - 10% Stock',
          count: analytics?.urgent_count ?? 0,
          color: '#ef4444',
          percentage: 0,
        },
        {
          key: 'quick_attention',
          name: 'Atención Rápida',
          label: '🟡 Atención Rápida (10% - 15% Stock)',
          range_label: '10% - 15% Stock',
          count: analytics?.quick_attention_count ?? 0,
          color: '#eab308',
          percentage: 0,
        },
        {
          key: 'emptying',
          name: 'Góndola Vaciándose',
          label: '🟠 Góndola Vaciándose (15% - 20% Stock)',
          range_label: '15% - 20% Stock',
          count: analytics?.emptying_count ?? 0,
          color: '#f97316',
          percentage: 0,
        },
      ];

  const avgDepletion = analytics?.average_depletion_pct ?? 0.0;
  const totalActive = analytics?.total_active_alerts ?? totalAisles;

  // Formato para tooltip personalizado
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload as StockChartCategory;
      return (
        <div className="bg-slate-900/95 border border-slate-700/80 rounded-xl p-3.5 shadow-2xl backdrop-blur-md">
          <div className="flex items-center gap-2 mb-1.5">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: data.color }}
            />
            <span className="font-extrabold text-sm text-white">{data.name}</span>
          </div>
          <p className="text-xs text-slate-400 mb-1">Rango: <span className="text-slate-200 font-semibold">{data.range_label}</span></p>
          <div className="flex items-center justify-between gap-4 text-xs font-mono">
            <span className="text-slate-300">Alertas activas:</span>
            <span className="font-bold text-white text-sm">{data.count}</span>
          </div>
          <div className="flex items-center justify-between gap-4 text-xs font-mono mt-0.5">
            <span className="text-slate-300">Proporción:</span>
            <span className="font-bold text-cyan-400">{data.percentage.toFixed(1)}%</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-6">
      {/* Header del Gráfico */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Sparkles size={18} />
            </div>
            <div>
              <h2 className="text-lg font-extrabold text-white tracking-tight flex items-center gap-2">
                Distribución Analítica de Faltantes & Severidad
              </h2>
              <p className="text-xs text-slate-400">
                Consolidación estadística por rangos de stock en góndola ({totalActive} alertas activas)
              </p>
            </div>
          </div>
        </div>

        {/* Selector de tipo de gráfico */}
        <div className="flex items-center gap-1.5 bg-slate-950/80 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setChartMode('bar')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              chartMode === 'bar'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <BarChart3 size={14} />
            <span>Barras</span>
          </button>
          <button
            onClick={() => setChartMode('donut')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              chartMode === 'donut'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <PieIcon size={14} />
            <span>Donut</span>
          </button>
        </div>
      </div>

      {/* Tarjetas KPI de Distribución y Desabastecimiento Promedio */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* KPI 1: Desabastecimiento Promedio Global */}
        <div className="p-4 rounded-xl bg-gradient-to-br from-slate-800/70 to-slate-900/90 border border-slate-700/60 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span className="font-semibold uppercase tracking-wider text-[10px] text-slate-400 flex items-center gap-1">
              <TrendingDown size={13} className="text-cyan-400" />
              Desabastecimiento Promedio
            </span>
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl font-extrabold font-mono text-cyan-300">
              {avgDepletion.toFixed(1)}%
            </span>
            <span className="text-xs text-slate-400">faltante global</span>
          </div>
          <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
            <div
              className="bg-cyan-400 h-full rounded-full transition-all duration-700"
              style={{ width: `${Math.min(100, Math.max(0, avgDepletion))}%` }}
            />
          </div>
        </div>

        {/* KPI 2: 🔴 Urgente (0% - 10% Stock) */}
        <div className="p-4 rounded-xl bg-red-950/20 border border-red-500/30 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-red-300 text-xs mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px] flex items-center gap-1.5 text-red-400">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              🔴 Urgente
            </span>
            <span className="text-[10px] font-mono bg-red-950/80 px-2 py-0.5 rounded border border-red-500/20 text-red-300">
              0% - 10% Stock
            </span>
          </div>
          <div className="text-3xl font-extrabold font-mono text-red-400 mb-1">
            {categories.find((c) => c.key === 'urgent')?.count ?? 0}
            <span className="text-xs text-red-300/70 font-normal ml-1.5">pasillos</span>
          </div>
          <span className="text-[11px] text-red-400/80 font-medium">
            Reposición total inmediata
          </span>
        </div>

        {/* KPI 3: 🟡 Atención Rápida (10% - 15% Stock) */}
        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-amber-300 text-xs mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px] flex items-center gap-1.5 text-amber-400">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              🟡 Atención Rápida
            </span>
            <span className="text-[10px] font-mono bg-amber-950/80 px-2 py-0.5 rounded border border-amber-500/20 text-amber-300">
              10% - 15% Stock
            </span>
          </div>
          <div className="text-3xl font-extrabold font-mono text-amber-400 mb-1">
            {categories.find((c) => c.key === 'quick_attention')?.count ?? 0}
            <span className="text-xs text-amber-300/70 font-normal ml-1.5">pasillos</span>
          </div>
          <span className="text-[11px] text-amber-400/80 font-medium">
            Reposición moderada
          </span>
        </div>

        {/* KPI 4: 🟠 Góndola Vaciándose (15% - 20% Stock) */}
        <div className="p-4 rounded-xl bg-orange-950/20 border border-orange-500/30 shadow-lg flex flex-col justify-between">
          <div className="flex items-center justify-between text-orange-300 text-xs mb-2">
            <span className="font-bold uppercase tracking-wider text-[10px] flex items-center gap-1.5 text-orange-400">
              <span className="w-2 h-2 rounded-full bg-orange-500" />
              🟠 Góndola Vaciándose
            </span>
            <span className="text-[10px] font-mono bg-orange-950/80 px-2 py-0.5 rounded border border-orange-500/20 text-orange-300">
              15% - 20% Stock
            </span>
          </div>
          <div className="text-3xl font-extrabold font-mono text-orange-400 mb-1">
            {categories.find((c) => c.key === 'emptying')?.count ?? 0}
            <span className="text-xs text-orange-300/70 font-normal ml-1.5">pasillos</span>
          </div>
          <span className="text-[11px] text-orange-400/80 font-medium">
            Control y prevención activa
          </span>
        </div>
      </div>

      {/* Componente Gráfico Interactivo */}
      <div className="bg-slate-950/60 rounded-xl p-5 border border-slate-800">
        <div className="h-64 w-full">
          {chartMode === 'bar' ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={categories}
                margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
              >
                <XAxis
                  dataKey="name"
                  stroke="#94a3b8"
                  fontSize={12}
                  tickLine={false}
                  axisLine={{ stroke: '#334155' }}
                />
                <YAxis
                  stroke="#94a3b8"
                  fontSize={12}
                  tickLine={false}
                  axisLine={{ stroke: '#334155' }}
                  allowDecimals={false}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                  {categories.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categories}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={5}
                  dataKey="count"
                >
                  {categories.map((entry, index) => (
                    <Cell key={`donut-cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Leyenda interactiva inferior */}
        <div className="flex flex-wrap items-center justify-center gap-6 pt-3 border-t border-slate-800/80 text-xs">
          {categories.map((cat) => (
            <div key={cat.key} className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: cat.color }}
              />
              <span className="text-slate-300 font-medium">{cat.label}:</span>
              <span className="font-mono font-bold text-white">{cat.count}</span>
              <span className="text-slate-500 font-mono">({cat.percentage.toFixed(1)}%)</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
