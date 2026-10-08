import { ModelVersionInfo, DatasetItem, AlertEvent, TrainingStatus, DashboardSummary, IncidentSummary, LocationData, ReplenishmentAlertRecord, UploadAnalysisResponse } from '../types';

export const api = {
  // Cámara
  async getCameraStatus() {
    const res = await fetch('/api/camera/status');
    return res.json();
  },
  async controlCamera(action: 'start' | 'stop') {
    const res = await fetch('/api/camera/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    });
    return res.json();
  },
  async setCameraSource(source_type: string, webcam_index = 0, rtsp_url = '') {
    const res = await fetch('/api/camera/source', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_type, webcam_index, rtsp_url }),
    });
    return res.json();
  },

  // Inventario y ROI
  async getRoi() {
    const res = await fetch('/api/inventory/roi');
    return res.json();
  },
  async setRoi(roi: number[] | null) {
    const res = await fetch('/api/inventory/roi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ roi }),
    });
    return res.json();
  },

  // Alertas
  async getAlertHistory(limit = 50): Promise<AlertEvent[]> {
    const res = await fetch(`/api/alerts/history?limit=${limit}`);
    return res.json();
  },
  async updateAlertConfig(empty_threshold: number, consecutive_seconds: number, cooldown_seconds: number) {
    const res = await fetch('/api/alerts/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ empty_threshold, consecutive_seconds, cooldown_seconds }),
    });
    return res.json();
  },

  // Modelos
  async listModels(): Promise<{ production: ModelVersionInfo[]; candidates: ModelVersionInfo[]; archive: ModelVersionInfo[] }> {
    const res = await fetch('/api/models');
    return res.json();
  },
  async updateThresholds(confidence: number, iou: number) {
    const res = await fetch('/api/models/thresholds', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confidence, iou }),
    });
    return res.json();
  },
  async hotSwap(version: string) {
    const res = await fetch('/api/models/hot-swap', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ version }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Fallo en Hot-Swap');
    }
    return res.json();
  },
  async rollback(version: string) {
    const res = await fetch('/api/models/rollback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ version }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Fallo en Rollback');
    }
    return res.json();
  },

  // Active Learning & Dataset
  async getDatasetStats(): Promise<Record<string, number>> {
    const res = await fetch('/api/dataset/stats');
    return res.json();
  },
  async listDatasetSamples(stage: string): Promise<DatasetItem[]> {
    const res = await fetch(`/api/dataset/samples?stage=${stage}`);
    return res.json();
  },
  async captureSample() {
    const res = await fetch('/api/dataset/capture', { method: 'POST' });
    return res.json();
  },
  async reviewSample(stage: string, sampleId: string, action: 'approve' | 'reject' | 'update_labels', annotations?: any[]) {
    const res = await fetch(`/api/dataset/review/${stage}/${sampleId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, annotations }),
    });
    return res.json();
  },

  // Entrenamiento
  async getTrainingStatus(): Promise<TrainingStatus> {
    const res = await fetch('/api/training/status');
    return res.json();
  },
  async startTraining(epochs = 50, batch_size = 16, imgsz = 640, lr0 = 0.01) {
    const res = await fetch('/api/training/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ epochs, batch_size, imgsz, lr0 }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error al iniciar entrenamiento');
    }
    return res.json();
  },

  // Sistema
  async getSystemMetrics() {
    const res = await fetch('/api/system/metrics');
    return res.json();
  },

  // ---------------------------------------------------------------------------
  // Stock & Incidents API
  // ---------------------------------------------------------------------------

  async getStockDashboard(): Promise<DashboardSummary> {
    const res = await fetch('/api/stock/dashboard');
    if (!res.ok) throw new Error('Error al cargar el dashboard de stock');
    return res.json();
  },

  async getLocations(activeOnly = true): Promise<LocationData[]> {
    const res = await fetch(`/api/stock/locations?active_only=${activeOnly}`);
    if (!res.ok) throw new Error('Error al cargar ubicaciones');
    return res.json();
  },

  async getIncidents(status?: string, locationId?: string, limit = 100): Promise<IncidentSummary[]> {
    let url = `/api/stock/incidents?limit=${limit}`;
    if (status) url += `&status=${status}`;
    if (locationId) url += `&location_id=${locationId}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Error al cargar incidencias');
    return res.json();
  },

  async resolveIncident(incidentId: string): Promise<any> {
    const res = await fetch(`/api/stock/incidents/${incidentId}/resolve`, {
      method: 'PATCH',
    });
    if (!res.ok) throw new Error('Error al resolver incidencia');
    return res.json();
  },

  async sendReplenishmentAlert(incidentId: string, channel: string = 'webhook'): Promise<ReplenishmentAlertRecord> {
    const res = await fetch(`/api/stock/incidents/${incidentId}/alert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al enviar alerta de reposición');
    }
    return res.json();
  },

  // ---------------------------------------------------------------------------
  // Zona de Análisis & Gestión /historica
  // ---------------------------------------------------------------------------

  async uploadImages(files: File[]): Promise<UploadAnalysisResponse> {
    const formData = new FormData();
    for (const file of files) {
      formData.append('files', file);
    }
    const res = await fetch('/api/stock/upload', {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al procesar las imágenes con YOLOv8');
    }
    return res.json();
  },

  async resolveHistoricaFile(filename: string): Promise<any> {
    const res = await fetch(`/api/stock/historica/${encodeURIComponent(filename)}/resolve`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al resolver la falla');
    }
    return res.json();
  },

  async sendHistoricaAlert(filename: string, channel: string = 'webhook'): Promise<ReplenishmentAlertRecord> {
    const res = await fetch(`/api/stock/historica/${encodeURIComponent(filename)}/alert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ channel }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Error al enviar alerta de reposición');
    }
    return res.json();
  },
};

