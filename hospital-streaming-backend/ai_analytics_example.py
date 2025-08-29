#!/usr/bin/env python3
"""
AI Analytics Examples for Hospital Patient Data
Shows how stored patient data can be used for AI/ML analysis
"""

import asyncio
import asyncpg
import pandas as pd
from datetime import datetime, timedelta
import json

# Example AI/ML capabilities using stored patient data

async def get_patient_vitals_for_ai(patient_id: str, hours: int = 24):
    """Extract patient vitals for AI analysis"""
    
    conn = await asyncpg.connect(
        "postgresql://hospital_user:hospital_pass@localhost:5433/hospital_vitals"
    )
    
    try:
        # Get comprehensive vital signs data
        query = """
        SELECT 
            timestamp,
            vital_type,
            value,
            unit,
            quality_indicator,
            metadata->>'source' as data_source,
            metadata->>'signal_quality' as signal_quality,
            metadata->>'battery_level' as battery_level
        FROM vital_readings 
        WHERE patient_id = $1 
        AND timestamp > NOW() - INTERVAL '%s hours'
        ORDER BY timestamp DESC
        """ % hours
        
        rows = await conn.fetch(query, patient_id)
        
        # Convert to pandas DataFrame for AI analysis
        df = pd.DataFrame(rows)
        return df
        
    finally:
        await conn.close()

async def get_patient_complete_profile(patient_id: str):
    """Get complete patient profile for AI context"""
    
    # Connect to main database for case sheet data
    main_conn = await asyncpg.connect(
        "postgresql://hospital_user:hospital_pass@localhost:5432/hospital_streaming"
    )
    
    # Connect to TimescaleDB for vitals data
    ts_conn = await asyncpg.connect(
        "postgresql://hospital_user:hospital_pass@localhost:5433/hospital_vitals"
    )
    
    try:
        # Get patient basic info
        patient_info = await main_conn.fetchrow("""
            SELECT id, name, age, gender, diagnosis, ward, room, 
                   admission_date, assigned_doctor, status
            FROM patients WHERE id = $1
        """, patient_id)
        
        # Get clinical notes
        notes = await main_conn.fetch("""
            SELECT timestamp, author_name, author_role, content 
            FROM patient_notes WHERE patient_id = $1 
            ORDER BY timestamp DESC
        """, patient_id)
        
        # Get investigations
        investigations = await main_conn.fetch("""
            SELECT ordered_date, name, type, status, results, ordered_by
            FROM patient_investigations WHERE patient_id = $1
            ORDER BY ordered_date DESC
        """, patient_id)
        
        # Get therapies
        therapies = await main_conn.fetch("""
            SELECT start_date, type, description, frequency, 
                   status, prescribed_by
            FROM patient_therapies WHERE patient_id = $1
            ORDER BY start_date DESC
        """, patient_id)
        
        # Get vital signs summary
        vital_summary = await ts_conn.fetchrow("""
            SELECT 
                COUNT(*) as total_readings,
                COUNT(DISTINCT vital_type) as vital_types,
                MIN(timestamp) as first_reading,
                MAX(timestamp) as last_reading,
                AVG(CASE WHEN vital_type = 'heart_rate' THEN value END) as avg_heart_rate,
                AVG(CASE WHEN vital_type = 'temperature' THEN value END) as avg_temperature,
                AVG(CASE WHEN vital_type = 'oxygen_saturation' THEN value END) as avg_oxygen_sat
            FROM vital_readings WHERE patient_id = $1
        """, patient_id)
        
        # Get recent alerts
        alerts = await ts_conn.fetch("""
            SELECT timestamp, alert_type, severity, message, metadata
            FROM device_alerts_ts WHERE patient_id = $1
            ORDER BY timestamp DESC LIMIT 10
        """, patient_id)
        
        return {
            "patient_info": dict(patient_info) if patient_info else None,
            "notes": [dict(note) for note in notes],
            "investigations": [dict(inv) for inv in investigations],
            "therapies": [dict(therapy) for therapy in therapies],
            "vital_summary": dict(vital_summary) if vital_summary else None,
            "recent_alerts": [dict(alert) for alert in alerts]
        }
        
    finally:
        await main_conn.close()
        await ts_conn.close()

