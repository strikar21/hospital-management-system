"""
FHIR R5 Observation API
Endpoints for vitals time-series data
"""

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from ...services.fhir.fhir_observation_service import FhirObservationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fhir/r5/observations", tags=["FHIR R5 - Observations"])

# Initialize service
observation_service = FhirObservationService()


# ================================
# CREATE OBSERVATIONS (ESP32)
# ================================

@router.post("/")
async def createObservation(observation_data: Dict[str, Any]):
    """
    Create FHIR R5 Observation (single vital reading)

    Request body:
    {
        "patientContextId": "uuid",
        "deviceId": "uuid",
        "code": "8867-4",
        "codeDisplay": "Heart rate",
        "valueQuantity": 72,
        "valueUnit": "beats/min",
        "timestamp": "2025-11-18T10:30:00Z",
        "status": "final",
        "dataQuality": "good",
        "signalStrength": 95
    }
    """
    try:
        # Validate required fields
        required = ['patientContextId', 'deviceId', 'code']
        for field in required:
            if not observation_data.get(field):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field} is required"
                )

        if 'valueQuantity' not in observation_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="valueQuantity is required"
            )

        result = await observation_service.create_observation(observation_data)

        return JSONResponse({
            "success": True,
            "observationId": str(result['id']),
            "code": result['code'],
            "value": float(result['valueQuantity']) if result.get('valueQuantity') else None,
            "unit": result.get('valueUnit'),
            "timestamp": result['timestamp'].isoformat()
        }, status_code=status.HTTP_201_CREATED)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating observation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create observation: {str(e)}"
        )


@router.post("/batch")
async def createBatchObservations(observations: List[Dict[str, Any]]):
    """
    Batch create observations (ESP32 streaming)

    Request body: array of observation objects
    """
    try:
        if not observations or len(observations) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="observations array cannot be empty"
            )

        count = await observation_service.create_batch_observations(observations)

        logger.info(f"✅ Batch created {count} observations")

        return JSONResponse({
            "success": True,
            "count": count,
            "message": f"Created {count} observations"
        }, status_code=status.HTTP_201_CREATED)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error batch creating observations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch create observations: {str(e)}"
        )


# ================================
# QUERY VITALS (DASHBOARD)
# ================================

@router.get("/patient/{patientContextId}/latest")
async def getLatestVitals(patientContextId: str):
    """
    Get latest vitals for patient (one reading per LOINC code)

    Returns most recent heart rate, SpO2, temperature, etc.
    """
    try:
        results = await observation_service.get_latest_vitals(patientContextId)

        vitals = []
        for r in results:
            vitals.append({
                "code": r['code'],
                "codeDisplay": r.get('codedisplay'),
                "value": float(r['value']) if r.get('value') else None,
                "unit": r.get('unit'),
                "timestamp": r['obs_timestamp'].isoformat() if r.get('obs_timestamp') else None,
                "isAbnormal": r.get('isabnormal', False)
            })

        return JSONResponse({
            "success": True,
            "patientContextId": patientContextId,
            "count": len(vitals),
            "vitals": vitals
        })

    except Exception as e:
        logger.error(f"❌ Error getting latest vitals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get latest vitals: {str(e)}"
        )


@router.get("/patient/{patientContextId}/trend")
async def getVitalsTrend(
    patientContextId: str,
    code: str = Query(..., description="LOINC code (8867-4 = heart rate)"),
    hoursBack: int = Query(24, ge=1, le=168, description="Hours back to query")
):
    """
    Get vitals trend for specific LOINC code

    Use for charts/graphs showing heart rate over time, etc.
    """
    try:
        results = await observation_service.get_vitals_trend(
            patientContextId,
            code,
            hoursBack
        )

        trend = []
        for r in results:
            trend.append({
                "timestamp": r['obs_timestamp'].isoformat() if r.get('obs_timestamp') else None,
                "value": float(r['value']) if r.get('value') else None,
                "unit": r.get('unit')
            })

        return JSONResponse({
            "success": True,
            "patientContextId": patientContextId,
            "code": code,
            "hoursBack": hoursBack,
            "count": len(trend),
            "trend": trend
        })

    except Exception as e:
        logger.error(f"❌ Error getting vitals trend: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get vitals trend: {str(e)}"
        )


