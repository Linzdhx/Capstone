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
