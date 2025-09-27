"""
Hospital Management System - Production Logging Configuration
Structured logging for HIPAA compliance and operational monitoring
"""

import logging
import logging.config
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

class HIPAAFormatter(logging.Formatter):
    """Custom formatter for HIPAA compliant logging"""

    def format(self, record: logging.LogRecord) -> str:
        # Create base log structure
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process_id': os.getpid(),
            'thread_id': record.thread
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add custom fields from extra
        for key, value in record.__dict__.items():
            if key not in {'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                          'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                          'getMessage', 'exc_info', 'exc_text', 'stack_info'}:
                # Sanitize sensitive data
                if isinstance(value, (str, int, float, bool, list, dict)):
                    log_entry[key] = self.sanitize_sensitive_data(key, value)

        return json.dumps(log_entry, default=str)

    def sanitize_sensitive_data(self, key: str, value: Any) -> Any:
        """Remove or mask sensitive information for HIPAA compliance"""
        sensitive_keys = {
            'password', 'token', 'secret', 'key', 'auth', 'credential',
            'ssn', 'social_security', 'patient_id', 'medical_record_number'
        }

        key_lower = key.lower()

        # Mask sensitive fields
        for sensitive in sensitive_keys:
            if sensitive in key_lower:
                if isinstance(value, str) and len(value) > 0:
                    return f"***{value[-4:]}" if len(value) > 4 else "***"
                return "***"

        # Truncate very long strings to prevent log bloat
        if isinstance(value, str) and len(value) > 1000:
            return value[:1000] + "...[truncated]"

        return value

class AuditLogger:
    """Special logger for HIPAA audit trail"""

    def __init__(self):
        self.logger = logging.getLogger('hospital.audit')

    def log_patient_access(self, user_id: str, patient_id: str, action: str,
                          ip_address: str = None, user_agent: str = None):
        """Log patient data access for HIPAA audit"""
        self.logger.info(
            "Patient data access",
            extra={
                'event_type': 'patient_access',
                'user_id': user_id,
                'patient_id': patient_id,
                'action': action,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'compliance': 'HIPAA_AUDIT'
            }
        )

    def log_authentication(self, user_id: str, action: str, success: bool,
                          ip_address: str = None, reason: str = None):
        """Log authentication events"""
        self.logger.info(
            f"Authentication {action}",
            extra={
                'event_type': 'authentication',
                'user_id': user_id,
                'action': action,
                'success': success,
                'ip_address': ip_address,
                'reason': reason,
                'compliance': 'HIPAA_AUDIT'
            }
        )

    def log_data_modification(self, user_id: str, table_name: str, record_id: str,
                             action: str, changes: Dict[str, Any] = None):
        """Log data modifications for audit trail"""
        sanitized_changes = {}
        if changes:
            for key, value in changes.items():
                sanitized_changes[key] = self.sanitize_for_audit(value)

        self.logger.info(
            f"Data modification in {table_name}",
            extra={
                'event_type': 'data_modification',
                'user_id': user_id,
                'table_name': table_name,
                'record_id': record_id,
                'action': action,
                'changes': sanitized_changes,
                'compliance': 'HIPAA_AUDIT'
            }
        )

    def sanitize_for_audit(self, value: Any) -> Any:
        """Sanitize sensitive data for audit logs"""
        if isinstance(value, str):
            # Check if it looks like sensitive data
            if any(keyword in value.lower() for keyword in ['password', 'ssn', 'social']):
                return "***[REDACTED]***"
        return value

def setup_production_logging():
    """Configure production logging with HIPAA compliance"""

    # Create logs directory
    log_dir = Path("/app/logs")
    log_dir.mkdir(exist_ok=True)

    # Logging configuration
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'hipaa': {
                '()': 'app.core.logging_config.HIPAAFormatter'
            },
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'standard',
                'stream': sys.stdout
            },
            'file_all': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'hipaa',
                'filename': str(log_dir / 'hospital.log'),
                'maxBytes': 50 * 1024 * 1024,  # 50MB
                'backupCount': 10,
                'encoding': 'utf8'
            },
            'file_error': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'hipaa',
                'filename': str(log_dir / 'error.log'),
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'file_audit': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'hipaa',
                'filename': str(log_dir / 'audit.log'),
                'maxBytes': 100 * 1024 * 1024,  # 100MB
                'backupCount': 50,  # Keep more audit logs for compliance
                'encoding': 'utf8'
            },
            'file_security': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'WARNING',
                'formatter': 'hipaa',
                'filename': str(log_dir / 'security.log'),
                'maxBytes': 20 * 1024 * 1024,  # 20MB
                'backupCount': 20,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            # Root logger
            '': {
                'level': 'INFO',
                'handlers': ['console', 'file_all', 'file_error']
            },
            # Application loggers
            'hospital': {
                'level': 'INFO',
                'handlers': ['file_all', 'file_error'],
                'propagate': False
            },
            'hospital.audit': {
                'level': 'INFO',
                'handlers': ['file_audit'],
                'propagate': False
            },
            'hospital.security': {
                'level': 'WARNING',
                'handlers': ['file_security', 'file_error'],
                'propagate': False
            },
            # Third-party loggers
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console', 'file_all']
            },
            'uvicorn.error': {
                'level': 'INFO',
                'handlers': ['file_error']
            },
            'uvicorn.access': {
                'level': 'INFO',
                'handlers': ['file_all']
            },
            'fastapi': {
                'level': 'INFO',
                'handlers': ['file_all']
            },
            'sqlalchemy': {
                'level': 'WARNING',
                'handlers': ['file_error']
            }
        }
    }

    # Apply configuration
    logging.config.dictConfig(config)

    # Set production log level from environment
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logging.getLogger().setLevel(getattr(logging, log_level))

    # Log configuration startup
    logger = logging.getLogger('hospital.system')
    logger.info(
        "Production logging initialized",
        extra={
            'log_level': log_level,
            'log_directory': str(log_dir),
            'hipaa_compliance': True,
            'audit_logging': True
        }
    )

def get_audit_logger() -> AuditLogger:
    """Get the HIPAA audit logger instance"""
    return AuditLogger()

def log_system_event(event_type: str, message: str, **kwargs):
    """Log system-level events"""
    logger = logging.getLogger('hospital.system')
    logger.info(
        message,
        extra={
            'event_type': event_type,
            **kwargs
        }
    )

def log_security_event(event_type: str, message: str, severity: str = 'WARNING', **kwargs):
    """Log security-related events"""
    logger = logging.getLogger('hospital.security')
    log_method = getattr(logger, severity.lower(), logger.warning)
    log_method(
        message,
        extra={
            'event_type': event_type,
            'security_event': True,
            **kwargs
        }
    )

# Initialize logging when module is imported in production
if os.getenv('ENV') == 'production':
    setup_production_logging()