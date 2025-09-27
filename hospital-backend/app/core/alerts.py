"""
Hospital Management System - Production Alerting System
Real-time alerts for critical system and medical events
"""

import asyncio
import logging
import smtplib
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from enum import Enum
import aiohttp
import os

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertCategory(Enum):
    SYSTEM = "system"
    MEDICAL = "medical"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"

class Alert:
    def __init__(self,
                 title: str,
                 message: str,
                 severity: AlertSeverity,
                 category: AlertCategory,
                 source: str,
                 metadata: Dict[str, Any] = None):
        self.id = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{hash(title + source) % 10000:04d}"
        self.title = title
        self.message = message
        self.severity = severity
        self.category = category
        self.source = source
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.acknowledged = False
        self.resolved = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'category': self.category.value,
            'source': self.source,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged,
            'resolved': self.resolved
        }

class AlertManager:
    def __init__(self):
        self.logger = logging.getLogger('hospital.alerts')
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.email_enabled = os.getenv('ALERT_EMAIL_ENABLED', 'true').lower() == 'true'
        self.webhook_enabled = os.getenv('ALERT_WEBHOOK_ENABLED', 'false').lower() == 'true'

        # Email configuration
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.yourdomain.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', 'hospital-alerts@yourdomain.com')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.alert_email_to = os.getenv('ALERT_EMAIL_TO', 'admin@yourdomain.com')

        # Webhook configuration
        self.webhook_url = os.getenv('ALERT_WEBHOOK_URL', '')

        # Rate limiting
        self.rate_limit_window = timedelta(minutes=5)
        self.rate_limit_cache: Dict[str, List[datetime]] = {}

    async def create_alert(self,
                          title: str,
                          message: str,
                          severity: AlertSeverity,
                          category: AlertCategory,
                          source: str,
                          metadata: Dict[str, Any] = None) -> Alert:
        """Create and process a new alert"""
        alert = Alert(title, message, severity, category, source, metadata)

        # Check rate limiting
        if self._is_rate_limited(alert):
            self.logger.debug(f"Alert rate limited: {alert.title}")
            return alert

        # Store alert
        self.active_alerts[alert.id] = alert
        self.alert_history.append(alert)

        # Log the alert
        self.logger.warning(
            f"Alert created: {alert.title}",
            extra={
                'alert_id': alert.id,
                'severity': alert.severity.value,
                'category': alert.category.value,
                'source': alert.source,
                'metadata': alert.metadata
            }
        )

        # Send notifications
        await self._send_notifications(alert)

        return alert

    def _is_rate_limited(self, alert: Alert) -> bool:
        """Check if alert should be rate limited"""
        key = f"{alert.title}:{alert.source}"
        now = datetime.utcnow()

        if key not in self.rate_limit_cache:
            self.rate_limit_cache[key] = []

        # Clean old entries
        self.rate_limit_cache[key] = [
            timestamp for timestamp in self.rate_limit_cache[key]
            if now - timestamp < self.rate_limit_window
        ]

        # Check if rate limited (max 3 similar alerts per window)
        if len(self.rate_limit_cache[key]) >= 3:
            return True

        # Add current alert to cache
        self.rate_limit_cache[key].append(now)
        return False

    async def _send_notifications(self, alert: Alert):
        """Send alert notifications via configured channels"""
        tasks = []

        if self.email_enabled and alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]:
            tasks.append(self._send_email_alert(alert))

        if self.webhook_enabled:
            tasks.append(self._send_webhook_alert(alert))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_email_alert(self, alert: Alert):
        """Send email alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_email_to
            msg['Subject'] = f"[HOSPITAL ALERT - {alert.severity.value.upper()}] {alert.title}"

            # Create email body
            body = f"""
Hospital Management System Alert

Alert ID: {alert.id}
Timestamp: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
Severity: {alert.severity.value.upper()}
Category: {alert.category.value.upper()}
Source: {alert.source}

Message:
{alert.message}

Metadata:
{json.dumps(alert.metadata, indent=2)}

---
This is an automated alert from the Hospital Management System.
Please respond immediately for CRITICAL and EMERGENCY alerts.
            """

            msg.attach(MIMEText(body, 'plain'))

            # Send email
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()

            self.logger.info(f"Email alert sent for {alert.id}")

        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")

    async def _send_webhook_alert(self, alert: Alert):
        """Send webhook alert"""
        if not self.webhook_url:
            return

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'alert': alert.to_dict(),
                    'system': 'hospital-management'
                }

                async with session.post(
                    self.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Webhook alert sent for {alert.id}")
                    else:
                        self.logger.warning(f"Webhook alert failed with status {response.status}")

        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            self.logger.info(
                f"Alert acknowledged: {alert_id}",
                extra={
                    'alert_id': alert_id,
                    'acknowledged_by': acknowledged_by
                }
            )
            return True
        return False

    def resolve_alert(self, alert_id: str, resolved_by: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            del self.active_alerts[alert_id]

            self.logger.info(
                f"Alert resolved: {alert_id}",
                extra={
                    'alert_id': alert_id,
                    'resolved_by': resolved_by
                }
            )
            return True
        return False

    def get_active_alerts(self,
                         severity: Optional[AlertSeverity] = None,
                         category: Optional[AlertCategory] = None) -> List[Alert]:
        """Get active alerts with optional filtering"""
        alerts = list(self.active_alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        if category:
            alerts = [a for a in alerts if a.category == category]

        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)

    def cleanup_old_alerts(self, max_age_days: int = 30):
        """Clean up old resolved alerts from history"""
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        self.alert_history = [
            alert for alert in self.alert_history
            if alert.timestamp > cutoff or not alert.resolved
        ]
        self.logger.info(f"Cleaned up old alerts, {len(self.alert_history)} remaining")

# Global alert manager instance
alert_manager = AlertManager()

# Convenience functions for common alerts
async def alert_system_error(title: str, message: str, source: str, metadata: Dict[str, Any] = None):
    """Create a system error alert"""
    return await alert_manager.create_alert(
        title=title,
        message=message,
        severity=AlertSeverity.CRITICAL,
        category=AlertCategory.SYSTEM,
        source=source,
        metadata=metadata
    )

async def alert_security_threat(title: str, message: str, source: str, metadata: Dict[str, Any] = None):
    """Create a security threat alert"""
    return await alert_manager.create_alert(
        title=title,
        message=message,
        severity=AlertSeverity.CRITICAL,
        category=AlertCategory.SECURITY,
        source=source,
        metadata=metadata
    )

async def alert_medical_emergency(title: str, message: str, source: str, metadata: Dict[str, Any] = None):
    """Create a medical emergency alert"""
    return await alert_manager.create_alert(
        title=title,
        message=message,
        severity=AlertSeverity.EMERGENCY,
        category=AlertCategory.MEDICAL,
        source=source,
        metadata=metadata
    )

async def alert_performance_issue(title: str, message: str, source: str, metadata: Dict[str, Any] = None):
    """Create a performance issue alert"""
    return await alert_manager.create_alert(
        title=title,
        message=message,
        severity=AlertSeverity.WARNING,
        category=AlertCategory.PERFORMANCE,
        source=source,
        metadata=metadata
    )

async def alert_compliance_violation(title: str, message: str, source: str, metadata: Dict[str, Any] = None):
    """Create a compliance violation alert"""
    return await alert_manager.create_alert(
        title=title,
        message=message,
        severity=AlertSeverity.CRITICAL,
        category=AlertCategory.COMPLIANCE,
        source=source,
        metadata=metadata
    )