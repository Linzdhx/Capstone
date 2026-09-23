import logging
import sys
from typing import Any

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configura logging estructurado y limpio para toda la aplicación."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Formato legible y consistente
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger("inventory_monitor")
    root_logger.setLevel(numeric_level)
    
    # Evitar handlers duplicados
    if not root_logger.handlers:
        root_logger.addHandler(handler)
        
    return root_logger

logger = setup_logging()
