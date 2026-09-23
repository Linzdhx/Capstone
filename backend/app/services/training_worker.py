import os
import sys
import time
import json
import shutil
import random
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
import yaml
from ultralytics import YOLO

from backend.app.core.logging import logger
from backend.app.core.config import BASE_DIR, settings
from backend.app.schemas.dataset import TrainingStatus, TrainingRequest
from backend.app.ml.evaluator import model_evaluator

class TrainingWorker:
    """Worker en segundo plano para preparación de datasets, fine-tuning y evaluación de modelos candidatos."""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

        self.approved_dir = BASE_DIR / "data" / "approved"
        self.validation_dir = BASE_DIR / "data" / "validation"
        self.candidates_dir = BASE_DIR / "models" / "candidates"
        self.production_dir = BASE_DIR / "models" / "production"
        self.workspace_dir = BASE_DIR / "data" / "training_workspace"

        self.status = TrainingStatus(
            status="idle",
            progress_percent=0.0,
            current_epoch=0,
            total_epochs=0,
            message="Worker listo para entrenar"
        )

    def get_status(self) -> TrainingStatus:
        with self._lock:
            return self.status.model_copy()

    def start_training(self, req: TrainingRequest) -> bool:
        """Inicia el proceso de fine-tuning asíncrono si no hay otro en ejecución."""
        with self._lock:
            if self.status.status in ["training", "evaluating", "preparing"]:
                logger.warning("Intento de iniciar entrenamiento mientras otro está en ejecución.")
                return False

            # Verificar cantidad mínima de muestras aprobadas
            approved_images = list(self.approved_dir.glob("*.jpg")) + list(self.approved_dir.glob("*.png"))
            if len(approved_images) < settings.training.min_approved_samples:
                msg = f"Se requieren al menos {settings.training.min_approved_samples} muestras aprobadas (actuales: {len(approved_images)})"
                self.status = TrainingStatus(
                    status="failed",
                    message=msg,
                    error=msg
                )
                logger.warning(msg)
                return False

            self.status = TrainingStatus(
                status="preparing",
                progress_percent=5.0,
                current_epoch=0,
                total_epochs=req.epochs,
                message="Preparando dataset estructurado YOLO...",
                started_at=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            )

            self._thread = threading.Thread(target=self._run_training_pipeline, args=(req,), daemon=True)
            self._thread.start()
            logger.info("Hilo de entrenamiento iniciado en segundo plano.")
            return True

    def _determine_next_version(self) -> str:
        """Calcula el siguiente número de versión para el candidato (ej: v002)."""
        existing_numbers = []
        for p in [self.production_dir, self.candidates_dir, BASE_DIR / "models" / "archive"]:
            if p.exists():
                for sub in p.iterdir():
                    name = sub.name.lower()
                    if name.startswith("v") and name[1:].isdigit():
                        existing_numbers.append(int(name[1:]))

        next_num = max(existing_numbers, default=1) + 1
        return f"v{next_num:03d}"

    def _prepare_yolo_dataset(self) -> Path:
        """Crea la estructura de carpetas train/val requerida por YOLOv8 con split 80/20."""
        if self.workspace_dir.exists():
            shutil.rmtree(self.workspace_dir)

        train_img_dir = self.workspace_dir / "images" / "train"
        val_img_dir = self.workspace_dir / "images" / "val"
        train_lbl_dir = self.workspace_dir / "labels" / "train"
        val_lbl_dir = self.workspace_dir / "labels" / "val"

        for d in [train_img_dir, val_img_dir, train_lbl_dir, val_lbl_dir]:
            d.mkdir(parents=True, exist_ok=True)

        approved_images = list(self.approved_dir.glob("*.jpg")) + list(self.approved_dir.glob("*.png"))
        random.seed(42)
        shuffled = list(approved_images)
        random.shuffle(shuffled)

        # Split 80% train, 20% val
        val_count = max(1, int(len(shuffled) * 0.2))
        val_images = set(shuffled[:val_count])

        for img_path in shuffled:
            is_val = img_path in val_images
            dest_img_dir = val_img_dir if is_val else train_img_dir
            dest_lbl_dir = val_lbl_dir if is_val else train_lbl_dir

            # Copiar imagen
            shutil.copy2(img_path, dest_img_dir / img_path.name)

            # Copiar etiqueta .txt si existe
            lbl_name = img_path.stem + ".txt"
            src_lbl = self.approved_dir / lbl_name
            if src_lbl.exists():
                shutil.copy2(src_lbl, dest_lbl_dir / lbl_name)
            else:
                # Si no existe archivo de etiquetas, crear uno vacío
                (dest_lbl_dir / lbl_name).touch()

        # Generar data.yaml con rutas absolutas normalizadas
        data_yaml_content = {
            "path": str(self.workspace_dir.resolve()).replace("\\", "/"),
            "train": "images/train",
            "val": "images/val",
            "names": {
                0: "missing",
                1: "product"
            }
        }

        yaml_path = self.workspace_dir / "data.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data_yaml_content, f, default_flow_style=False)

        return yaml_path

    def _run_training_pipeline(self, req: TrainingRequest) -> None:
        """Flujo desacoplado: preparación -> fine-tuning -> candidato -> evaluación."""
        candidate_ver = self._determine_next_version()
        candidate_dir = self.candidates_dir / candidate_ver
        candidate_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Preparar Dataset
            data_yaml = self._prepare_yolo_dataset()

            with self._lock:
                self.status.status = "training"
                self.status.progress_percent = 15.0
                self.status.candidate_version = candidate_ver
                self.status.message = f"Fine-tuning YOLOv8 ({req.epochs} épocas)..."

            # 2. Base model: preferir el modelo actual de producción
            base_model_path = self.production_dir / "best.pt"
            if not base_model_path.exists():
                base_model_path = BASE_DIR / "yolov8n.pt"

            logger.info(f"Iniciando fine-tuning usando modelo base {base_model_path} en {candidate_dir}")

            model = YOLO(str(base_model_path))
            device = "cuda" if settings.model.device in ["cuda", "auto"] else "cpu"

            # 3. Entrenamiento con Ultralytics
            train_results = model.train(
                data=str(data_yaml),
                epochs=req.epochs,
                batch=req.batch_size,
                imgsz=req.imgsz,
                lr0=req.lr0,
                device=device,
                project=str(self.workspace_dir / "runs"),
                name="fine_tune",
                exist_ok=True,
                verbose=False
            )

            with self._lock:
                self.status.status = "evaluating"
                self.status.progress_percent = 85.0
                self.status.message = "Evaluando modelo candidato frente al conjunto de validación..."

            # 4. Guardar candidato
            trained_best = Path(train_results.save_dir) / "weights" / "best.pt"
            cand_best_path = candidate_dir / "best.pt"

            if trained_best.exists():
                shutil.copy2(trained_best, cand_best_path)
            else:
                raise FileNotFoundError(f"Pesos entrenados no encontrados en {trained_best}")

            # 5. Evaluación con ModelEvaluator
            passed, metrics = model_evaluator.evaluate_model(cand_best_path, data_yaml)

            # 6. Escribir metadatos del candidato
            cand_meta = {
                "model_version": candidate_ver,
                "model_name": req.name or f"YOLOv8n-Custom-{candidate_ver}",
                "status": "candidate",
                "classes": {0: "missing", 1: "product"},
                "task": "detect",
                "base_model": str(base_model_path.name),
                "confidence_threshold": settings.model.default_confidence,
                "iou_threshold": settings.model.default_iou,
                "metrics": metrics,
                "evaluation_passed": passed,
                "training_dataset": f"Approved dataset ({len(list(self.approved_dir.glob('*.jpg')))} items)",
                "training_config": req.model_dump(),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            }

            with open(candidate_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(cand_meta, f, indent=2)

            with self._lock:
                self.status.status = "completed"
                self.status.progress_percent = 100.0
                self.status.candidate_version = candidate_ver
                self.status.metrics = metrics
                self.status.completed_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                self.status.message = f"Entrenamiento completado exitosamente. Candidato {candidate_ver} listo para revisión/hot-swap."

            logger.info(f"Entrenamiento completado exitosamente para candidato {candidate_ver}")

        except Exception as e:
            err = str(e)
            logger.error(f"Error durante el pipeline de entrenamiento: {err}")
            with self._lock:
                self.status.status = "failed"
                self.status.error = err
                self.status.message = f"Error en entrenamiento: {err}"

training_worker = TrainingWorker()
