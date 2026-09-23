import os
import time
import json
import uuid
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import cv2
import numpy as np

from backend.app.core.logging import logger
from backend.app.core.config import BASE_DIR, settings
from backend.app.schemas.dataset import DatasetItem, BBoxAnnotation
from backend.app.schemas.detection import DetectionResult

class DatasetService:
    """Gestor del ciclo de vida de Active Learning (collected -> pending_review -> approved / rejected -> validation)."""

    def __init__(self):
        self.data_dir = BASE_DIR / "data"
        self.collected_dir = self.data_dir / "collected"
        self.pending_dir = self.data_dir / "pending_review"
        self.approved_dir = self.data_dir / "approved"
        self.rejected_dir = self.data_dir / "rejected"
        self.validation_dir = self.data_dir / "validation"

        for d in [self.collected_dir, self.pending_dir, self.approved_dir, self.rejected_dir, self.validation_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self._last_capture_time = 0.0

    def should_auto_collect(self, det_result: DetectionResult, empty_rate: float) -> Optional[str]:
        """Evalúa si el frame actual debe capturarse para Active Learning."""
        if not settings.active_learning.auto_collect:
            return None

        now = time.time()
        if now - self._last_capture_time < settings.active_learning.min_seconds_between_captures:
            return None

        # Condición 1: Detección con confianza baja (incertidumbre del modelo)
        low_conf = any(
            d.confidence < settings.active_learning.low_confidence_threshold
            for d in det_result.detections
        )
        if low_conf:
            return "low_confidence"

        # Condición 2: Alta tasa de missing inusual
        if empty_rate >= settings.active_learning.high_missing_threshold and len(det_result.detections) >= 3:
            return "high_missing"

        return None

    def capture_sample(
        self,
        frame: np.ndarray,
        det_result: DetectionResult,
        empty_rate: float,
        reason: str = "manual",
        source: str = "camera",
        stage: str = "pending_review"
    ) -> DatasetItem:
        """Guarda la imagen y sus metadatos en disco en la etapa indicada (por defecto pending_review para revisión humana)."""
        sample_id = str(uuid.uuid4())[:8]
        ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        ts_unix = int(time.time())

        target_dir = self.pending_dir if stage == "pending_review" else self.collected_dir
        img_filename = f"sample_{sample_id}_{ts_unix}.jpg"
        meta_filename = f"sample_{sample_id}_{ts_unix}.json"

        img_path = target_dir / img_filename
        meta_path = target_dir / meta_filename

        # Guardar imagen en disco
        cv2.imwrite(str(img_path), frame)

        # Convertir detecciones al formato de anotación
        annotations: List[BBoxAnnotation] = []
        for d in det_result.detections:
            annotations.append(BBoxAnnotation(
                id=str(uuid.uuid4())[:6],
                class_id=d.class_id,
                class_name=d.class_name,
                confidence=d.confidence,
                box=d.box
            ))

        item_data = {
            "id": sample_id,
            "stage": stage,
            "image_filename": img_filename,
            "image_url": f"/api/dataset/images/{stage}/{img_filename}",
            "image_path": str(img_path),
            "timestamp": ts_str,
            "source": source,
            "model_version": det_result.model_version,
            "detections": [a.model_dump() for a in annotations],
            "empty_rate": empty_rate,
            "tags": [reason]
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(item_data, f, indent=2)

        self._last_capture_time = time.time()
        logger.info(f"Muestra Active Learning guardada ({reason}) en '{stage}': {sample_id}")
        return DatasetItem(**item_data)

    def _get_stage_dir(self, stage: str) -> Path:
        mapping = {
            "collected": self.collected_dir,
            "pending_review": self.pending_dir,
            "approved": self.approved_dir,
            "rejected": self.rejected_dir,
            "validation": self.validation_dir
        }
        return mapping.get(stage, self.pending_dir)

    def list_samples(self, stage: str = "pending_review") -> List[DatasetItem]:
        sdir = self._get_stage_dir(stage)
        items: List[DatasetItem] = []

        if not sdir.exists():
            return items

        for mfile in sorted(sdir.glob("*.json"), reverse=True):
            try:
                with open(mfile, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Actualizar URL relativa por si cambió de etapa
                    img_name = data.get("image_filename")
                    data["image_url"] = f"/api/dataset/images/{stage}/{img_name}"
                    items.append(DatasetItem(**data))
            except Exception as e:
                logger.warning(f"Error leyendo muestra {mfile}: {e}")

        return items

    def get_sample(self, stage: str, sample_id: str) -> Optional[DatasetItem]:
        sdir = self._get_stage_dir(stage)
        for mfile in sdir.glob(f"sample_{sample_id}_*.json"):
            try:
                with open(mfile, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["image_url"] = f"/api/dataset/images/{stage}/{data.get('image_filename')}"
                    return DatasetItem(**data)
            except Exception:
                pass
        return None

    def update_annotations(self, stage: str, sample_id: str, annotations: List[BBoxAnnotation]) -> Optional[DatasetItem]:
        sdir = self._get_stage_dir(stage)
        for mfile in sdir.glob(f"sample_{sample_id}_*.json"):
            with open(mfile, "r", encoding="utf-8") as f:
                data = json.load(f)

            data["detections"] = [a.model_dump() for a in annotations]
            with open(mfile, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            data["image_url"] = f"/api/dataset/images/{stage}/{data.get('image_filename')}"
            return DatasetItem(**data)
        return None

    def transition_sample(self, sample_id: str, from_stage: str, to_stage: str) -> bool:
        """Mueve imagen y metadatos de una etapa a otra (ej. pending_review -> approved o rejected)."""
        src_dir = self._get_stage_dir(from_stage)
        dst_dir = self._get_stage_dir(to_stage)

        meta_file = None
        for mf in src_dir.glob(f"sample_{sample_id}_*.json"):
            meta_file = mf
            break

        if not meta_file:
            return False

        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        img_filename = data.get("image_filename")
        src_img = src_dir / img_filename
        dst_img = dst_dir / img_filename
        dst_meta = dst_dir / meta_file.name

        if src_img.exists():
            shutil.move(str(src_img), str(dst_img))

        data["stage"] = to_stage
        data["image_path"] = str(dst_img)
        data["image_url"] = f"/api/dataset/images/{to_stage}/{img_filename}"
        data["reviewed_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        # Si se aprueba, generar también el archivo de etiqueta YOLO (.txt) en formato normalizado
        if to_stage == "approved":
            self._save_yolo_label(dst_dir, img_filename, data.get("detections", []))

        with open(dst_meta, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        if meta_file.exists():
            meta_file.unlink()

        logger.info(f"Muestra '{sample_id}' movida de {from_stage} a {to_stage}")
        return True

    def _save_yolo_label(self, target_dir: Path, image_filename: str, detections: List[Dict[str, Any]]) -> None:
        """Genera el archivo .txt con formato YOLO (class_id cx cy w h normalizado)."""
        txt_name = Path(image_filename).stem + ".txt"
        txt_path = target_dir / txt_name
        
        # Necesitamos las dimensiones de la imagen para normalizar
        img_path = target_dir / image_filename
        if not img_path.exists():
            return
            
        img = cv2.imread(str(img_path))
        if img is None:
            return
        h, w = img.shape[:2]

        lines = []
        for d in detections:
            cls_id = d.get("class_id", 0)
            box = d.get("box", [])
            if len(box) == 4 and w > 0 and h > 0:
                x1, y1, x2, y2 = box
                cx = ((x1 + x2) / 2.0) / w
                cy = ((y1 + y2) / 2.0) / h
                bw = (x2 - x1) / w
                bh = (y2 - y1) / h
                # Asegurar rangos [0.0, 1.0]
                cx = max(0.0, min(1.0, cx))
                cy = max(0.0, min(1.0, cy))
                bw = max(0.0, min(1.0, bw))
                bh = max(0.0, min(1.0, bh))
                lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def get_stats(self) -> Dict[str, int]:
        return {
            "collected": len(list(self.collected_dir.glob("*.json"))),
            "pending_review": len(list(self.pending_dir.glob("*.json"))),
            "approved": len(list(self.approved_dir.glob("*.json"))),
            "rejected": len(list(self.rejected_dir.glob("*.json"))),
            "validation": len(list(self.validation_dir.glob("*.json")))
        }

dataset_service = DatasetService()
