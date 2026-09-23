import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from ultralytics import YOLO

from backend.app.core.logging import logger
from backend.app.core.config import BASE_DIR, settings

class ModelEvaluator:
    """Evaluador de modelos candidatos YOLOv8 sobre el conjunto de validación."""

    def __init__(self, validation_dir: Optional[Path] = None):
        self.validation_dir = validation_dir or BASE_DIR / "data" / "validation"
        self.pass_threshold_map50 = settings.training.eval_pass_map50

    def evaluate_model(self, model_path: Path, data_yaml_path: Path) -> Tuple[bool, Dict[str, Any]]:
        """Ejecuta YOLO.val() sobre el dataset especificado y calcula métricas."""
        if not model_path.exists():
            raise FileNotFoundError(f"Modelo no encontrado en {model_path}")
        if not data_yaml_path.exists():
            raise FileNotFoundError(f"data.yaml no encontrado en {data_yaml_path}")

        logger.info(f"Iniciando evaluación de modelo {model_path.name} usando {data_yaml_path}...")
        
        try:
            model = YOLO(str(model_path))
            device = "cuda" if settings.model.device == "cuda" or (settings.model.device == "auto") else "cpu"
            
            # Ejecutar validación
            val_results = model.val(
                data=str(data_yaml_path),
                device=device,
                verbose=False
            )

            # Extraer métricas de ultralytics
            map50 = float(val_results.box.map50) if hasattr(val_results, "box") else 0.0
            map50_95 = float(val_results.box.map) if hasattr(val_results, "box") else 0.0
            precision = float(val_results.box.mp) if hasattr(val_results, "box") else 0.0
            recall = float(val_results.box.mr) if hasattr(val_results, "box") else 0.0

            metrics = {
                "mAP50": round(map50, 4),
                "mAP50_95": round(map50_95, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "pass_threshold_map50": self.pass_threshold_map50
            }

            passed = map50 >= self.pass_threshold_map50
            logger.info(f"Evaluación completada. mAP50: {map50:.4f}, mAP50-95: {map50_95:.4f}, Passed: {passed}")
            return passed, metrics

        except Exception as e:
            logger.error(f"Error evaluando modelo: {e}")
            return False, {
                "error": str(e),
                "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "mAP50": 0.0,
                "mAP50_95": 0.0,
                "precision": 0.0,
                "recall": 0.0
            }

model_evaluator = ModelEvaluator()