# AI Analysis Examples

def ai_trend_analysis(vitals_df):
    """AI: Analyze vital sign trends"""
    
    # Pivot data for trend analysis
    pivot_df = vitals_df.pivot(index='timestamp', columns='vital_type', values='value')
    
    # Detect trends
    trends = {}
    for vital in pivot_df.columns:
        data = pivot_df[vital].dropna()
        if len(data) > 5:
            # Simple trend detection (can be replaced with ML models)
            recent_avg = data.tail(10).mean()
            earlier_avg = data.head(10).mean()
            
            if recent_avg > earlier_avg * 1.1:
                trends[vital] = "INCREASING"
            elif recent_avg < earlier_avg * 0.9:
                trends[vital] = "DECREASING" 
            else:
                trends[vital] = "STABLE"
    
    return trends

def ai_anomaly_detection(vitals_df):
    """AI: Detect anomalies in vital signs"""
    
    anomalies = []
    
    for vital_type in vitals_df['vital_type'].unique():
        vital_data = vitals_df[vitals_df['vital_type'] == vital_type]
        values = vital_data['value'].values
        
        if len(values) > 10:
            # Simple statistical anomaly detection
            mean_val = values.mean()
            std_val = values.std()
            threshold = 2.5  # 2.5 standard deviations
            
            for idx, value in enumerate(values):
                z_score = abs((value - mean_val) / std_val)
                if z_score > threshold:
                    timestamp = vital_data.iloc[idx]['timestamp']
                    anomalies.append({
                        'timestamp': timestamp,
                        'vital_type': vital_type,
                        'value': value,
                        'z_score': z_score,
                        'severity': 'HIGH' if z_score > 3 else 'MEDIUM'
                    })
    
    return anomalies

def ai_risk_assessment(patient_profile):
    """AI: Comprehensive risk assessment"""
    
    risk_score = 0
    risk_factors = []
    
    # Analyze patient demographics
    if patient_profile['patient_info']:
        age = patient_profile['patient_info'].get('age', 0)
        if age > 65:
            risk_score += 10
            risk_factors.append("Advanced age")
    
    # Analyze vital trends
    if patient_profile['vital_summary']:
        avg_hr = patient_profile['vital_summary'].get('avg_heart_rate', 0)
        avg_temp = patient_profile['vital_summary'].get('avg_temperature', 0)
        avg_o2 = patient_profile['vital_summary'].get('avg_oxygen_sat', 100)
        
        if avg_hr > 100:
            risk_score += 15
            risk_factors.append("Elevated average heart rate")
        
        if avg_temp > 100.4:
            risk_score += 10
            risk_factors.append("Elevated temperature")
            
        if avg_o2 < 95:
            risk_score += 20
            risk_factors.append("Low oxygen saturation")
    
    # Analyze recent alerts
    critical_alerts = [a for a in patient_profile['recent_alerts'] if a['severity'] == 'critical']
    if len(critical_alerts) > 5:
        risk_score += 25
        risk_factors.append("Multiple critical alerts")
    
    # Determine risk level
    if risk_score >= 50:
        risk_level = "HIGH"
    elif risk_score >= 25:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "recommendation": get_ai_recommendation(risk_level, risk_factors)
    }

