import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileImage,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  X,
  Sparkles,
  ArrowRight,
  FolderCheck,
  Trash2,
} from 'lucide-react';
import { api } from '../services/api';
import { UploadAnalysisResponse } from '../types';

interface AnalysisUploadZoneProps {
  onAnalysisComplete: () => void;
}

export const AnalysisUploadZone: React.FC<AnalysisUploadZoneProps> = ({ onAnalysisComplete }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadAnalysisResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const validFiles = Array.from(e.dataTransfer.files).filter((f) =>
        f.type.startsWith('image/')
      );
      if (validFiles.length > 0) {
        setSelectedFiles((prev) => [...prev, ...validFiles]);
        setErrorMessage(null);
      } else {
        setErrorMessage('Solo se admiten archivos de imagen (.jpg, .jpeg, .png, .webp)');
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const validFiles = Array.from(e.target.files).filter((f) =>
        f.type.startsWith('image/')
      );
      setSelectedFiles((prev) => [...prev, ...validFiles]);
      setErrorMessage(null);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadAndAnalyze = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setErrorMessage(null);
    setUploadResult(null);

    try {
      const res = await api.uploadImages(selectedFiles);
      setUploadResult(res);
      setSelectedFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      onAnalysisComplete();
    } catch (err: any) {
      setErrorMessage(err.message || 'Error al procesar las imágenes');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-slate-800/90 border border-slate-700/80 rounded-2xl p-6 shadow-xl backdrop-blur-sm mb-8 transition-all">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-700/60 gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-gradient-to-br from-indigo-500/20 to-cyan-500/20 border border-indigo-500/30 rounded-xl text-cyan-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              Zona de Análisis de Imágenes (YOLOv8)
            </h2>
            <p className="text-xs text-slate-400">
              Sube fotos para detección de stock. Solo las imágenes con fallas se guardan en{' '}
              <code className="bg-slate-900 px-1.5 py-0.5 rounded text-cyan-300 font-mono">/historica</code> para alimentar el Dashboard.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 rounded-lg flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Sin fallas = Descartada
          </span>
          <span className="px-2.5 py-1 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-lg flex items-center gap-1.5">
            <FolderCheck className="w-3.5 h-3.5" />
            Con fallas = /historica
          </span>
        </div>
      </div>

      {/* Dropzone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`mt-5 border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200 ${
          dragActive
            ? 'border-cyan-400 bg-cyan-950/20 scale-[1.01]'
            : 'border-slate-600/60 hover:border-cyan-500/50 bg-slate-900/40 hover:bg-slate-900/60'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="flex flex-col items-center justify-center space-y-2">
          <div className="p-3 bg-slate-800 rounded-full border border-slate-700 text-cyan-400 shadow-md">
            <UploadCloud className="w-6 h-6" />
          </div>
          <div className="text-sm font-medium text-slate-200">
            Arrastra y suelta fotos de góndolas aquí, o{' '}
            <span className="text-cyan-400 underline underline-offset-2">explora tus archivos</span>
          </div>
          <p className="text-xs text-slate-500">
            Admite múltiples capturas en JPG, PNG o WEBP. Inferencia instantánea con modelo YOLOv8.
          </p>
        </div>
      </div>

      {/* Selected files preview */}
      {selectedFiles.length > 0 && (
        <div className="mt-4 p-4 bg-slate-900/70 border border-slate-700/60 rounded-xl">
          <div className="flex items-center justify-between mb-3 text-xs font-semibold text-slate-300">
            <span>Archivos seleccionados ({selectedFiles.length})</span>
            <button
              onClick={() => setSelectedFiles([])}
              className="text-slate-400 hover:text-rose-400 text-xs transition-colors flex items-center gap-1"
            >
              <Trash2 className="w-3 h-3" /> Limpiar todo
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-40 overflow-y-auto pr-1">
            {selectedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 bg-slate-800 border border-slate-700/80 rounded-lg text-xs"
              >
                <div className="flex items-center space-x-2 truncate">
                  <FileImage className="w-4 h-4 text-cyan-400 shrink-0" />
                  <span className="truncate text-slate-300 font-medium">{file.name}</span>
                  <span className="text-slate-500 text-[10px]">
                    ({(file.size / 1024).toFixed(0)} KB)
                  </span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(idx);
                  }}
                  className="text-slate-400 hover:text-rose-400 p-1 rounded"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>

          <div className="mt-4 flex justify-end">
            <button
              onClick={handleUploadAndAnalyze}
              disabled={isUploading}
              className="px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 text-white font-medium text-xs rounded-xl shadow-lg flex items-center space-x-2 transition-all transform active:scale-95"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Analizando con YOLOv8...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Analizar {selectedFiles.length} imagen(es)</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Error display */}
      {errorMessage && (
        <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Analysis results report */}
      {uploadResult && (
        <div className="mt-4 p-4 bg-slate-900/90 border border-slate-700/80 rounded-xl transition-all">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-700/60 text-xs">
            <span className="font-semibold text-white flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-cyan-400" />
              Resultado de Análisis YOLOv8
            </span>
            <div className="flex items-center gap-3">
              <span className="text-slate-400">Total: {uploadResult.total_analyzed}</span>
              <span className="px-2 py-0.5 bg-rose-500/20 text-rose-300 rounded font-semibold border border-rose-500/30">
                {uploadResult.faults_detected} con faltantes (/historica)
              </span>
              <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-300 rounded font-semibold border border-emerald-500/30">
                {uploadResult.discarded_clean} descartadas (OK)
              </span>
            </div>
          </div>

          <div className="mt-3 space-y-2 max-h-48 overflow-y-auto pr-1">
            {uploadResult.results.map((item, i) => (
              <div
                key={i}
                className={`p-2.5 rounded-lg border text-xs flex items-center justify-between ${
                  item.saved_to_historica
                    ? 'bg-rose-950/20 border-rose-500/30 text-rose-200'
                    : 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200'
                }`}
              >
                <div className="flex items-center space-x-2 truncate">
                  {item.saved_to_historica ? (
                    <FolderCheck className="w-4 h-4 text-rose-400 shrink-0" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  )}
                  <span className="font-medium truncate text-white">{item.filename}</span>
                  <span className="text-[11px] opacity-80">{item.message}</span>
                </div>
                <div className="shrink-0 ml-2">
                  {item.saved_to_historica ? (
                    <span className="px-2 py-0.5 bg-rose-500/30 text-rose-200 rounded font-mono text-[10px] font-bold">
                      {item.missing_count} FALTANTES ({item.missing_percentage}%)
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 bg-emerald-500/30 text-emerald-200 rounded font-mono text-[10px] font-bold">
                      STOCK COMPLETO
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
