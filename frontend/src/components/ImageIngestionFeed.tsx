import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  FolderCheck,
  Inbox,
  Radio,
  RefreshCw,
  WifiOff,
} from 'lucide-react';
import { api } from '../services/api';
import { UploadAnalysisResponse } from '../types';

const mergeBatches = (
  current: UploadAnalysisResponse[],
  incoming: UploadAnalysisResponse[],
): UploadAnalysisResponse[] =>
  Array.from(
    new Map([...incoming, ...current].map((batch) => [batch.batch_id, batch])).values(),
  )
    .sort((a, b) => Date.parse(b.received_at) - Date.parse(a.received_at))
    .slice(0, 20);

export const ImageIngestionFeed: React.FC = () => {
  const [batches, setBatches] = useState<UploadAnalysisResponse[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let reconnectTimeout: number | undefined;
    let socket: WebSocket | null = null;

    api.getImageAnalysisHistory()
      .then((history) => {
        if (active) {
          setBatches((current) => mergeBatches(current, history));
          setErrorMessage(null);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setErrorMessage(error instanceof Error ? error.message : 'Error al cargar resultados');
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    const connect = () => {
      if (!active) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(`${protocol}//${window.location.host}/ws/image-analysis`);

      socket.onopen = () => {
        if (active) setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const message: { type?: string; batch?: UploadAnalysisResponse } = JSON.parse(event.data);
          const batch = message.batch;
          if (message.type === 'image_analysis' && batch?.batch_id) {
            setBatches((current) => mergeBatches(current, [batch]));
          }
        } catch (error) {
          console.error('Error al leer el resultado de análisis recibido:', error);
        }
      };

      socket.onclose = () => {
        if (active) {
          setIsConnected(false);
          reconnectTimeout = window.setTimeout(connect, 2000);
        }
      };

      socket.onerror = () => socket?.close();
    };

    connect();

    return () => {
      active = false;
      if (reconnectTimeout !== undefined) window.clearTimeout(reconnectTimeout);
      socket?.close();
    };
  }, []);

  return (
    <section className="mb-8 rounded-2xl border border-slate-700/80 bg-slate-800/90 p-6 shadow-xl backdrop-blur-sm">
      <div className="flex flex-col gap-3 border-b border-slate-700/60 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/10 p-2.5 text-cyan-400">
            <Inbox className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold tracking-tight text-white">Recepción automática de imágenes</h2>
            <p className="text-xs text-slate-400">
              El servidor externo envía imágenes para análisis YOLOv8; los resultados aparecen aquí en vivo.
            </p>
          </div>
        </div>
        <div className={`flex w-fit items-center gap-2 rounded-lg border px-3 py-1.5 text-xs ${
          isConnected
            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
            : 'border-slate-600/50 bg-slate-900/50 text-slate-400'
        }`}>
          {isConnected ? <Radio className="h-3.5 w-3.5 animate-pulse" /> : <WifiOff className="h-3.5 w-3.5" />}
          {isConnected ? 'Canal de resultados conectado' : 'Conectando al canal de resultados…'}
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-slate-700/60 bg-slate-900/50 p-4">
        <p className="text-xs font-semibold text-slate-200">Contrato para el servidor emisor</p>
        <p className="mt-1 text-xs text-slate-400">
          Envíe una o varias imágenes con una petición multipart al endpoint de esta aplicación:
        </p>
        <code className="mt-2 block overflow-x-auto rounded-lg bg-slate-950 px-3 py-2 text-[11px] text-cyan-300">
          curl -X POST "http://&lt;HOST&gt;:8000/api/stock/upload" -F "files=@foto1.jpg" -F "files=@foto2.jpg"
        </code>
        <p className="mt-2 text-[11px] text-slate-500">
          La respuesta HTTP contiene el lote analizado. El Dashboard también recibe los resultados por WebSocket
          en <code className="text-slate-300">/ws/image-analysis</code>. Se conservan los últimos 20 lotes en memoria.
        </p>
      </div>

      <div className="mt-5 flex items-center justify-between">
        <h3 className="text-sm font-bold text-white">Resultados recibidos</h3>
        <span className="text-[11px] text-slate-500">Últimos {batches.length} lotes</span>
      </div>

      {errorMessage && (
        <div className="mt-3 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {errorMessage}
        </div>
      )}

      {isLoading ? (
        <div className="mt-4 flex items-center gap-2 py-6 text-xs text-slate-400">
          <RefreshCw className="h-4 w-4 animate-spin" /> Cargando historial de análisis…
        </div>
      ) : batches.length === 0 ? (
        <div className="mt-4 rounded-xl border border-dashed border-slate-700 p-8 text-center">
          <Inbox className="mx-auto h-8 w-8 text-slate-500" />
          <p className="mt-2 text-sm font-medium text-slate-300">Esperando las primeras imágenes</p>
          <p className="mt-1 text-xs text-slate-500">
            Cuando el servidor emisor publique un lote, sus resultados aparecerán aquí automáticamente.
          </p>
        </div>
      ) : (
        <div className="mt-3 max-h-[34rem] space-y-3 overflow-y-auto pr-1">
          {batches.map((batch) => (
            <article key={batch.batch_id} className="rounded-xl border border-slate-700/70 bg-slate-900/60 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/60 pb-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
                  <Clock3 className="h-3.5 w-3.5 text-cyan-400" />
                  {new Date(batch.received_at).toLocaleString('es-CL')}
                  <span className="font-mono text-[10px] text-slate-500">#{batch.batch_id.slice(0, 8)}</span>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-[10px] font-semibold">
                  <span className="rounded border border-slate-600 bg-slate-800 px-2 py-1 text-slate-300">
                    {batch.total_analyzed} analizadas
                  </span>
                  <span className="rounded border border-rose-500/30 bg-rose-500/10 px-2 py-1 text-rose-300">
                    {batch.faults_detected} con faltantes
                  </span>
                  <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-emerald-300">
                    {batch.discarded_clean} stock correcto
                  </span>
                  {batch.failed_count > 0 && (
                    <span className="rounded border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-amber-300">
                      {batch.failed_count} con error
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-3 space-y-2">
                {batch.results.map((result, index) => {
                  const failed = result.processing_error;
                  const hasMissing = result.saved_to_historica && !failed;
                  return (
                    <div
                      key={`${batch.batch_id}-${index}`}
                      className={`flex flex-col gap-2 rounded-lg border p-3 text-xs sm:flex-row sm:items-center sm:justify-between ${
                        failed
                          ? 'border-amber-500/30 bg-amber-950/20 text-amber-200'
                          : hasMissing
                            ? 'border-rose-500/30 bg-rose-950/20 text-rose-200'
                            : 'border-emerald-500/30 bg-emerald-950/20 text-emerald-200'
                      }`}
                    >
                      <div className="flex min-w-0 items-center gap-2">
                        {failed ? (
                          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                        ) : hasMissing ? (
                          <FolderCheck className="h-4 w-4 shrink-0 text-rose-400" />
                        ) : (
                          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                        )}
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-white">{result.filename}</p>
                          <p className="truncate opacity-80">{result.message}</p>
                        </div>
                      </div>
                      <span className="shrink-0 font-mono text-[10px] font-bold">
                        {failed
                          ? 'ERROR DE ANÁLISIS'
                          : hasMissing
                            ? `${result.missing_count} FALTANTES (${result.missing_percentage}%)`
                            : 'STOCK CORRECTO'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
};