def get_ai_recommendation(risk_level, risk_factors):
    """AI: Generate clinical recommendations"""
    
    recommendations = []
    
    if risk_level == "HIGH":
        recommendations.append("Immediate physician consultation required")
        recommendations.append("Consider continuous monitoring")
        
    if "Low oxygen saturation" in risk_factors:
        recommendations.append("Check oxygen therapy requirements")
        recommendations.append("Consider arterial blood gas analysis")
        
    if "Elevated average heart rate" in risk_factors:
        recommendations.append("ECG monitoring recommended")
        recommendations.append("Review cardiac medications")
        
    if "Multiple critical alerts" in risk_factors:
        recommendations.append("Increase monitoring frequency")
        recommendations.append("Notify attending physician")
    
    return recommendations

def ai_clinical_summary(patient_profile):
    """AI: Generate clinical summary from all patient data"""
    
    patient = patient_profile['patient_info']
    vitals = patient_profile['vital_summary']
    notes = patient_profile['notes']
    
    # Generate AI summary
    summary = f"""
    PATIENT: {patient['name']} (Age: {patient['age']}, {patient['gender']})
    ADMISSION: {patient['admission_date']} - {patient['diagnosis']}
    LOCATION: {patient['ward']}, Room {patient['room']}
    
    VITAL SIGNS ANALYSIS:
    - Total readings: {vitals['total_readings']} over {vitals['vital_types']} vital types
    - Average heart rate: {vitals['avg_heart_rate']:.1f} BPM
    - Average temperature: {vitals['avg_temperature']:.1f}°F  
    - Average oxygen saturation: {vitals['avg_oxygen_sat']:.1f}%
    - Monitoring period: {vitals['first_reading']} to {vitals['last_reading']}
    
    CLINICAL NOTES SUMMARY:
    - {len(notes)} clinical notes from healthcare team
    - Latest note: {notes[0]['content'][:100]}... ({notes[0]['author_name']})
    
    ALERTS: {len(patient_profile['recent_alerts'])} recent alerts
    """
    
    return summary.strip()

# Example usage function
async def demonstrate_ai_capabilities():
    """Demonstrate AI capabilities on stored patient data"""
    
    print("🤖 AI ANALYTICS DEMONSTRATION")
    print("=" * 50)
    
    # Get complete patient profile
    patient_profile = await get_patient_complete_profile("TEST001")
    
    if patient_profile['patient_info']:
        print("\n1. CLINICAL SUMMARY:")
        summary = ai_clinical_summary(patient_profile)
        print(summary)
        
        print("\n2. RISK ASSESSMENT:")
        risk_assessment = ai_risk_assessment(patient_profile)
        print(f"Risk Level: {risk_assessment['risk_level']}")
        print(f"Risk Score: {risk_assessment['risk_score']}")
        print("Risk Factors:", ", ".join(risk_assessment['risk_factors']))
        print("Recommendations:")
        for rec in risk_assessment['recommendation']:
            print(f"  - {rec}")
        
        # Get vitals for trend analysis
        vitals_df = await get_patient_vitals_for_ai("TEST001", 24)
        
        if not vitals_df.empty:
            print("\n3. TREND ANALYSIS:")
            trends = ai_trend_analysis(vitals_df)
            for vital, trend in trends.items():
                print(f"  {vital}: {trend}")
            
            print("\n4. ANOMALY DETECTION:")
            anomalies = ai_anomaly_detection(vitals_df)
            print(f"  Found {len(anomalies)} anomalies")
            for anomaly in anomalies[:3]:  # Show top 3
                print(f"  - {anomaly['vital_type']}: {anomaly['value']} (Z-score: {anomaly['z_score']:.2f})")
    
    else:
        print("No patient data found for TEST001")

if __name__ == "__main__":
    # This demonstrates how stored patient data can be used for AI analysis
    print("📋 This file shows AI capabilities - run demonstrate_ai_capabilities() to test")
    print("🔬 Capabilities include:")
    print("  - Trend analysis across all vital signs")
    print("  - Anomaly detection using statistical methods") 
    print("  - Risk assessment based on patient profile")
    print("  - Clinical summary generation")
    print("  - Intelligent recommendations")
    print("💡 Ready for integration with advanced ML models!")