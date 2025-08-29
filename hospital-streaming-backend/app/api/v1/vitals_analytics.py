from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import asyncpg
import json
from pydantic import BaseModel

from app.db.database import database
from app.services.staff_service import StaffService

router = APIRouter(prefix="/vitals-analytics")

class MedicationEvent(BaseModel):
    medication_id: str
    medication_name: str
    action: str  # administered, modified, stopped
    timestamp: datetime
    dosage: Optional[str] = None
    performed_by: str

class VitalsTimeframe(BaseModel):
    timeframe: str  # 1m, 5m, 15m, 1h, 4h, 12h, 24h
    open_value: float
    high_value: float
    low_value: float
    close_value: float
    timestamp: datetime
    volume: int  # number of readings in this timeframe
    quality_avg: float

class MedicationCorrelatedVitals(BaseModel):
    patient_id: str
    vital_type: str
    medication_events: List[MedicationEvent]
    vitals_data: List[VitalsTimeframe]
    correlation_insights: Dict[str, Any]

# TimescaleDB connection pool
timescale_pool = None

async def get_timescale_connection():
    """Get optimized TimescaleDB connection for analytics"""
    global timescale_pool
    
    if timescale_pool is None:
        timescale_pool = await asyncpg.create_pool(
            "postgresql://hospital_user:hospital_pass@localhost:5434/hospital_vitals",
            min_size=5,
            max_size=20,
            command_timeout=30  # Longer timeout for analytics queries
        )
    
    return await timescale_pool.acquire()

async def verify_staff_access(staff_id: str = Query(..., description="Staff ID performing the action")):
    """Verify staff member exists and is active - with fallback for development"""
    try:
        staff = await StaffService.get_staff_by_id(staff_id)
        if staff:
            return staff
    except Exception as e:
        print(f"Staff verification failed for {staff_id}: {e}")
    
    # Fallback for development - create a mock staff record
    print(f"Using fallback staff access for {staff_id}")
    return {
        "id": staff_id,
        "name": "Development User",
        "role": "Doctor",
        "is_active": True
    }