@router.get("/patient/{patientContextId}/range")
async def getObservationsInTimeRange(
    patientContextId: str,
    startTime: str = Query(..., description="ISO datetime (2025-11-18T10:00:00Z)"),
    endTime: str = Query(..., description="ISO datetime"),
    codes: Optional[str] = Query(None, description="Comma-separated LOINC codes"),
    limit: int = Query(1000, ge=1, le=10000)
):
    """
    Get observations within time range

    Optionally filter by LOINC codes
    """
    try:
        start_dt = datetime.fromisoformat(startTime.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(endTime.replace('Z', '+00:00'))

        loinc_codes = None
        if codes:
            loinc_codes = [c.strip() for c in codes.split(',')]

        results = await observation_service.get_observations_in_timerange(
            patientContextId,
            start_dt,
            end_dt,
            loinc_codes,
            limit
        )

        observations = []
        for r in results:
            observations.append({
                "id": str(r['id']),
                "timestamp": r['timestamp'].isoformat(),
                "code": r['code'],
                "codeDisplay": r.get('codeDisplay'),
                "value": float(r['valueQuantity']) if r.get('valueQuantity') else None,
                "unit": r.get('valueUnit'),
                "status": r.get('status'),
                "isAbnormal": r.get('isAbnormal', False),
                "aiAnalysis": r.get('aiAnalysis', {}),
                "dataQuality": r.get('dataQuality')
            })

        return JSONResponse({
            "success": True,
            "patientContextId": patientContextId,
            "startTime": startTime,
            "endTime": endTime,
            "count": len(observations),
            "observations": observations
        })

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Error getting observations in range: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get observations: {str(e)}"
        )


