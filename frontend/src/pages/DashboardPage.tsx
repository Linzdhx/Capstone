import React, { useEffect, useState, useCallback } from 'react';
import {
  PackageX,
  Package,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  TrendingDown,
  Layers,
  Sparkles,
  Inbox,
  FolderOpen,
  ShieldAlert,
} from 'lucide-react';
import { TelemetryMessage, DashboardSummary } from '../types';
import { SystemMonitor } from '../components/SystemMonitor';
import { AisleCard } from '../components/AisleCard';
import { AnalysisUploadZone } from '../components/AnalysisUploadZone';
import { StockAnalyticsChart } from '../components/StockAnalyticsChart';
import { api } from '../services/api';

interface DashboardPageProps {
  telemetry: TelemetryMessage | null;
  onNavigate: (tab: any) => void;
}

// --- Tarjeta de resumen global ---
interface SummaryKpiProps {
  icon: React.ReactNode;
  title: string;
  value: string | number;
  subtitle?: string;
  colorClass?: string;
  bgClass?: string;
}
const SummaryKpi: React.FC<SummaryKpiProps> = ({
  icon,
  title,
  value,
  subtitle,
  colorClass = 'text-slate-100',
  bgClass = 'bg-slate-800/60',
}) => (
  <div className={`flex flex-col gap-1.5 p-4 rounded-xl border border-slate-700/60 ${bgClass} shadow-md`}>
    <div className="flex items-center gap-2 text-slate-400">
      <span className="text-slate-400">{icon}</span>
      <span className="text-[10px] font-bold uppercase tracking-widest">{title}</span>
    </div>
    <div className={`text-2xl font-extrabold font-mono ${colorClass}`}>{value}</div>
    {subtitle && <div className="text-[11px] text-slate-400 font-medium">{subtitle}</div>}
  </div>
);

