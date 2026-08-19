import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict

class StructuredJsonFormatter(logging.Formatter):
    """
    JSON log formatter for production and structured monitoring.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_fields"):
            log_obj.update(record.extra_fields)
        return json.dumps(log_obj)

def setup_structured_logging(log_level: str = "INFO", json_format: bool = False) -> None:
    """
    Configures application-wide logging format and level.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(StructuredJsonFormatter())
    else:
        standard_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        handler.setFormatter(logging.Formatter(standard_format))
        
    root_logger.addHandler(handler)

def get_logger(name: str) -> logging.Logger:
    """Returns a named logger."""
    return logging.getLogger(f"subrogate.{name}")
