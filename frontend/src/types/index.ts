export type AppState = 'CONNECTED' | 'DISCONNECTED' | 'RUNNING' | 'TRAINING' | 'VALIDATING' | 'ALERT';

export interface CameraInfo {
  status: 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED' | 'ERROR';
  fps: number;
  resolution: {
    width: number;
    height: number;
  };
  source: string;
}

export interface ModelTimings {
  preprocess_ms: number;
  inference_ms: number;
  postprocess_ms: number;
  total_ms: number;
}

export interface ModelTelemetry {
  version: string;
  inference_fps: number;
  confidence_threshold: number;
  iou_threshold: number;
  timings: ModelTimings;
}

export interface InventoryTelemetry {
  products: number;
  missing: number;
  total_spaces: number;
  occupancy_rate: number;
  empty_rate: number;
  roi_applied: boolean;
}

export interface AlertEvent {
  id: string;
  timestamp: string;
  empty_rate: number;
  occupancy_rate: number;
  products: number;
  missing: number;
  snapshot_filename?: string;
  snapshot_url?: string;
  detections_count: number;
  message: string;
}

export interface AlertTelemetry {
  is_active: boolean;
  consecutive_seconds_high: number;
  cooldown_remaining_seconds: number;
  empty_rate: number;
  threshold: number;
  last_alert?: AlertEvent | null;
}

export interface SystemTelemetry {
  cpu: {
    percent: number;
    cores: number;
  };
  ram: {
    used_gb: number;
    total_gb: number;
    percent: number;
  };
  gpu: {
    available: boolean;
    name: string;
    device_count: number;
    vram_allocated_mb: number;
    vram_reserved_mb: number;
    vram_total_mb: number;
  };
}

export interface TelemetryMessage {
  timestamp: number;
  camera: CameraInfo;
  model: ModelTelemetry;
  inventory: InventoryTelemetry;
  alert: AlertTelemetry;
  system: SystemTelemetry;
}

export interface ModelVersionInfo {
  version: string;
  name: string;
  status: 'production' | 'candidate' | 'archive';
  classes: Record<string, string>;
  task: string;
  base_model?: string;
  confidence_threshold: number;
  iou_threshold: number;
  metrics?: {
    mAP50?: number;
    mAP50_95?: number;
    precision?: number;
    recall?: number;
    [key: string]: any;
  };
  created_at: string;
  parent_model?: string;
  path: string;
}

export interface BBoxAnnotation {
  id?: string;
  class_id: number;
  class_name: string;
  confidence: number;
  box: [number, number, number, number];
}

export interface DatasetItem {
  id: string;
  stage: 'collected' | 'pending_review' | 'approved' | 'rejected' | 'validation';
  image_url: string;
  image_path: string;
  timestamp: string;
  source: string;
  model_version: string;
  detections: BBoxAnnotation[];
  empty_rate: number;
  tags: string[];
}

export interface TrainingStatus {
  status: 'idle' | 'preparing' | 'training' | 'evaluating' | 'completed' | 'failed';
  progress_percent: number;
  current_epoch: number;
  total_epochs: number;
  message: string;
  candidate_version?: string;
  metrics?: Record<string, any>;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

// ---------------------------------------------------------------------------
// Stock & Incident Management (nuevas entidades)
// ---------------------------------------------------------------------------

export type SeverityLevel = 'LOW' | 'MODERATE' | 'CRITICAL';
export type IncidentStatus = 'ACTIVE' | 'RESOLVED';
export type AlertSendStatus = 'pending' | 'sent' | 'failed';

export interface SeverityInfo {
  severity: SeverityLevel;
  status: string;
  action: string;
  message: string;
}

export interface StockMetrics {
  expected_count: number;
  missing_count: number;
  remaining_count: number;
  missing_percentage: number;
  remaining_percentage: number;
}

export interface AisleStatus {
  location_id: string;
  display_order: number;
  display_name: string;   // Título Principal: "Alerta 1", "Alerta 2", ...
  aisle_name?: string;    // Sub-etiqueta: "Pasillo 1", "Pasillo 2", ...
  filename?: string;
  image_url?: string;
  stock: StockMetrics;
  severity_info: SeverityInfo;
  /** Estado de stock clasificado explícitamente:
   *  "SIN_STOCK"      → 0 detecciones, góndola completamente vacía
   *  "FALTA_PRODUCTO" → hay missing > 0
   *  "STOCK_CORRECTO" → solo products, sin missing
   */
  stock_status: 'SIN_STOCK' | 'FALTA_PRODUCTO' | 'STOCK_CORRECTO';
  debug_info?: {
    camera_id: string;
    shelf_id: string;
    filename?: string;
    detections_count: number;
    valid_detections_count: number;
    valid_products_count: number;
    valid_missing_count: number;
    confidence_scores: number[];
    average_confidence: number;
    estimated_occupancy: string;
    final_stock_status: string;
  };
  active_incident_id: string | null;
  has_active_incident: boolean;
  last_detected_at: string | null;
  alert_sent?: boolean;
}

export interface StockChartCategory {
  key: string;
  name: string;
  label: string;
  range_label: string;
  count: number;
  color: string;
  percentage: number;
}

export interface StockAnalyticsSummary {
  total_active_alerts: number;
  average_depletion_pct: number;
  urgent_count: number;
  quick_attention_count: number;
  emptying_count: number;
  categories: StockChartCategory[];
}

export interface DashboardSummary {
  is_active: boolean;
  message?: string;
  total_aisles: number;
  aisles_critical: number;
  aisles_moderate: number;
  aisles_low: number;
  aisles_ok: number;
  total_missing: number;
  total_spaces: number;
  overall_missing_pct: number;
  active_incidents: number;
  aisles: AisleStatus[];
  analytics?: StockAnalyticsSummary;
}


export interface ImageAnalysisDetail {
  filename: string;
  saved_to_historica: boolean;
  missing_count: number;
  product_count: number;
  expected_count: number;
  missing_percentage: number;
  severity: SeverityLevel | null;
  message: string;
}

export interface UploadAnalysisResponse {
  total_analyzed: number;
  faults_detected: number;
  discarded_clean: number;
  results: ImageAnalysisDetail[];
  dashboard_active: boolean;
}

export interface IncidentSummary {
  id: string;
  location_id: string;
  display_name: string;
  missing_percentage: number;
  missing_count: number;
  expected_count: number;
  remaining_count: number;
  severity: SeverityLevel;
  status: IncidentStatus;
  created_at: string;
  resolved_at: string | null;
  image_url: string | null;
  alert_sent: boolean;
}

export interface LocationData {
  id: string;
  name: string;
  display_order: number;
  display_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReplenishmentAlertRecord {
  id: string;
  incident_id: string;
  channel: string;
  payload: Record<string, any>;
  status: AlertSendStatus;
  sent_at: string | null;
  error_message: string | null;
}
