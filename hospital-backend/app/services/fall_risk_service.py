"""
Fall Risk Service - Comprehensive Two-Stage Fall Risk Assessment
Combines ESP32 IMU analysis with patient historical factors
STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case

Architecture:
1. ESP32 Watch: Real-time IMU motion analysis → imuFallRisk (0-10 scale)
2. Backend: Comprehensive risk assessment → final fallRisk (low/medium/high)

Clinical Factors Considered:
- Age (elderly at higher risk)
- Current medications (sedatives, antihypertensives, diuretics)
- Medical history (previous falls, stroke, Parkinson's, dementia)
- Mobility status (ambulatory, uses walker, wheelchair-bound)
- Cognitive status (confusion, disorientation)
- Recent vital sign instability (hypotension, arrhythmia)
- Environmental factors (time of day, location)
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class PatientRiskFactors:
    """Patient-specific risk factors for fall assessment"""
    # Demographics
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None  # kg

    # Medical History
    previousFalls: int = 0  # Number of falls in past 6 months
    strokeHistory: bool = False
    parkinsonsDisease: bool = False
    dementia: bool = False
    osteoporosis: bool = False
    arthritis: bool = False
    visionImpairment: bool = False
    hearingImpairment: bool = False
    diabetesWithNeuropathy: bool = False

    # Medications (high-risk categories)
    onSedatives: bool = False
    onAntihypertensives: bool = False
    onDiuretics: bool = False
    onAntidepressants: bool = False
    onAnticonvulsants: bool = False
    polyPharmacy: bool = False  # Taking 4+ medications

    # Mobility & Function
    mobilityStatus: Optional[str] = None  # 'ambulatory', 'walker', 'cane', 'wheelchair'
    usesMobilityAid: bool = False
    recentSurgery: bool = False
    bedRest: bool = False

    # Cognitive Status
    confusionPresent: bool = False
    disorientedToTime: bool = False
    disorientedToPlace: bool = False
    agitation: bool = False

    # Current Clinical State
    recentHypotensiveEpisode: bool = False
    recentArrhythmia: bool = False
    orthostatic: bool = False  # Orthostatic hypotension
    urinaryIncontinence: bool = False
    diarrhea: bool = False


@dataclass
class FallRiskResult:
    """Comprehensive fall risk assessment result"""
    riskLevel: str  # 'low', 'medium', 'high'
    riskScore: float  # 0.0-10.0 (normalized composite score)
    imuContribution: float  # Contribution from IMU (0.0-1.0)
    clinicalContribution: float  # Contribution from clinical factors (0.0-1.0)
    confidenceLevel: float  # 0.0-1.0 (how confident we are in the assessment)
    contributingFactors: List[str]  # List of factors contributing to risk
    recommendations: List[str]  # Clinical recommendations
    alertRequired: bool  # Whether to generate an alert
    previousRiskLevel: Optional[str] = None  # Previous risk level for trend detection


class FallRiskService:
    """
    Comprehensive Fall Risk Assessment Service

    Combines real-time IMU data from ESP32 watch with patient history
    to calculate a comprehensive fall risk score.

    Risk Score Calculation:
    - IMU Fall Risk (ESP32): 40% weight
    - Clinical Risk Factors: 60% weight

    Risk Levels:
    - Low: 0.0-3.0 → Routine monitoring
    - Medium: 3.1-6.0 → Enhanced precautions
    - High: 6.1-10.0 → Immediate intervention
    """

    def __init__(self):
        # IMU risk weight (40%)
        self.imuWeight = 0.4

        # Clinical factors weight (60%)
        self.clinicalWeight = 0.6

        # Age thresholds
        self.ageElderlyThreshold = 65
        self.ageVeryElderlyThreshold = 80

        # Fall history thresholds
        self.recentFallThreshold = 1  # Even 1 fall is significant

        # Risk level thresholds
        self.lowRiskThreshold = 3.0
        self.mediumRiskThreshold = 6.0

        # Alert thresholds
        self.alertOnRiskIncrease = True
        self.alertOnHighRisk = True

        logger.info("FallRiskService initialized")

    def calculate_comprehensive_fall_risk(
        self,
        imuFallRisk: float,
        patientFactors: PatientRiskFactors,
        recentVitals: Optional[Dict[str, Any]] = None,
        previousRiskLevel: Optional[str] = None
    ) -> FallRiskResult:
        """
        Calculate comprehensive fall risk combining IMU + clinical factors

        Args:
            imuFallRisk: Real-time IMU-based fall risk from ESP32 (0-10 scale)
            patientFactors: Patient-specific risk factors
            recentVitals: Recent vital signs data (optional)
            previousRiskLevel: Previous risk assessment level (for trend detection)

        Returns:
            FallRiskResult with comprehensive assessment
        """
        # Normalize IMU risk to 0.0-1.0
        normalizedImuRisk = min(max(imuFallRisk / 10.0, 0.0), 1.0)

        # Calculate clinical risk score (0.0-1.0)
        clinicalRiskScore, contributingFactors = self._calculate_clinical_risk_score(
            patientFactors, recentVitals
        )

        # Calculate weighted composite risk score (0.0-10.0 scale)
        compositeRisk = (
            (normalizedImuRisk * self.imuWeight * 10.0) +
            (clinicalRiskScore * self.clinicalWeight * 10.0)
        )

        # Determine risk level
        if compositeRisk <= self.lowRiskThreshold:
            riskLevel = 'low'
        elif compositeRisk <= self.mediumRiskThreshold:
            riskLevel = 'medium'
        else:
            riskLevel = 'high'

        # Generate recommendations
        recommendations = self._generate_recommendations(
            riskLevel, compositeRisk, contributingFactors, patientFactors
        )

        # Determine if alert is required
        alertRequired = self._should_generate_alert(
            riskLevel, previousRiskLevel, compositeRisk
        )

        # Calculate confidence level
        confidenceLevel = self._calculate_confidence_level(
            imuFallRisk, patientFactors, recentVitals
        )

        result = FallRiskResult(
            riskLevel=riskLevel,
            riskScore=round(compositeRisk, 2),
            imuContribution=round(normalizedImuRisk, 2),
            clinicalContribution=round(clinicalRiskScore, 2),
            confidenceLevel=round(confidenceLevel, 2),
            contributingFactors=contributingFactors,
            recommendations=recommendations,
            alertRequired=alertRequired,
            previousRiskLevel=previousRiskLevel
        )

        logger.info(
            f"Fall risk calculated: {riskLevel} (score={compositeRisk:.2f}, "
            f"IMU={normalizedImuRisk:.2f}, Clinical={clinicalRiskScore:.2f})"
        )

        return result

    def _calculate_clinical_risk_score(
        self,
        factors: PatientRiskFactors,
        recentVitals: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, List[str]]:
        """
        Calculate clinical risk score based on patient factors

        Returns:
            Tuple of (risk_score (0.0-1.0), contributing_factors)
        """
        riskScore = 0.0
        contributingFactors = []

        # ========================================
        # AGE FACTORS (0-15 points)
        # ========================================
        if factors.age:
            if factors.age >= self.ageVeryElderlyThreshold:
                riskScore += 15
                contributingFactors.append(f"Age {factors.age} (very elderly)")
            elif factors.age >= self.ageElderlyThreshold:
                riskScore += 10
                contributingFactors.append(f"Age {factors.age} (elderly)")

        # ========================================
        # FALL HISTORY (0-20 points)
        # ========================================
        if factors.previousFalls >= 3:
            riskScore += 20
            contributingFactors.append(f"{factors.previousFalls} falls in past 6 months")
        elif factors.previousFalls >= 1:
            riskScore += 15
            contributingFactors.append(f"{factors.previousFalls} fall(s) in past 6 months")

        # ========================================
        # NEUROLOGICAL CONDITIONS (0-15 points)
        # ========================================
        if factors.strokeHistory:
            riskScore += 10
            contributingFactors.append("History of stroke")

        if factors.parkinsonsDisease:
            riskScore += 15
            contributingFactors.append("Parkinson's disease")

        if factors.dementia:
            riskScore += 12
            contributingFactors.append("Dementia")

        if factors.diabetesWithNeuropathy:
            riskScore += 8
            contributingFactors.append("Diabetic neuropathy")

        # ========================================
        # MEDICATIONS (0-15 points)
        # ========================================
        medicationRisk = 0

        if factors.onSedatives:
            medicationRisk += 8
            contributingFactors.append("On sedatives")

        if factors.onAntihypertensives:
            medicationRisk += 5
            contributingFactors.append("On antihypertensives")

        if factors.onDiuretics:
            medicationRisk += 4
            contributingFactors.append("On diuretics")

        if factors.onAntidepressants:
            medicationRisk += 4
            contributingFactors.append("On antidepressants")

        if factors.onAnticonvulsants:
            medicationRisk += 5
            contributingFactors.append("On anticonvulsants")

        if factors.polyPharmacy:
            medicationRisk += 6
            contributingFactors.append("Polypharmacy (4+ medications)")

        # Cap medication risk at 15 points
        riskScore += min(medicationRisk, 15)

        # ========================================
        # MOBILITY & FUNCTION (0-12 points)
        # ========================================
        if factors.mobilityStatus == 'walker':
            riskScore += 8
            contributingFactors.append("Uses walker")
        elif factors.mobilityStatus == 'cane':
            riskScore += 6
            contributingFactors.append("Uses cane")
        elif factors.mobilityStatus == 'wheelchair':
            riskScore += 4
            contributingFactors.append("Wheelchair-bound (transfer risk)")

        if factors.recentSurgery:
            riskScore += 10
            contributingFactors.append("Recent surgery")

        if factors.bedRest:
            riskScore += 8
            contributingFactors.append("On bed rest (deconditioning)")

        # ========================================
        # COGNITIVE STATUS (0-10 points)
        # ========================================
        if factors.confusionPresent:
            riskScore += 10
            contributingFactors.append("Confusion present")

        if factors.disorientedToTime or factors.disorientedToPlace:
            riskScore += 8
            contributingFactors.append("Disoriented")

        if factors.agitation:
            riskScore += 6
            contributingFactors.append("Agitation")

        # ========================================
        # CURRENT CLINICAL STATE (0-10 points)
        # ========================================
        if factors.recentHypotensiveEpisode:
            riskScore += 8
            contributingFactors.append("Recent hypotensive episode")

        if factors.recentArrhythmia:
            riskScore += 7
            contributingFactors.append("Recent arrhythmia")

        if factors.orthostatic:
            riskScore += 10
            contributingFactors.append("Orthostatic hypotension")

        if factors.urinaryIncontinence or factors.diarrhea:
            riskScore += 5
            contributingFactors.append("Incontinence (rushing to bathroom)")

        # ========================================
        # SENSORY IMPAIRMENTS (0-8 points)
        # ========================================
        if factors.visionImpairment:
            riskScore += 6
            contributingFactors.append("Vision impairment")

        if factors.hearingImpairment:
            riskScore += 3
            contributingFactors.append("Hearing impairment")

        # ========================================
        # MUSCULOSKELETAL (0-8 points)
        # ========================================
        if factors.osteoporosis:
            riskScore += 5
            contributingFactors.append("Osteoporosis (high injury risk)")

        if factors.arthritis:
            riskScore += 4
            contributingFactors.append("Arthritis")

        # ========================================
        # VITAL SIGNS ANALYSIS (0-10 points)
        # ========================================
        if recentVitals:
            # Check for recent hypotension
            if recentVitals.get('bloodPressureSystolic', 120) < 90:
                riskScore += 8
                contributingFactors.append("Current hypotension")

            # Check for tachycardia
            if recentVitals.get('heartRate', 70) > 120:
                riskScore += 5
                contributingFactors.append("Current tachycardia")

            # Check for bradycardia
            if recentVitals.get('heartRate', 70) < 50:
                riskScore += 6
                contributingFactors.append("Current bradycardia")

            # Check for hypoxia
            if recentVitals.get('oxygenSaturation', 98) < 90:
                riskScore += 7
                contributingFactors.append("Current hypoxia")

        # Normalize to 0.0-1.0 scale (max possible score is ~140 points)
        maxPossibleScore = 140.0
        normalizedScore = min(riskScore / maxPossibleScore, 1.0)

        return normalizedScore, contributingFactors

    def _generate_recommendations(
        self,
        riskLevel: str,
        riskScore: float,
        factors: List[str],
        patientFactors: PatientRiskFactors
    ) -> List[str]:
        """Generate clinical recommendations based on risk level"""
        recommendations = []

        if riskLevel == 'high':
            recommendations.append("IMMEDIATE: Implement high fall risk precautions")
            recommendations.append("Place bed in lowest position with side rails up")
            recommendations.append("Consider 1:1 supervision or bed alarm")
            recommendations.append("Ensure call bell within reach at all times")
            recommendations.append("Assist with all transfers and ambulation")

            if patientFactors.confusionPresent:
                recommendations.append("Consider safety companion for confused patient")

            if patientFactors.onSedatives or patientFactors.onAntihypertensives:
                recommendations.append("Review medications with physician - consider dose reduction")

            if patientFactors.orthostatic:
                recommendations.append("Instruct patient to sit at bedside 1-2 min before standing")

        elif riskLevel == 'medium':
            recommendations.append("Implement moderate fall risk precautions")
            recommendations.append("Place fall risk sign on door and bed")
            recommendations.append("Assist with first ambulation after rest/sleep")
            recommendations.append("Keep pathway clear and well-lit")
            recommendations.append("Ensure non-slip footwear worn")

            if patientFactors.usesMobilityAid:
                recommendations.append("Ensure mobility aid is within easy reach")

            if patientFactors.urinaryIncontinence:
                recommendations.append("Scheduled toileting every 2-3 hours")

        else:  # low risk
            recommendations.append("Routine fall precautions apply")
            recommendations.append("Encourage independent mobility as tolerated")
            recommendations.append("Monitor for changes in condition")

        return recommendations

    def _should_generate_alert(
        self,
        currentLevel: str,
        previousLevel: Optional[str],
        riskScore: float
    ) -> bool:
        """Determine if an alert should be generated"""

        # Always alert on high risk
        if currentLevel == 'high' and self.alertOnHighRisk:
            return True

        # Alert on risk level increase
        if previousLevel and self.alertOnRiskIncrease:
            riskLevels = {'low': 0, 'medium': 1, 'high': 2}
            if riskLevels.get(currentLevel, 0) > riskLevels.get(previousLevel, 0):
                return True

        # Alert if risk score is very high (>8.0)
        if riskScore > 8.0:
            return True

        return False

    def _calculate_confidence_level(
        self,
        imuFallRisk: float,
        patientFactors: PatientRiskFactors,
        recentVitals: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate confidence level in the fall risk assessment

        Higher confidence when:
        - IMU data is present and not near edge cases
        - Complete patient factor data available
        - Recent vitals data available
        """
        confidence = 0.5  # Base confidence

        # IMU data quality (up to +0.2)
        if imuFallRisk > 0.5 and imuFallRisk < 9.5:
            # Not near edge cases (0 or 10)
            confidence += 0.2
        elif imuFallRisk > 0:
            confidence += 0.1

        # Patient factor completeness (up to +0.2)
        factorCount = 0
        totalFactors = 30  # Approximate number of factors we check

        if patientFactors.age is not None:
            factorCount += 1
        if patientFactors.previousFalls > 0:
            factorCount += 1
        if patientFactors.mobilityStatus:
            factorCount += 1

        # Count boolean factors that are True
        factorCount += sum([
            patientFactors.strokeHistory,
            patientFactors.parkinsonsDisease,
            patientFactors.dementia,
            patientFactors.onSedatives,
            patientFactors.onAntihypertensives,
            patientFactors.confusionPresent
        ])

        confidence += (factorCount / totalFactors) * 0.2

        # Recent vitals available (up to +0.1)
        if recentVitals:
            vitalCount = sum([
                'heartRate' in recentVitals,
                'bloodPressureSystolic' in recentVitals,
                'oxygenSaturation' in recentVitals
            ])
            confidence += (vitalCount / 3) * 0.1

        return min(confidence, 1.0)

    def extract_patient_risk_factors_from_db(
        self,
        patientRecord: Dict[str, Any]
    ) -> PatientRiskFactors:
        """
        Extract PatientRiskFactors from database patient record

        Args:
            patientRecord: Patient database record (dict)

        Returns:
            PatientRiskFactors dataclass instance
        """
        # Calculate age from dateOfBirth
        age = None
        if patientRecord.get('dateOfBirth'):
            from datetime import date
            dob = patientRecord['dateOfBirth']
            if isinstance(dob, str):
                dob = datetime.fromisoformat(dob.replace('Z', '+00:00')).date()
            today = date.today()
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Parse medical history (assuming it's a text field)
        medicalHistory = (patientRecord.get('medicalHistory') or '').lower()

        # Parse current medications (assuming it's a text field)
        currentMedications = (patientRecord.get('currentMedications') or '').lower()

        return PatientRiskFactors(
            age=age,
            gender=patientRecord.get('gender'),
            weight=patientRecord.get('weight'),

            # Medical history parsing (simple keyword matching)
            previousFalls=self._count_falls_in_history(medicalHistory),
            strokeHistory='stroke' in medicalHistory or 'cva' in medicalHistory,
            parkinsonsDisease='parkinson' in medicalHistory,
            dementia='dementia' in medicalHistory or 'alzheimer' in medicalHistory,
            osteoporosis='osteoporosis' in medicalHistory,
            arthritis='arthritis' in medicalHistory,
            diabetesWithNeuropathy='neuropathy' in medicalHistory and 'diabetes' in medicalHistory,

            # Medication parsing (simple keyword matching)
            onSedatives=any(med in currentMedications for med in ['lorazepam', 'diazepam', 'alprazolam', 'sedative']),
            onAntihypertensives=any(med in currentMedications for med in ['amlodipine', 'lisinopril', 'losartan', 'metoprolol']),
            onDiuretics=any(med in currentMedications for med in ['furosemide', 'hydrochlorothiazide', 'lasix']),
            onAntidepressants=any(med in currentMedications for med in ['sertraline', 'fluoxetine', 'escitalopram', 'ssri']),
            onAnticonvulsants=any(med in currentMedications for med in ['phenytoin', 'carbamazepine', 'valproate']),
            polyPharmacy=currentMedications.count(',') >= 3 if currentMedications else False,

            # These would ideally come from nursing assessments
            # For now, default to False (should be populated from dedicated fields)
            mobilityStatus=None,
            confusionPresent=False,
            usesMobilityAid=False,
            recentSurgery=False
        )

    def _count_falls_in_history(self, medicalHistory: str) -> int:
        """Count number of falls mentioned in medical history"""
        fallKeywords = ['fall', 'fell', 'fallen']
        count = 0
        for keyword in fallKeywords:
            count += medicalHistory.count(keyword)
        return min(count, 5)  # Cap at 5
