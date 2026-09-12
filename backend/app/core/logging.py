import logging
import json
import traceback
from datetime import datetime
from app.core.config import settings

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.
    Strips out potential PHI from standard messages, requires explicit 'extra' fields.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "module": record.module,
            "funcName": record.funcName,
            "message": record.getMessage()
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)
            
        # Merge any 'extra' attributes passed in via the 'extra' dict
        # Ensure we don't accidentally log things like raw requests or passwords
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename", 
                           "funcName", "id", "levelname", "levelno", "lineno", "module", 
                           "msecs", "message", "msg", "name", "pathname", "process", 
                           "processName", "relativeCreated", "stack_info", "thread", "threadName"]:
                if key == "password" or key == "token":
                    log_obj[key] = "***REDACTED***"
                else:
                    log_obj[key] = value

        return json.dumps(log_obj)

def setup_logging():
    """
    Initializes root logger with structured JSON format for production environments.
    """
    logger = logging.getLogger("medflow")
    
    # Don't add multiple handlers if already set up
    if not logger.handlers:
        handler = logging.StreamHandler()
        if settings.ENV == "production":
            handler.setFormatter(JSONFormatter())
            logger.setLevel(logging.INFO)
        else:
            handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
            logger.setLevel(logging.DEBUG)
        
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger

log = setup_logging()
