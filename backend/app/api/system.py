import psutil
import torch
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/system", tags=["System"])

def get_system_metrics_dict() -> Dict[str, Any]:
    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_count = psutil.cpu_count(logical=True)

    # RAM
    vmem = psutil.virtual_memory()
    ram_used_gb = round(vmem.used / (1024 ** 3), 2)
    ram_total_gb = round(vmem.total / (1024 ** 3), 2)
    ram_percent = vmem.percent

    # GPU
    cuda_available = torch.cuda.is_available()
    gpu_info = {
        "available": cuda_available,
        "name": "N/A",
        "device_count": 0,
        "vram_allocated_mb": 0.0,
        "vram_reserved_mb": 0.0,
        "vram_total_mb": 0.0
    }

    if cuda_available:
        try:
            device_idx = 0
            gpu_info["name"] = torch.cuda.get_device_name(device_idx)
            gpu_info["device_count"] = torch.cuda.device_count()
            gpu_info["vram_allocated_mb"] = round(torch.cuda.memory_allocated(device_idx) / (1024 ** 2), 1)
            gpu_info["vram_reserved_mb"] = round(torch.cuda.memory_reserved(device_idx) / (1024 ** 2), 1)
            # Memoria total de dispositivo
            props = torch.cuda.get_device_properties(device_idx)
            gpu_info["vram_total_mb"] = round(props.total_memory / (1024 ** 2), 1)
        except Exception:
            pass

    return {
        "cpu": {
            "percent": cpu_percent,
            "cores": cpu_count
        },
        "ram": {
            "used_gb": ram_used_gb,
            "total_gb": ram_total_gb,
            "percent": ram_percent
        },
        "gpu": gpu_info
    }

@router.get("/metrics")
def get_system_metrics():
    return get_system_metrics_dict()
