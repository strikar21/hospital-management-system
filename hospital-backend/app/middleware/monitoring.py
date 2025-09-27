"""
Hospital Management System - Production Monitoring Middleware
Request monitoring, performance tracking, and health metrics
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from app.core.alerts import alert_performance_issue, alert_system_error

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'http_active_connections',
    'Number of active HTTP connections'
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

DATABASE_CONNECTIONS_MAX = Gauge(
    'database_connections_max',
    'Maximum number of database connections'
)

PATIENT_DATA_PROCESSING_DURATION = Histogram(
    'patient_data_processing_duration_seconds',
    'Time spent processing patient data'
)

VITAL_SIGNS_RECEIVED = Counter(
    'vital_signs_received_total',
    'Total vital signs data points received',
    ['device_type', 'patient_id']
)

AUTHENTICATION_ATTEMPTS = Counter(
    'authentication_attempts_total',
    'Total authentication attempts',
    ['method', 'result']
)

AUDIT_LOG_WRITES = Counter(
    'audit_log_writes_total',
    'Total audit log writes',
    ['table', 'operation']
)

AUDIT_LOG_WRITE_FAILURES = Counter(
    'audit_log_write_failures_total',
    'Failed audit log writes'
)

WEBSOCKET_CONNECTIONS = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections'
)

WEBSOCKET_DISCONNECTIONS = Counter(
    'websocket_disconnections_total',
    'Total WebSocket disconnections',
    ['reason']
)

class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring HTTP requests and system health"""

    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger('hospital.monitoring')
        self.slow_request_threshold = 5.0  # seconds
        self.error_rate_threshold = 0.1  # 10%
        self.error_rate_window = []
        self.max_window_size = 100

    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.time()
        ACTIVE_CONNECTIONS.inc()

        # Extract request info
        method = request.method
        path = request.url.path
        endpoint = self._get_endpoint_name(path)

        # Process request
        response = None
        status_code = 500
        error = None

        try:
            response = await call_next(request)
            status_code = response.status_code

        except Exception as e:
            error = e
            self.logger.error(f"Request processing error: {e}", exc_info=True)
            # Create a basic error response
            from fastapi import HTTPException
            if isinstance(e, HTTPException):
                status_code = e.status_code
            else:
                status_code = 500

        finally:
            # Calculate duration
            duration = time.time() - start_time
            ACTIVE_CONNECTIONS.dec()

            # Record metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()

            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Log request
            self._log_request(request, status_code, duration, error)

            # Check for performance issues
            await self._check_performance_alerts(endpoint, duration, status_code)

            # Track error rates
            self._update_error_rate(status_code >= 400)

        return response

    def _get_endpoint_name(self, path: str) -> str:
        """Extract endpoint name from path for metrics"""
        # Remove UUID patterns and numeric IDs for grouping
        import re

        # Replace UUIDs with {id}
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )

        # Replace numeric IDs with {id}
        path = re.sub(r'/\d+', '/{id}', path)

        return path

    def _log_request(self, request: Request, status_code: int, duration: float, error: Exception = None):
        """Log request details"""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        log_data = {
            'method': request.method,
            'path': request.url.path,
            'status_code': status_code,
            'duration_seconds': duration,
            'client_ip': client_ip,
            'user_agent': user_agent,
            'query_params': dict(request.query_params)
        }

        if error:
            log_data['error'] = str(error)
            self.logger.error("Request failed", extra=log_data)
        elif status_code >= 400:
            self.logger.warning("Request error", extra=log_data)
        else:
            self.logger.info("Request completed", extra=log_data)

    async def _check_performance_alerts(self, endpoint: str, duration: float, status_code: int):
        """Check for performance issues and create alerts"""
        # Check for slow requests
        if duration > self.slow_request_threshold:
            await alert_performance_issue(
                title=f"Slow request detected",
                message=f"Request to {endpoint} took {duration:.2f} seconds (threshold: {self.slow_request_threshold}s)",
                source="monitoring_middleware",
                metadata={
                    'endpoint': endpoint,
                    'duration': duration,
                    'threshold': self.slow_request_threshold
                }
            )

        # Check for system errors
        if status_code >= 500:
            await alert_system_error(
                title=f"System error on {endpoint}",
                message=f"HTTP {status_code} error on {endpoint}",
                source="monitoring_middleware",
                metadata={
                    'endpoint': endpoint,
                    'status_code': status_code,
                    'duration': duration
                }
            )

    def _update_error_rate(self, is_error: bool):
        """Update error rate tracking"""
        self.error_rate_window.append(is_error)

        # Keep window size manageable
        if len(self.error_rate_window) > self.max_window_size:
            self.error_rate_window.pop(0)

        # Check error rate
        if len(self.error_rate_window) >= 20:  # Minimum sample size
            error_rate = sum(self.error_rate_window) / len(self.error_rate_window)

            if error_rate > self.error_rate_threshold:
                asyncio.create_task(
                    alert_system_error(
                        title="High error rate detected",
                        message=f"Error rate is {error_rate:.1%} (threshold: {self.error_rate_threshold:.1%})",
                        source="monitoring_middleware",
                        metadata={
                            'error_rate': error_rate,
                            'threshold': self.error_rate_threshold,
                            'sample_size': len(self.error_rate_window)
                        }
                    )
                )