export const DashboardPage: React.FC<DashboardPageProps> = ({ telemetry }) => {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await api.getStockDashboard();
      setDashboard(data);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'Error al conectar con la API de stock');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // Polling periódico cada 4 segundos para mantener sincronización con /historica
  useEffect(() => {
    const interval = setInterval(() => {
      fetchDashboard();
      setLastRefresh(new Date());
    }, 4000);
    return () => clearInterval(interval);
  }, [fetchDashboard]);

  const handleManualRefresh = () => {
    setLoading(true);
    fetchDashboard();
    setLastRefresh(new Date());
  };

  const isDashboardActive = Boolean(dashboard?.is_active && dashboard.aisles.length > 0);

  return (
    <div className="space-y-8 pb-12">
      {/* 1. Encabezado del Dashboard */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-700/60">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-3">
            Monitoreo de Stock & Pasillos
            {isDashboardActive ? (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 flex items-center gap-1.5 animate-pulse">
                <span className="w-2 h-2 rounded-full bg-rose-500" />
                ACTIVO ({dashboard?.total_aisles} Pasillos con Fallas)
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-700/60 text-slate-300 border border-slate-600/40 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                INACTIVO (Sin fallas)
              </span>
            )}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Activación y análisis dinámico de imágenes en{' '}
            <code className="bg-slate-800 text-cyan-300 px-1.5 py-0.5 rounded font-mono">/historica</code> y carpetas de entrenamiento (<code className="bg-slate-800 text-cyan-300 px-1.5 py-0.5 rounded font-mono">data/approved</code>).
            Cada detección con fallas se numera correlativamente (Alerta N / Pasillo N).
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="text-right hidden sm:block">
            <span className="text-[10px] text-slate-500 block uppercase tracking-wider font-semibold">
              Última sincronización
            </span>
            <span className="text-xs font-mono text-slate-400">
              {lastRefresh.toLocaleTimeString('es-CL')}
            </span>
          </div>

          <button
            onClick={handleManualRefresh}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-all flex items-center gap-1.5 text-xs font-medium shadow-md active:scale-95"
            title="Refrescar datos"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin text-cyan-400' : ''} />
            <span className="hidden sm:inline">Refrescar</span>
          </button>
        </div>
      </div>

      {/* 2. Sección de Carga de Imágenes (Zona de Análisis) */}
      <section>
        <AnalysisUploadZone onAnalysisComplete={fetchDashboard} />
      </section>

      {/* 3. Estado Condicional del Dashboard */}
      {error ? (
        <div className="p-6 bg-rose-950/30 border border-rose-500/40 rounded-2xl text-center space-y-3">
          <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
          <h3 className="text-lg font-bold text-white">Error al cargar datos</h3>
          <p className="text-xs text-rose-300 max-w-md mx-auto">{error}</p>
          <button
            onClick={handleManualRefresh}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-bold transition-all shadow-lg"
          >
            Reintentar
          </button>
        </div>
      ) : !dashboard || !dashboard.is_active || dashboard.aisles.length === 0 ? (
        /* ESTADO INACTIVO: Carpeta /historica vacía */
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-10 text-center shadow-xl backdrop-blur-sm">
          <div className="w-16 h-16 bg-slate-900/80 border border-slate-700 rounded-full flex items-center justify-center mx-auto mb-4 text-emerald-400 shadow-inner">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-extrabold text-white mb-2">
            Dashboard Inactivo — Sin Faltantes Detectados
          </h3>
          <p className="text-sm text-slate-400 max-w-lg mx-auto mb-6 leading-relaxed">
            La carpeta <code className="bg-slate-900 px-2 py-0.5 rounded text-cyan-400 font-mono text-xs font-bold">/historica</code> está vacía o no contiene imágenes con productos faltantes.
            El monitoreo de pasillos solo se activa cuando se detectan fallas de stock en las imágenes analizadas.
          </p>
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-slate-900/80 border border-slate-700 rounded-xl text-xs text-slate-300">
            <FolderOpen className="w-4 h-4 text-cyan-400" />
            <span>Sube imágenes en la <strong>Zona de Análisis</strong> superior para activar el Dashboard.</span>
          </div>
        </div>
      ) : (
        /* ESTADO ACTIVO: Hay imágenes con faltantes en /historica */
        <div className="space-y-6">
          {/* Métricas Globales de Faltantes */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3.5">
            <SummaryKpi
              icon={<Layers size={16} />}
              title="Pasillos Activos"
              value={dashboard.total_aisles}
              subtitle="Góndolas con fallas"
              colorClass="text-cyan-400"
              bgClass="bg-slate-800/70 border-cyan-500/20"
            />
            <SummaryKpi
              icon={<ShieldAlert size={16} />}
              title="Críticos (>20%)"
              value={dashboard.aisles_critical}
              subtitle="Reposición total"
              colorClass="text-red-400"
              bgClass="bg-red-950/20 border-red-500/30"
            />
            <SummaryKpi
              icon={<AlertTriangle size={16} />}
              title="Moderados (10-20%)"
              value={dashboard.aisles_moderate}
              subtitle="Atención rápida"
              colorClass="text-amber-400"
              bgClass="bg-amber-950/20 border-amber-500/30"
            />
            <SummaryKpi
              icon={<PackageX size={16} />}
              title="Total Faltantes"
              value={dashboard.total_missing}
              subtitle={`De ${dashboard.total_spaces} espacios`}
              colorClass="text-rose-400"
              bgClass="bg-slate-800/70"
            />
            <SummaryKpi
              icon={<TrendingDown size={16} />}
              title="% Faltante Global"
              value={`${dashboard.overall_missing_pct.toFixed(1)}%`}
              subtitle="Nivel promedio"
              colorClass="text-orange-400"
              bgClass="bg-slate-800/70"
            />
          </div>

          {/* Gráfico Analítico de Stock y Faltantes */}
          <StockAnalyticsChart
            analytics={dashboard.analytics}
            totalAisles={dashboard.total_aisles}
          />

          {/* Grid de Pasillos (AisleCard) */}
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 inline-block" />
                Alertas y Pasillos con Fallas Detectadas ({dashboard.aisles.length})
              </h2>
              <span className="text-xs text-slate-400 font-medium">
                Al resolver Pasillo 1, Pasillo 2 se convierte automáticamente en el nuevo Pasillo 1.
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {dashboard.aisles.map((aisle) => (
                <AisleCard
                  key={aisle.filename || aisle.location_id}
                  aisle={aisle}
                  onAlertSent={() => fetchDashboard()}
                  onResolved={() => fetchDashboard()}
                />
              ))}
            </div>
          </section>
        </div>
      )}

      {/* 4. Hardware & Telemetría del Sistema (al final del Dashboard, visualmente separado) */}
      <section className="pt-8 border-t border-slate-800/80">
        <div className="mb-4">
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-slate-500 inline-block" />
            Hardware & Telemetría del Sistema
          </h2>
          <p className="text-[11px] text-slate-500">
            Diagnóstico de infraestructura, latencias de procesamiento y consumo de recursos.
          </p>
        </div>
        {telemetry?.system ? (
          <SystemMonitor system={telemetry.system} />
        ) : (
          <div className="p-4 bg-slate-900/60 rounded-xl border border-slate-800 text-xs text-slate-500 text-center">
            Telemetría de hardware no disponible en este momento.
          </div>
        )}
      </section>
    </div>
  );
};