@router.get("/patient/{patientContextId}/abnormal")
async def getAbnormalObservations(
    patientContextId: str,
    hoursBack: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get abnormal/alert-worthy observations"""
    try:
        results = await observation_service.get_abnormal_observations(
            patientContextId,
            hoursBack,
            limit
        )

        observations = []
        for r in results:
            observations.append({
                "id": str(r['id']),
                "timestamp": r['timestamp'].isoformat(),
                "code": r['code'],
                "codeDisplay": r.get('codeDisplay'),
                "value": float(r['valueQuantity']) if r.get('valueQuantity') else None,
                "unit": r.get('valueUnit'),
                "aiAnalysis": r.get('aiAnalysis', {}),
                "isAbnormal": r.get('isAbnormal'),
                "alertGenerated": r.get('alertGenerated')
            })

        return JSONResponse({
            "success": True,
            "patientContextId": patientContextId,
            "count": len(observations),
            "abnormalObservations": observations
        })

    except Exception as e:
        logger.error(f"❌ Error getting abnormal observations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get abnormal observations: {str(e)}"
        )


@router.get("/device/{deviceId}/recent")
async def getDeviceObservations(
    deviceId: str,
    hoursBack: int = Query(1, ge=1, le=24),
    limit: int = Query(1000, ge=1, le=10000)
):
    """Get recent observations from a specific device"""
    try:
        results = await observation_service.get_device_observations(
            deviceId,
            hoursBack,
            limit
        )

        observations = []
        for r in results:
            observations.append({
                "id": str(r['id']),
                "timestamp": r['timestamp'].isoformat(),
                "patientContextId": str(r['patientContextId']),
                "code": r['code'],
                "codeDisplay": r.get('codeDisplay'),
                "value": float(r['valueQuantity']) if r.get('valueQuantity') else None,
                "unit": r.get('valueUnit'),
                "dataQuality": r.get('dataQuality'),
                "signalStrength": r.get('signalStrength')
            })

        return JSONResponse({
            "success": True,
            "deviceId": deviceId,
            "count": len(observations),
            "observations": observations
        })

    except Exception as e:
        logger.error(f"❌ Error getting device observations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device observations: {str(e)}"
        )


# ================================
# AGGREGATIONS
# ================================

@router.get("/patient/{patientContextId}/aggregated")
async def getAggregatedVitals(
    patientContextId: str,
    code: str = Query(..., description="LOINC code"),
    bucketSize: str = Query('1 minute', description="1 minute or 1 hour"),
    hoursBack: int = Query(24, ge=1, le=168)
):
    """
    Get aggregated vitals (min, max, avg) using TimescaleDB continuous aggregates

    Returns pre-computed statistics for fast dashboard rendering
    """
    try:
        if bucketSize not in ['1 minute', '1 hour']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bucketSize must be '1 minute' or '1 hour'"
            )

        results = await observation_service.get_aggregated_vitals(
            patientContextId,
            code,
            bucketSize,
            hoursBack
        )

        aggregated = []
        for r in results:
            aggregated.append({
                "bucket": r['bucket'].isoformat(),
                "avgValue": float(r['avg_value']) if r.get('avg_value') else None,
                "minValue": float(r['min_value']) if r.get('min_value') else None,
                "maxValue": float(r['max_value']) if r.get('max_value') else None,
                "stddevValue": float(r['stddev_value']) if r.get('stddev_value') else None,
                "abnormalCount": r.get('abnormal_count', 0),
                "readingCount": r.get('reading_count', 0)
            })

        return JSONResponse({
            "success": True,
            "patientContextId": patientContextId,
            "code": code,
            "bucketSize": bucketSize,
            "count": len(aggregated),
            "aggregated": aggregated
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting aggregated vitals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get aggregated vitals: {str(e)}"
        )


# ================================
# AI ANALYSIS
# ================================

@router.patch("/{observationId}/ai-analysis")
async def updateAiAnalysis(
    observationId: str,
    ai_data: Dict[str, Any]
):
    """
    Update AI analysis results for an observation

    Request body:
    {
        "aiAnalysis": {
            "severity": "warning",
            "trend": "rising",
            "reason": "hypertension+rising"
        },
        "isAbnormal": true,
        "alertGenerated": true
    }
    """
    try:
        if 'aiAnalysis' not in ai_data or 'isAbnormal' not in ai_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="aiAnalysis and isAbnormal are required"
            )

        await observation_service.update_ai_analysis(
            observationId,
            ai_data['aiAnalysis'],
            ai_data['isAbnormal'],
            ai_data.get('alertGenerated', False)
        )

        return JSONResponse({
            "success": True,
            "observationId": observationId,
            "aiAnalysis": ai_data['aiAnalysis'],
            "isAbnormal": ai_data['isAbnormal']
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating AI analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update AI analysis: {str(e)}"
        )


# ================================
# STATISTICS
# ================================

@router.get("/patient/{patientContextId}/stats")
async def getObservationStats(
    patientContextId: str,
    hoursBack: int = Query(24, ge=1, le=168)
):
    """Get observation statistics for a patient"""
    try:
        stats = await observation_service.get_observation_stats(
            patientContextId,
            hoursBack
        )

        return JSONResponse({
            "success": True,
            "patientContextId": patientContextId,
            "hoursBack": hoursBack,
            "stats": {
                "totalObservations": stats.get('total_observations', 0),
                "uniqueVitals": stats.get('unique_vitals', 0),
                "abnormalCount": stats.get('abnormal_count', 0),
                "alertCount": stats.get('alert_count', 0),
                "earliestObservation": stats.get('earliest_observation').isoformat() if stats.get('earliest_observation') else None,
                "latestObservation": stats.get('latest_observation').isoformat() if stats.get('latest_observation') else None
            }
        })

    except Exception as e:
        logger.error(f"❌ Error getting observation stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get observation stats: {str(e)}"
        )


# ================================
# LOINC CODE HELPERS
# ================================

@router.get("/loinc-codes")
async def getLoincCodes():
    """Get supported LOINC codes"""
    return JSONResponse({
        "success": True,
        "loincCodes": {
            "heart_rate": {
                "code": "8867-4",
                "display": "Heart rate",
                "unit": "beats/min"
            },
            "spo2": {
                "code": "2708-6",
                "display": "Oxygen saturation",
                "unit": "%"
            },
            "temperature": {
                "code": "8310-5",
                "display": "Body temperature",
                "unit": "°C"
            },
            "respiratory_rate": {
                "code": "9279-1",
                "display": "Respiratory rate",
                "unit": "breaths/min"
            },
            "blood_pressure_systolic": {
                "code": "8480-6",
                "display": "Systolic blood pressure",
                "unit": "mmHg"
            },
            "blood_pressure_diastolic": {
                "code": "8462-4",
                "display": "Diastolic blood pressure",
                "unit": "mmHg"
            }
        }
    })
