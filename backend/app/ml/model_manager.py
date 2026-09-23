import os
import time
import json
import shutil
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import torch
from ultralytics import YOLO

from backend.app.core.logging import logger
from backend.app.core.config import BASE_DIR, settings
from backend.app.schemas.detection import DetectionItem, DetectionResult, TimingMetrics
from backend.app.schemas.model import ModelVersionInfo

class ModelManager:
    """Administrador thread-safe para carga, inferencia, hot-swap y rollback de modelos YOLOv8."""

    def __init__(self, production_path: Optional[str] = None):
        self._lock = threading.RLock()
        self.production_dir = BASE_DIR / "models" / "production"
        self.candidates_dir = BASE_DIR / "models" / "candidates"
        self.archive_dir = BASE_DIR / "models" / "archive"
        
        self.production_path = Path(production_path) if production_path else self.production_dir / "best.pt"
        if not self.production_path.is_absolute():
            self.production_path = BASE_DIR / self.production_path
            
        self.device = self._resolve_device(settings.model.device)
        self.confidence_threshold = settings.model.default_confidence
        self.iou_threshold = settings.model.default_iou
        
        self.model: Optional[YOLO] = None
        self.classes: Dict[int, str] = {0: "missing", 1: "product"}
        self.metadata: Dict[str, Any] = {}
        self.active_version = "v001"
        
        # Carga inicial
        self._load_active_model()

    def _resolve_device(self, configured: str) -> str:
        if configured == "auto" or not configured:
            return "cuda" if torch.cuda.is_available() else "cpu"
        return configured

    def _load_active_model(self) -> None:
        with self._lock:
            if not self.production_path.exists():
                logger.error(f"Modelo de producción no encontrado en {self.production_path}")
                raise FileNotFoundError(f"No existe el archivo {self.production_path}")
                
            logger.info(f"Cargando modelo YOLOv8 desde {self.production_path} en dispositivo '{self.device}'...")
            self.model = YOLO(str(self.production_path))
            
            # Obtener clases del modelo
            if hasattr(self.model, "names") and self.model.names:
                self.classes = {int(k): str(v) for k, v in self.model.names.items()}
                logger.info(f"Clases detectadas en el modelo: {self.classes}")
                
            # Cargar metadatos si existen
            meta_path = self.production_dir / "metadata.json"
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        self.metadata = json.load(f)
                        self.active_version = self.metadata.get("model_version", "v001")
                except Exception as e:
                    logger.warning(f"No se pudieron leer metadatos de {meta_path}: {e}")
            else:
                self.metadata = {
                    "model_version": "v001",
                    "model_name": "YOLOv8n-EmptySpaces",
                    "classes": self.classes,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "production"
                }
            logger.info(f"Modelo versión {self.active_version} cargado exitosamente.")

    def update_thresholds(self, confidence: Optional[float] = None, iou: Optional[float] = None) -> Dict[str, float]:
        with self._lock:
            if confidence is not None:
                self.confidence_threshold = max(0.01, min(1.0, float(confidence)))
            if iou is not None:
                self.iou_threshold = max(0.01, min(1.0, float(iou)))
            return {
                "confidence": self.confidence_threshold,
                "iou": self.iou_threshold
            }

    def predict(self, frame: np.ndarray) -> DetectionResult:
        """Ejecuta inferencia midiendo preprocess, inference y postprocess."""
        with self._lock:
            if self.model is None:
                return DetectionResult(model_version=self.active_version)

            h, w = frame.shape[:2]
            
            # Ultralytics predict devuelve un objeto Results que ya cronometra speeds:
            # results[0].speed -> {'preprocess': ms, 'inference': ms, 'postprocess': ms}
            t0 = time.perf_counter()
            results = self.model.predict(
                source=frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False
            )
            t_end = time.perf_counter()
            total_elapsed_ms = (t_end - t0) * 1000.0

            detections: List[DetectionItem] = []
            timings = TimingMetrics(total_ms=round(total_elapsed_ms, 2))

            if results and len(results) > 0:
                res = results[0]
                if hasattr(res, "speed") and isinstance(res.speed, dict):
                    timings.preprocess_ms = round(res.speed.get("preprocess", 0.0), 2)
                    timings.inference_ms = round(res.speed.get("inference", 0.0), 2)
                    timings.postprocess_ms = round(res.speed.get("postprocess", 0.0), 2)

                if res.boxes is not None and len(res.boxes) > 0:
                    boxes_xyxy = res.boxes.xyxy.cpu().numpy()
                    confs = res.boxes.conf.cpu().numpy()
                    cls_ids = res.boxes.cls.cpu().numpy().astype(int)

                    for box, conf, cls_id in zip(boxes_xyxy, confs, cls_ids):
                        cls_name = self.classes.get(cls_id, f"class_{cls_id}")
                        detections.append(DetectionItem(
                            class_id=int(cls_id),
                            class_name=cls_name,
                            confidence=round(float(conf), 4),
                            box=[round(float(v), 2) for v in box]
                        ))

            return DetectionResult(
                detections=detections,
                timings=timings,
                model_version=self.active_version,
                frame_width=w,
                frame_height=h
            )

    def get_info(self) -> ModelVersionInfo:
        with self._lock:
            return ModelVersionInfo(
                version=self.active_version,
                name=self.metadata.get("model_name", "YOLOv8n"),
                status="production",
                classes={str(k): v for k, v in self.classes.items()},
                task="detect",
                base_model=self.metadata.get("base_model", "yolov8n.pt"),
                confidence_threshold=self.confidence_threshold,
                iou_threshold=self.iou_threshold,
                metrics=self.metadata.get("metrics"),
                created_at=self.metadata.get("created_at", ""),
                parent_model=self.metadata.get("parent_model"),
                path=str(self.production_path)
            )

    def list_versions(self) -> Dict[str, List[ModelVersionInfo]]:
        """Lista modelos en producción, candidatos y archivo."""
        with self._lock:
            res: Dict[str, List[ModelVersionInfo]] = {
                "production": [self.get_info()],
                "candidates": [],
                "archive": []
            }

            # Candidatos
            if self.candidates_dir.exists():
                for cdir in sorted(self.candidates_dir.iterdir()):
                    if cdir.is_dir() and (cdir / "best.pt").exists():
                        meta = {}
                        mpath = cdir / "metadata.json"
                        if mpath.exists():
                            try:
                                with open(mpath, "r", encoding="utf-8") as f:
                                    meta = json.load(f)
                            except Exception:
                                pass
                        res["candidates"].append(ModelVersionInfo(
                            version=meta.get("model_version", cdir.name),
                            name=meta.get("model_name", f"Candidate {cdir.name}"),
                            status="candidate",
                            classes={str(k): v for k, v in meta.get("classes", self.classes).items()},
                            confidence_threshold=meta.get("confidence_threshold", self.confidence_threshold),
                            iou_threshold=meta.get("iou_threshold", self.iou_threshold),
                            metrics=meta.get("metrics"),
                            created_at=meta.get("created_at", ""),
                            parent_model=meta.get("parent_model"),
                            path=str(cdir / "best.pt")
                        ))

            # Archivo
            if self.archive_dir.exists():
                for adir in sorted(self.archive_dir.iterdir(), reverse=True):
                    if adir.is_dir() and (adir / "best.pt").exists():
                        meta = {}
                        mpath = adir / "metadata.json"
                        if mpath.exists():
                            try:
                                with open(mpath, "r", encoding="utf-8") as f:
                                    meta = json.load(f)
                            except Exception:
                                pass
                        res["archive"].append(ModelVersionInfo(
                            version=meta.get("model_version", adir.name),
                            name=meta.get("model_name", f"Archive {adir.name}"),
                            status="archive",
                            classes={str(k): v for k, v in meta.get("classes", self.classes).items()},
                            confidence_threshold=meta.get("confidence_threshold", self.confidence_threshold),
                            iou_threshold=meta.get("iou_threshold", self.iou_threshold),
                            metrics=meta.get("metrics"),
                            created_at=meta.get("created_at", ""),
                            parent_model=meta.get("parent_model"),
                            path=str(adir / "best.pt")
                        ))

            return res

    def hot_swap(self, candidate_version: str) -> bool:
        """Promueve un candidato a producción sin reiniciar el servidor."""
        with self._lock:
            cand_dir = self.candidates_dir / candidate_version
            cand_model = cand_dir / "best.pt"
            if not cand_model.exists():
                raise FileNotFoundError(f"Candidato '{candidate_version}' no encontrado en {cand_dir}")

            # 1. Archivar versión actual
            curr_ver = self.active_version
            archive_target = self.archive_dir / curr_ver
            archive_target.mkdir(parents=True, exist_ok=True)
            if self.production_path.exists():
                shutil.copy2(self.production_path, archive_target / "best.pt")
            curr_meta_path = self.production_dir / "metadata.json"
            if curr_meta_path.exists():
                shutil.copy2(curr_meta_path, archive_target / "metadata.json")
            logger.info(f"Versión de producción previa '{curr_ver}' archivada en {archive_target}")

            # 2. Copiar candidato a producción
            shutil.copy2(cand_model, self.production_path)
            cand_meta_path = cand_dir / "metadata.json"
            if cand_meta_path.exists():
                with open(cand_meta_path, "r", encoding="utf-8") as f:
                    cand_meta = json.load(f)
                cand_meta["status"] = "production"
                cand_meta["activated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                with open(self.production_dir / "metadata.json", "w", encoding="utf-8") as f:
                    json.dump(cand_meta, f, indent=2)

            # 3. Recargar modelo en memoria sin interrumpir el proceso
            self._load_active_model()
            logger.info(f"Hot-swap completado exitosamente a la versión '{self.active_version}'")
            return True

    def rollback(self, archive_version: str) -> bool:
        """Restaura una versión previamente archivada."""
        with self._lock:
            arch_dir = self.archive_dir / archive_version
            arch_model = arch_dir / "best.pt"
            if not arch_model.exists():
                raise FileNotFoundError(f"Versión archivada '{archive_version}' no encontrada en {arch_dir}")

            # 1. Archivar la versión actual antes de rollback
            curr_ver = self.active_version
            backup_target = self.archive_dir / f"{curr_ver}_pre_rollback"
            backup_target.mkdir(parents=True, exist_ok=True)
            if self.production_path.exists():
                shutil.copy2(self.production_path, backup_target / "best.pt")
            if (self.production_dir / "metadata.json").exists():
                shutil.copy2(self.production_dir / "metadata.json", backup_target / "metadata.json")

            # 2. Copiar versión restaurada a producción
            shutil.copy2(arch_model, self.production_path)
            arch_meta_path = arch_dir / "metadata.json"
            if arch_meta_path.exists():
                with open(arch_meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["status"] = "production"
                meta["restored_from"] = archive_version
                meta["restored_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                with open(self.production_dir / "metadata.json", "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)

            # 3. Recargar modelo
            self._load_active_model()
            logger.info(f"Rollback exitoso a versión '{archive_version}'")
            return True
