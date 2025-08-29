import asyncio
import math
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

from app.db.database import database, timescale_db
from app.services.vitals_service import VitalsService
from app.services.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

@dataclass
class PatientProfile:
    """Patient profile affecting vitals simulation"""
    patient_id: str
    age: int
    gender: str
    diagnosis: str
    status: str
    weight: Optional[float] = None

class VitalsSimulator:
    """Real-time vitals simulator for patients with assigned devices"""
    
    def __init__(self):
        self.running = False
        self.simulation_tasks = {}
        self.websocket_manager = WebSocketManager()
        
        # Base vitals ranges by age groups
        self.vitals_ranges = {
            "adult": {
                "heart_rate": (60, 100),
                "blood_pressure_systolic": (90, 140),
                "blood_pressure_diastolic": (60, 90),
                "respiratory_rate": (12, 20),
                "temperature": (36.1, 37.2),
                "oxygen_saturation": (95, 100)
            },
            "elderly": {
                "heart_rate": (55, 95),
                "blood_pressure_systolic": (100, 150),
                "blood_pressure_diastolic": (65, 95),
                "respiratory_rate": (14, 22),
                "temperature": (36.0, 37.0),
                "oxygen_saturation": (93, 100)
            },
            "child": {
                "heart_rate": (80, 120),
                "blood_pressure_systolic": (80, 120),
                "blood_pressure_diastolic": (50, 80),
                "respiratory_rate": (18, 30),
                "temperature": (36.2, 37.5),
                "oxygen_saturation": (95, 100)
            }
        }
        
        # Condition modifiers
        self.condition_modifiers = {
            "critical": {
                "heart_rate": 1.3,
                "blood_pressure_systolic": 1.2,
                "respiratory_rate": 1.4,
                "oxygen_saturation": 0.9
            },
            "unstable": {
                "heart_rate": 1.2,
                "blood_pressure_systolic": 1.1,
                "respiratory_rate": 1.2,
                "oxygen_saturation": 0.95
            },
            "stable": {
                "heart_rate": 1.0,
                "blood_pressure_systolic": 1.0,
                "respiratory_rate": 1.0,
                "oxygen_saturation": 1.0
            }
        }

    def get_age_category(self, age: int) -> str:
        """Categorize patient by age for vitals ranges"""
        if age < 18:
            return "child"
        elif age > 65:
            return "elderly"
        else:
            return "adult"

    def generate_ecg_sample(self, timestamp: datetime, heart_rate: int, quality: float = 0.95) -> Dict[str, Any]:
        """Generate realistic ECG waveform sample (P-QRS-T complex)"""
        # Calculate time phase based on heart rate
        cycle_length = 60.0 / heart_rate  # seconds per beat
        phase = (timestamp.timestamp() % cycle_length) / cycle_length * 2 * math.pi
        
        # P wave (0-0.3π)
        p_wave = 0.2 * math.exp(-((phase - 0.15*math.pi)**2) / (2 * (0.05*math.pi)**2)) if phase < 0.3*math.pi else 0
        
        # QRS complex (0.4π-0.6π) 
        if 0.4*math.pi <= phase <= 0.6*math.pi:
            qrs_phase = (phase - 0.5*math.pi) / (0.1*math.pi)
            if abs(qrs_phase) < 1:
                qrs_wave = 1.0 * (1 - qrs_phase**2) * math.sin(qrs_phase * math.pi)
            else:
                qrs_wave = 0
        else:
            qrs_wave = 0
            
        # T wave (0.7π-1.1π)
        t_wave = 0.3 * math.exp(-((phase - 0.9*math.pi)**2) / (2 * (0.1*math.pi)**2)) if 0.7*math.pi <= phase <= 1.1*math.pi else 0
        
        # Combine waves with noise
        baseline = 0.0
        noise = random.gauss(0, 0.02) * (1 - quality)
        ecg_value = baseline + p_wave + qrs_wave + t_wave + noise
        
        return {
            "timestamp": timestamp.isoformat(),
            "value": ecg_value,
            "heart_rate": heart_rate,
            "quality": quality,
            "waveform_phase": phase / (2 * math.pi)
        }

    def generate_eeg_sample(self, timestamp: datetime, patient_profile: PatientProfile) -> Dict[str, Any]:
        """Generate realistic EEG waveform sample"""
        # EEG frequency bands (Hz)
        alpha = 10.0  # 8-13 Hz
        beta = 20.0   # 13-30 Hz  
        theta = 6.0   # 4-8 Hz
        delta = 2.0   # 0.5-4 Hz
        
        t = timestamp.timestamp()
        
        # Generate different frequency components
        alpha_wave = 0.5 * math.sin(2 * math.pi * alpha * t)
        beta_wave = 0.2 * math.sin(2 * math.pi * beta * t + math.pi/3)
        theta_wave = 0.3 * math.sin(2 * math.pi * theta * t + math.pi/2)
        delta_wave = 0.4 * math.sin(2 * math.pi * delta * t + math.pi/4)
        
        # Combine waves based on patient state
        if patient_profile.status == "critical":
            # More delta waves in critical patients
            eeg_value = 0.6 * delta_wave + 0.2 * theta_wave + 0.1 * alpha_wave + 0.1 * beta_wave
        elif patient_profile.status == "sleeping" or "sedated" in patient_profile.diagnosis.lower():
            # More slow waves during sedation/sleep
            eeg_value = 0.4 * delta_wave + 0.4 * theta_wave + 0.2 * alpha_wave
        else:
            # Normal awake pattern
            eeg_value = 0.1 * delta_wave + 0.2 * theta_wave + 0.4 * alpha_wave + 0.3 * beta_wave
        
        # Add noise
        noise = random.gauss(0, 0.05)
        eeg_value += noise
        
        return {
            "timestamp": timestamp.isoformat(),
            "value": eeg_value,
            "dominant_frequency": alpha if patient_profile.status == "stable" else theta,
            "power_spectrum": {
                "delta": abs(delta_wave),
                "theta": abs(theta_wave), 
                "alpha": abs(alpha_wave),
                "beta": abs(beta_wave)
            }
        }

    def generate_vitals_for_patient(self, patient_profile: PatientProfile, device_id: str) -> Dict[str, Any]:
        """Generate all vitals for a patient based on their profile"""
        age_category = self.get_age_category(patient_profile.age)
        base_ranges = self.vitals_ranges[age_category]
        modifiers = self.condition_modifiers.get(patient_profile.status, self.condition_modifiers["stable"])
        
        now = datetime.utcnow()
        
        # Generate basic vitals with realistic variations
        heart_rate_base = random.randint(*base_ranges["heart_rate"])
        heart_rate = int(heart_rate_base * modifiers["heart_rate"])
        heart_rate = max(30, min(200, heart_rate))  # Safety bounds
        
        systolic_base = random.randint(*base_ranges["blood_pressure_systolic"])
        systolic = int(systolic_base * modifiers["blood_pressure_systolic"])
        
        diastolic_base = random.randint(*base_ranges["blood_pressure_diastolic"])
        diastolic = int(diastolic_base * modifiers.get("blood_pressure_diastolic", 1.0))
        
        resp_rate_base = random.randint(*base_ranges["respiratory_rate"])
        respiratory_rate = int(resp_rate_base * modifiers["respiratory_rate"])
        
        temp_base = random.uniform(*base_ranges["temperature"])
        temperature = temp_base + random.gauss(0, 0.2)
        
        o2_base = random.randint(*base_ranges["oxygen_saturation"])
        oxygen_saturation = int(o2_base * modifiers["oxygen_saturation"])
        oxygen_saturation = max(60, min(100, oxygen_saturation))  # Safety bounds
        
        # Generate waveform data
        ecg_data = self.generate_ecg_sample(now, heart_rate)
        eeg_data = self.generate_eeg_sample(now, patient_profile)
        
        return {
            "timestamp": now.isoformat(),
            "patient_id": patient_profile.patient_id,
            "device_id": device_id,
            "vitals": {
                "heart_rate": heart_rate,
                "blood_pressure": f"{systolic}/{diastolic}",
                "blood_pressure_systolic": systolic,
                "blood_pressure_diastolic": diastolic,
                "respiratory_rate": respiratory_rate,
                "temperature": round(temperature, 1),
                "oxygen_saturation": oxygen_saturation
            },
            "ecg": ecg_data,
            "eeg": eeg_data,
            "bioimpedance": random.randint(800, 1200),  # Ohms
            "tremor_level": random.uniform(0, 2.0) if patient_profile.status == "critical" else random.uniform(0, 0.5),
            "device_status": {
                "battery": random.randint(75, 100),
                "signal_strength": random.randint(80, 100),
                "quality": random.uniform(0.9, 1.0)
            }
        }

    async def simulate_patient_vitals(self, patient_profile: PatientProfile, device_id: str):
        """Continuous vitals simulation for a patient"""
        logger.info(f"Starting vitals simulation for patient {patient_profile.patient_id} on device {device_id}")
        
        try:
            while self.running and patient_profile.patient_id in self.simulation_tasks:
                # Generate vitals data
                vitals_data = self.generate_vitals_for_patient(patient_profile, device_id)
                
                # Store individual vital readings in TimescaleDB
                vitals = vitals_data["vitals"]
                timestamp = datetime.fromisoformat(vitals_data["timestamp"].replace('Z', '+00:00'))
                
                # Store basic vitals
                await VitalsService.store_vital_reading(
                    device_id, patient_profile.patient_id, "heart_rate", 
                    vitals["heart_rate"], "bpm"
                )
                await VitalsService.store_vital_reading(
                    device_id, patient_profile.patient_id, "blood_pressure_systolic", 
                    vitals["blood_pressure_systolic"], "mmHg"
                )
                await VitalsService.store_vital_reading(
                    device_id, patient_profile.patient_id, "blood_pressure_diastolic", 
                    vitals["blood_pressure_diastolic"], "mmHg"
                )
                await VitalsService.store_vital_reading(
                    device_id, patient_profile.patient_id, "respiratory_rate", 
                    vitals["respiratory_rate"], "breaths/min"
                )
                await VitalsService.store_vital_reading(
                    device_id, patient_profile.patient_id, "temperature", 
                    vitals["temperature"], "°C"
                )
                await VitalsService.store_vital_reading(
                    device_id, patient_profile.patient_id, "oxygen_saturation", 
                    vitals["oxygen_saturation"], "%"
                )
                
                # Store waveform data
                await VitalsService.store_vital_reading(
                    device_id, patient_profile.patient_id, "ecg_waveform", 
                    vitals_data["ecg"]["value"], "mV", metadata=vitals_data["ecg"]
                )
                await VitalsService.store_vital_reading(
                    device_id, patient_profile.patient_id, "eeg_waveform", 
                    vitals_data["eeg"]["value"], "µV", metadata=vitals_data["eeg"]
                )
                
                # Store other metrics
                await VitalsService.store_vital_reading(
                    device_id, patient_profile.patient_id, "bioimpedance", 
                    vitals_data["bioimpedance"], "Ω"
                )
                await VitalsService.store_vital_reading(
                    device_id, patient_profile.patient_id, "tremor_level", 
                    vitals_data["tremor_level"], "g"
                )
                
                # Update current vitals in PostgreSQL
                await self.update_current_vitals(patient_profile.patient_id, vitals_data)
                
                # Broadcast via WebSocket
                await self.websocket_manager.broadcast_patient_update(
                    patient_profile.patient_id, vitals_data
                )
                
                # Generate alerts if needed
                await self.check_and_generate_alerts(patient_profile, vitals_data)
                
                # Wait 1 second for next reading
                await asyncio.sleep(1.0)
                
        except asyncio.CancelledError:
            logger.info(f"Vitals simulation cancelled for patient {patient_profile.patient_id}")
        except Exception as e:
            logger.error(f"Error in vitals simulation for {patient_profile.patient_id}: {e}")
        finally:
            if patient_profile.patient_id in self.simulation_tasks:
                del self.simulation_tasks[patient_profile.patient_id]

    async def update_current_vitals(self, patient_id: str, vitals_data: Dict[str, Any]):
        """Update current vitals in PostgreSQL patient_current_vitals table"""
        try:
            query = """
                INSERT INTO patient_current_vitals (
                    patient_id, heart_rate, blood_pressure, blood_pressure_value, 
                    respiratory_rate, oxygen_sat, temperature, ecg, eeg, 
                    bioimpedance, tremor, last_updated, last_sync
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
                )
                ON CONFLICT (patient_id) DO UPDATE SET
                    heart_rate = EXCLUDED.heart_rate,
                    blood_pressure = EXCLUDED.blood_pressure,
                    blood_pressure_value = EXCLUDED.blood_pressure_value,
                    respiratory_rate = EXCLUDED.respiratory_rate,
                    oxygen_sat = EXCLUDED.oxygen_sat,
                    temperature = EXCLUDED.temperature,
                    ecg = EXCLUDED.ecg,
                    eeg = EXCLUDED.eeg,
                    bioimpedance = EXCLUDED.bioimpedance,
                    tremor = EXCLUDED.tremor,
                    last_updated = EXCLUDED.last_updated,
                    last_sync = EXCLUDED.last_sync
            """
            
            vitals = vitals_data["vitals"]
            now = datetime.utcnow()
            
            await database.execute(query, [
                patient_id,
                vitals["heart_rate"],
                vitals["blood_pressure"],
                vitals["blood_pressure_systolic"],
                vitals["respiratory_rate"],
                vitals["oxygen_saturation"],
                vitals["temperature"],
                int(vitals_data["ecg"]["value"] * 1000),  # Convert to integer
                int(vitals_data["eeg"]["value"] * 1000),  # Convert to integer
                vitals_data["bioimpedance"],
                vitals_data["tremor_level"],
                now.strftime("%H:%M:%S"),
                now.isoformat()
            ])
            
        except Exception as e:
            logger.error(f"Failed to update current vitals for {patient_id}: {e}")

    async def check_and_generate_alerts(self, patient_profile: PatientProfile, vitals_data: Dict[str, Any]):
        """Check vitals and generate alerts if values are outside normal ranges"""
        vitals = vitals_data["vitals"]
        alerts = []
        
        # Heart rate alerts
        if vitals["heart_rate"] > 100:
            alerts.append(("heart_rate", "high", f"Tachycardia: HR {vitals['heart_rate']} bpm"))
        elif vitals["heart_rate"] < 60:
            alerts.append(("heart_rate", "high", f"Bradycardia: HR {vitals['heart_rate']} bpm"))
        
        # Blood pressure alerts
        if vitals["blood_pressure_systolic"] > 140:
            alerts.append(("blood_pressure", "high", f"Hypertension: BP {vitals['blood_pressure']}"))
        elif vitals["blood_pressure_systolic"] < 90:
            alerts.append(("blood_pressure", "high", f"Hypotension: BP {vitals['blood_pressure']}"))
        
        # Oxygen saturation alerts
        if vitals["oxygen_saturation"] < 90:
            alerts.append(("oxygen", "critical", f"Low O2 Sat: {vitals['oxygen_saturation']}%"))
        
        # Temperature alerts
        if vitals["temperature"] > 38.0:
            alerts.append(("temperature", "medium", f"Fever: {vitals['temperature']}°C"))
        elif vitals["temperature"] < 35.0:
            alerts.append(("temperature", "high", f"Hypothermia: {vitals['temperature']}°C"))
        
        # Store alerts
        for alert_type, severity, message in alerts:
            await VitalsService.store_device_alert(
                vitals_data["device_id"],
                patient_profile.patient_id,
                alert_type,
                severity,
                message
            )

    async def start_simulation_for_patient(self, patient_id: str, device_id: str):
        """Start vitals simulation for a patient with an assigned device"""
        if patient_id in self.simulation_tasks:
            logger.warning(f"Simulation already running for patient {patient_id}")
            return
        
        # Get patient profile
        query = """
            SELECT id, name, age, gender, diagnosis, status, weight
            FROM patients 
            WHERE id = $1 AND "isActive" = true
        """
        
        patient_row = await database.fetch_one(query, [patient_id])
        if not patient_row:
            logger.error(f"Patient {patient_id} not found or inactive")
            return
        
        profile = PatientProfile(
            patient_id=patient_row["id"],
            age=patient_row["age"],
            gender=patient_row["gender"],
            diagnosis=patient_row["diagnosis"],
            status=patient_row["status"],
            weight=patient_row["weight"]
        )
        
        # Start simulation task
        task = asyncio.create_task(self.simulate_patient_vitals(profile, device_id))
        self.simulation_tasks[patient_id] = task
        
        logger.info(f"Started vitals simulation for patient {patient_id}")

    async def stop_simulation_for_patient(self, patient_id: str):
        """Stop vitals simulation for a patient"""
        if patient_id in self.simulation_tasks:
            self.simulation_tasks[patient_id].cancel()
            del self.simulation_tasks[patient_id]
            logger.info(f"Stopped vitals simulation for patient {patient_id}")

    async def start_all_simulations(self):
        """Start vitals simulation for all patients with assigned devices"""
        self.running = True
        
        # Get all patients with active device assignments
        query = """
            SELECT DISTINCT da.patient_id, da.device_id
            FROM device_assignments da
            JOIN patients p ON p.id = da.patient_id
            WHERE da.is_active = true AND p."isActive" = true
        """
        
        assignments = await database.fetch_all(query)
        
        for assignment in assignments:
            await self.start_simulation_for_patient(
                assignment["patient_id"], 
                assignment["device_id"]
            )
        
        logger.info(f"Started vitals simulation for {len(assignments)} patients")

    async def stop_all_simulations(self):
        """Stop all vitals simulations"""
        self.running = False
        
        # Cancel all tasks
        for patient_id, task in list(self.simulation_tasks.items()):
            task.cancel()
        
        # Wait for tasks to complete
        if self.simulation_tasks:
            await asyncio.gather(*self.simulation_tasks.values(), return_exceptions=True)
        
        self.simulation_tasks.clear()
        logger.info("Stopped all vitals simulations")

# Global simulator instance
vitals_simulator = VitalsSimulator()