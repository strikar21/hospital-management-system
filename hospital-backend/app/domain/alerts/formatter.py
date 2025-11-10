"""Format alert messages for display."""

from typing import Dict, Any


def format_alert_message(alert: Dict[str, Any]) -> str:
    """
    Format alert message with context for display.

    Args:
        alert: Alert record dict

    Returns:
        Formatted message string

    Example:
        >>> alert = {'type': 'vital', 'message': 'High Heart Rate: 125bpm', 'severity': 'high'}
        >>> format_alert_message(alert)
        '⚠️ High Heart Rate: 125bpm'
    """
    severity_icons = {
        'low': 'ℹ️',
        'medium': '⚠️',
        'high': '🔴',
        'critical': '🚨'
    }

    icon = severity_icons.get(alert.get('severity', 'medium'), '⚠️')
    message = alert.get('message', 'Unknown alert')

    return f"{icon} {message}"


def format_alert_summary(alerts: list[Dict[str, Any]]) -> str:
    """
    Format multiple alerts into summary string.

    Args:
        alerts: List of alert records

    Returns:
        Summary string

    Example:
        >>> alerts = [
        ...     {'severity': 'high', 'message': 'High HR'},
        ...     {'severity': 'critical', 'message': 'Low SpO2'}
        ... ]
        >>> format_alert_summary(alerts)
        '2 active alerts: 1 critical, 1 high'
    """
    if not alerts:
        return 'No active alerts'

    count = len(alerts)
    severity_counts = {}

    for alert in alerts:
        severity = alert.get('severity', 'medium')
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    # Format severity breakdown
    parts = []
    for severity in ['critical', 'high', 'medium', 'low']:
        if severity in severity_counts:
            parts.append(f"{severity_counts[severity]} {severity}")

    breakdown = ', '.join(parts)

    return f"{count} active alert{'s' if count != 1 else ''}: {breakdown}"