class HealthChecker:
    """System health checker"""

    def __init__(self):
        self.logger = logging.getLogger('hospital.health')
        self.last_check = None
        self.check_interval = 60  # seconds

    async def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }

        # Database connectivity
        try:
            from app.core.database import get_database
            db = get_database()
            await db.execute("SELECT 1")
            health_status['checks']['database'] = {'status': 'healthy'}
        except Exception as e:
            health_status['checks']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'unhealthy'

        # Memory usage
        import psutil
        memory_percent = psutil.virtual_memory().percent
        health_status['checks']['memory'] = {
            'status': 'healthy' if memory_percent < 90 else 'unhealthy',
            'usage_percent': memory_percent
        }

        if memory_percent > 90:
            health_status['overall_status'] = 'degraded'

        # Disk usage
        disk_percent = psutil.disk_usage('/').percent
        health_status['checks']['disk'] = {
            'status': 'healthy' if disk_percent < 90 else 'unhealthy',
            'usage_percent': disk_percent
        }

        if disk_percent > 90:
            health_status['overall_status'] = 'degraded'

        # Update metrics
        DATABASE_CONNECTIONS.set(10)  # This would come from actual connection pool
        DATABASE_CONNECTIONS_MAX.set(100)

        self.last_check = datetime.utcnow()
        return health_status

    async def get_metrics(self) -> str:
        """Get Prometheus metrics"""
        return generate_latest()

# Global instances
health_checker = HealthChecker()

async def metrics_endpoint():
    """Endpoint to expose Prometheus metrics"""
    return Response(
        content=await health_checker.get_metrics(),
        media_type=CONTENT_TYPE_LATEST
    )

async def health_endpoint():
    """Endpoint for health checks"""
    return await health_checker.check_system_health()

# Utility functions for tracking custom metrics
def track_patient_data_processing(duration: float):
    """Track patient data processing time"""
    PATIENT_DATA_PROCESSING_DURATION.observe(duration)

def track_vital_signs_received(device_type: str, patient_id: str):
    """Track vital signs data reception"""
    VITAL_SIGNS_RECEIVED.labels(device_type=device_type, patient_id=patient_id).inc()

def track_authentication_attempt(method: str, success: bool):
    """Track authentication attempts"""
    result = "success" if success else "failure"
    AUTHENTICATION_ATTEMPTS.labels(method=method, result=result).inc()

def track_audit_log_write(table: str, operation: str, success: bool = True):
    """Track audit log writes"""
    if success:
        AUDIT_LOG_WRITES.labels(table=table, operation=operation).inc()
    else:
        AUDIT_LOG_WRITE_FAILURES.inc()

def track_websocket_connection(connected: bool, reason: str = None):
    """Track WebSocket connections"""
    if connected:
        WEBSOCKET_CONNECTIONS.inc()
    else:
        WEBSOCKET_CONNECTIONS.dec()
        if reason:
            WEBSOCKET_DISCONNECTIONS.labels(reason=reason).inc()