@router.get("/patient/{patient_id}/medication-correlated-vitals")
async def get_medication_correlated_vitals(
    patient_id: str,
    vital_type: str = Query(..., description="Type of vital sign (heart_rate, blood_pressure_systolic, etc.)"),
    hours_back: int = Query(default=24, description="Hours of data to analyze"),
    medication_filter: Optional[str] = Query(None, description="Filter by specific medication name"),
    timeframe: str = Query(default="5m", description="Chart timeframe: 1m, 5m, 15m, 1h, 4h, 12h"),
    staff: dict = Depends(verify_staff_access)
):
    """
    Get vitals data correlated with medication administration events
    Shows before/after medication effects with stock-chart style visualization
    """
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)
        
        # Get medication events for this patient in the timeframe
        medication_query = """
            SELECT 
                pm.id as medication_id,
                pm.name as medication_name,
                mh.action,
                mh.timestamp,
                pm.dosage,
                mh.performed_by
            FROM patient_medications pm
            JOIN medication_history mh ON pm.id = mh.medication_id
            WHERE pm.patient_id = :patient_id
            AND mh.timestamp >= :start_time
            AND mh.timestamp <= :end_time
        """
        
        med_params = {
            "patient_id": patient_id,
            "start_time": start_time,
            "end_time": end_time
        }
        
        if medication_filter:
            medication_query += " AND pm.name ILIKE :med_name"
            med_params["med_name"] = f"%{medication_filter}%"
        
        medication_query += " ORDER BY mh.timestamp ASC"
        
        medication_events = await database.fetch_all(medication_query, med_params)
        
        # Convert timeframe to minutes for aggregation
        timeframe_minutes = {
            "1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "12h": 720, "24h": 1440
        }.get(timeframe, 5)
        
        # Get aggregated vitals data using TimescaleDB time_bucket
        timescale_conn = await get_timescale_connection()
        
        try:
            interval_str = f"{timeframe_minutes} minutes"
            vitals_query = f"""
                SELECT 
                    time_bucket('{interval_str}'::interval, timestamp) as bucket,
                    (array_agg(value ORDER BY timestamp ASC))[1] as open_value,
                    MAX(value) as high_value,
                    MIN(value) as low_value,
                    (array_agg(value ORDER BY timestamp DESC))[1] as close_value,
                    COUNT(*) as volume,
                    AVG(
                        CASE 
                            WHEN quality_indicator = 'excellent' THEN 1.0
                            WHEN quality_indicator = 'good' THEN 0.8
                            WHEN quality_indicator = 'poor' THEN 0.5
                            ELSE 0.7
                        END
                    ) as quality_avg
                FROM vital_readings
                WHERE patient_id = $1
                AND vital_type = $2
                AND timestamp >= $3
                AND timestamp <= $4
                GROUP BY bucket
                ORDER BY bucket ASC
            """
            
            vitals_data = await timescale_conn.fetch(
                vitals_query,
                patient_id,
                vital_type,
                start_time,
                end_time
            )
            
        finally:
            await timescale_conn.close()
        
        # Format vitals data
        vitals_timeframes = [
            VitalsTimeframe(
                timeframe=timeframe,
                open_value=row["open_value"],
                high_value=row["high_value"],
                low_value=row["low_value"],
                close_value=row["close_value"],
                timestamp=row["bucket"],
                volume=row["volume"],
                quality_avg=float(row["quality_avg"])
            )
            for row in vitals_data
        ]
        
        # Format medication events
        med_events = [
            MedicationEvent(
                medication_id=row["medication_id"],
                medication_name=row["medication_name"],
                action=row["action"],
                timestamp=row["timestamp"],
                dosage=row["dosage"],
                performed_by=row["performed_by"]
            )
            for row in medication_events
        ]
        
        # Calculate correlation insights
        correlation_insights = await calculate_medication_vitals_correlation(
            med_events, vitals_timeframes, vital_type
        )
        
        return MedicationCorrelatedVitals(
            patient_id=patient_id,
            vital_type=vital_type,
            medication_events=med_events,
            vitals_data=vitals_timeframes,
            correlation_insights=correlation_insights
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get correlated vitals: {str(e)}")

async def calculate_medication_vitals_correlation(
    medication_events: List[MedicationEvent],
    vitals_data: List[VitalsTimeframe],
    vital_type: str
) -> Dict[str, Any]:
    """Calculate insights about medication effects on vitals"""
    
    insights = {
        "total_medication_events": len(medication_events),
        "avg_vital_before_meds": 0.0,
        "avg_vital_after_meds": 0.0,
        "significant_changes": [],
        "trends": []
    }
    
    if not medication_events or not vitals_data:
        return insights
    
    # Analyze vitals before and after each medication event
    for med_event in medication_events:
        # Find vitals 1 hour before and after medication
        before_cutoff = med_event.timestamp - timedelta(hours=1)
        after_cutoff = med_event.timestamp + timedelta(hours=1)
        
        before_vitals = [
            v.close_value for v in vitals_data
            if before_cutoff <= v.timestamp <= med_event.timestamp
        ]
        after_vitals = [
            v.close_value for v in vitals_data
            if med_event.timestamp <= v.timestamp <= after_cutoff
        ]
        
        if before_vitals and after_vitals:
            before_avg = sum(before_vitals) / len(before_vitals)
            after_avg = sum(after_vitals) / len(after_vitals)
            change_percent = ((after_avg - before_avg) / before_avg) * 100
            
            if abs(change_percent) > 10:  # Significant change threshold
                insights["significant_changes"].append({
                    "medication": med_event.medication_name,
                    "action": med_event.action,
                    "timestamp": med_event.timestamp.isoformat(),
                    "before_avg": round(before_avg, 2),
                    "after_avg": round(after_avg, 2),
                    "change_percent": round(change_percent, 2),
                    "effect": "positive" if change_percent < 0 and vital_type in ["heart_rate", "blood_pressure_systolic"] 
                             else "concerning" if change_percent > 0 else "neutral"
                })
    
    # Overall trends
    if vitals_data:
        first_half = vitals_data[:len(vitals_data)//2]
        second_half = vitals_data[len(vitals_data)//2:]
        
        if first_half and second_half:
            first_avg = sum(v.close_value for v in first_half) / len(first_half)
            second_avg = sum(v.close_value for v in second_half) / len(second_half)
            overall_trend = "improving" if second_avg < first_avg else "stable" if abs(second_avg - first_avg) < 2 else "concerning"
            
            insights["trends"].append({
                "period": "overall",
                "direction": overall_trend,
                "first_period_avg": round(first_avg, 2),
                "second_period_avg": round(second_avg, 2)
            })
    
    return insights

@router.get("/patient/{patient_id}/vitals-timeseries")
async def get_vitals_timeseries_data(
    patient_id: str,
    vital_type: str = Query(..., description="Type of vital sign"),
    timeframe: str = Query(default="5m", description="Data aggregation timeframe"),
    hours_back: int = Query(default=12, description="Hours of data"),
    raw_data: bool = Query(default=False, description="Return raw 1-second data instead of aggregated"),
    staff: dict = Depends(verify_staff_access)
):
    """
    Get vitals time-series data for line charts with dots
    Perfect for medical vitals visualization with multiple timeframes
    """
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)
        
        timescale_conn = await get_timescale_connection()
        
        try:
            if raw_data:
                # Return raw 1-second data points (limited to reasonable amounts)
                raw_query = """
                    SELECT 
                        timestamp,
                        value,
                        quality_indicator,
                        metadata
                    FROM vital_readings
                    WHERE patient_id = $1
                    AND vital_type = $2
                    AND timestamp >= $3
                    AND timestamp <= $4
                    AND value IS NOT NULL
                    ORDER BY timestamp ASC
                    LIMIT 2000
                """
                
                results = await timescale_conn.fetch(
                    raw_query,
                    patient_id,
                    vital_type,
                    start_time,
                    end_time
                )
                
                line_data = [
                    {
                        "timestamp": row["timestamp"].isoformat(),
                        "value": float(row["value"]),
                        "quality": row["quality_indicator"],
                        "metadata": row["metadata"]
                    }
                    for row in results
                ]
                
            else:
                # Convert timeframe to minutes for aggregation
                timeframe_minutes = {
                    "1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "2h": 120, "4h": 240, "12h": 720
                }.get(timeframe, 5)
                
                # TimescaleDB optimized aggregation query
                interval_str = f"{timeframe_minutes} minutes"
                timeseries_query = f"""
                    SELECT 
                        time_bucket('{interval_str}'::interval, timestamp) as bucket,
                        AVG(value) as avg_value,
                        MAX(value) as max_value,
                        MIN(value) as min_value,
                        COUNT(*) as data_points,
                        STDDEV(value) as variability,
                        AVG(
                            CASE 
                                WHEN quality_indicator = 'excellent' THEN 1.0
                                WHEN quality_indicator = 'good' THEN 0.8
                                WHEN quality_indicator = 'poor' THEN 0.5
                                ELSE 0.7
                            END
                        ) as avg_quality_score,
                        array_agg(DISTINCT quality_indicator) as quality_indicators
                    FROM vital_readings
                    WHERE patient_id = $1
                    AND vital_type = $2
                    AND timestamp >= $3
                    AND timestamp <= $4
                    AND value IS NOT NULL
                    GROUP BY bucket
                    HAVING COUNT(*) > 0
                    ORDER BY bucket ASC
                """
                
                results = await timescale_conn.fetch(
                    timeseries_query,
                    patient_id,
                    vital_type,
                    start_time,
                    end_time
                )
                
                line_data = [
                    {
                        "timestamp": row["bucket"].isoformat(),
                        "value": float(row["avg_value"]),
                        "max_value": float(row["max_value"]),
                        "min_value": float(row["min_value"]),
                        "data_points": row["data_points"],
                        "variability": float(row["variability"]) if row["variability"] else 0,
                        "quality_score": float(row["avg_quality_score"]),
                        "quality_indicators": row["quality_indicators"]
                    }
                    for row in results
                ]
            
        finally:
            await timescale_conn.close()
        
        return {
            "patient_id": patient_id,
            "vital_type": vital_type,
            "timeframe": timeframe if not raw_data else "raw",
            "total_data_points": len(line_data),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "data": line_data,
            "chart_config": {
                "chart_type": "line",
                "show_dots": True,
                "dot_size": 4 if raw_data else 6,
                "line_width": 2,
                "y_axis_label": get_vital_unit(vital_type),
                "color_scheme": {
                    "primary_line": get_vital_color(vital_type),
                    "dot_color": get_vital_color(vital_type),
                    "excellent_quality": "#4CAF50",
                    "good_quality": "#FF9800", 
                    "poor_quality": "#F44336"
                },
                "thresholds": get_vital_thresholds(vital_type)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get timeseries data: {str(e)}")

def get_vital_unit(vital_type: str) -> str:
    """Get unit for vital sign type"""
    units = {
        "heart_rate": "BPM",
        "blood_pressure_systolic": "mmHg",
        "blood_pressure_diastolic": "mmHg", 
        "temperature": "°F",
        "oxygen_saturation": "%",
        "respiratory_rate": "/min"
    }
    return units.get(vital_type, "")

def get_vital_color(vital_type: str) -> str:
    """Get primary color for each vital type"""
    colors = {
        "heart_rate": "#E91E63",           # Pink - heart related
        "blood_pressure_systolic": "#F44336",    # Red - blood pressure
        "blood_pressure_diastolic": "#FF5722",   # Deep orange - blood pressure
        "temperature": "#FF9800",          # Orange - temperature
        "oxygen_saturation": "#2196F3",    # Blue - oxygen
        "respiratory_rate": "#4CAF50"      # Green - respiratory
    }
    return colors.get(vital_type, "#607D8B")  # Default blue-grey

def get_vital_thresholds(vital_type: str) -> Dict[str, Any]:
    """Get normal, warning, and critical thresholds for each vital type"""
    thresholds = {
        "heart_rate": {
            "normal_min": 60,
            "normal_max": 100,
            "warning_min": 50,
            "warning_max": 120,
            "critical_min": 40,
            "critical_max": 150,
            "zones": [
                {"min": 60, "max": 100, "color": "#4CAF50", "label": "Normal"},
                {"min": 50, "max": 59, "color": "#FF9800", "label": "Bradycardia Warning"},
                {"min": 101, "max": 120, "color": "#FF9800", "label": "Tachycardia Warning"},
                {"min": 0, "max": 49, "color": "#F44336", "label": "Critical Low"},
                {"min": 121, "max": 300, "color": "#F44336", "label": "Critical High"}
            ]
        },
        "blood_pressure_systolic": {
            "normal_min": 90,
            "normal_max": 140,
            "warning_min": 80,
            "warning_max": 160,
            "critical_min": 70,
            "critical_max": 180,
            "zones": [
                {"min": 90, "max": 140, "color": "#4CAF50", "label": "Normal"},
                {"min": 141, "max": 160, "color": "#FF9800", "label": "Stage 1 Hypertension"},
                {"min": 80, "max": 89, "color": "#FF9800", "label": "Hypotension Warning"},
                {"min": 161, "max": 300, "color": "#F44336", "label": "Stage 2+ Hypertension"},
                {"min": 0, "max": 79, "color": "#F44336", "label": "Severe Hypotension"}
            ]
        },
        "temperature": {
            "normal_min": 97.0,
            "normal_max": 99.5,
            "warning_min": 96.0,
            "warning_max": 101.0,
            "critical_min": 95.0,
            "critical_max": 103.0,
            "zones": [
                {"min": 97.0, "max": 99.5, "color": "#4CAF50", "label": "Normal"},
                {"min": 99.6, "max": 101.0, "color": "#FF9800", "label": "Fever"},
                {"min": 96.0, "max": 96.9, "color": "#FF9800", "label": "Hypothermia Warning"},
                {"min": 101.1, "max": 110.0, "color": "#F44336", "label": "High Fever"},
                {"min": 80.0, "max": 95.9, "color": "#F44336", "label": "Severe Hypothermia"}
            ]
        },
        "oxygen_saturation": {
            "normal_min": 95,
            "normal_max": 100,
            "warning_min": 90,
            "warning_max": 100,
            "critical_min": 85,
            "critical_max": 100,
            "zones": [
                {"min": 95, "max": 100, "color": "#4CAF50", "label": "Normal"},
                {"min": 90, "max": 94, "color": "#FF9800", "label": "Mild Hypoxemia"},
                {"min": 85, "max": 89, "color": "#F44336", "label": "Moderate Hypoxemia"},
                {"min": 0, "max": 84, "color": "#D32F2F", "label": "Severe Hypoxemia"}
            ]
        },
        "respiratory_rate": {
            "normal_min": 12,
            "normal_max": 20,
            "warning_min": 8,
            "warning_max": 25,
            "critical_min": 6,
            "critical_max": 30,
            "zones": [
                {"min": 12, "max": 20, "color": "#4CAF50", "label": "Normal"},
                {"min": 8, "max": 11, "color": "#FF9800", "label": "Bradypnea"},
                {"min": 21, "max": 25, "color": "#FF9800", "label": "Tachypnea"},
                {"min": 0, "max": 7, "color": "#F44336", "label": "Critical Low"},
                {"min": 26, "max": 100, "color": "#F44336", "label": "Critical High"}
            ]
        }
    }
    
    return thresholds.get(vital_type, {
        "normal_min": 0,
        "normal_max": 100,
        "zones": [{"min": 0, "max": 100, "color": "#607D8B", "label": "Unknown"}]
    })

@router.get("/patient/{patient_id}/medication-timeline")
async def get_medication_timeline(
    patient_id: str,
    hours_back: int = Query(default=24, description="Hours back to get timeline"),
    staff: dict = Depends(verify_staff_access)
):
    """Get medication administration timeline for chart overlays"""
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)
        
        timeline_query = """
            SELECT 
                pm.name as medication_name,
                pm.dosage,
                mh.action,
                mh.timestamp,
                mh.performed_by,
                pm.route,
                CASE 
                    WHEN mh.action = 'administered' THEN 'success'
                    WHEN mh.action = 'missed' THEN 'warning' 
                    WHEN mh.action = 'stopped' THEN 'danger'
                    ELSE 'info'
                END as event_type
            FROM patient_medications pm
            JOIN medication_history mh ON pm.id = mh.medication_id
            WHERE pm.patient_id = :patient_id
            AND mh.timestamp >= :start_time
            AND mh.timestamp <= :end_time
            ORDER BY mh.timestamp ASC
        """
        
        events = await database.fetch_all(timeline_query, {
            "patient_id": patient_id,
            "start_time": start_time,
            "end_time": end_time
        })
        
        return {
            "patient_id": patient_id,
            "timeline_events": [
                {
                    "timestamp": row["timestamp"].isoformat(),
                    "medication_name": row["medication_name"],
                    "dosage": row["dosage"],
                    "action": row["action"],
                    "performed_by": row["performed_by"],
                    "route": row["route"],
                    "event_type": row["event_type"],
                    "display_label": f"{row['medication_name']} - {row['action']}"
                }
                for row in events
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get medication timeline: {str(e)}")