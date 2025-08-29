// Clinical Decision Support Service
import { DrugInteraction, ClinicalAlert, Allergy, Patient, Medication, ClinicalProtocol } from '../types';

export class ClinicalDecisionSupportService {
  private static drugInteractions: DrugInteraction[] = [
    {
      id: 'di001',
      drug1: 'warfarin',
      drug2: 'aspirin',
      severity: 'major',
      description: 'Increased risk of bleeding',
      clinicalSignificance: 'May result in increased anticoagulant effect and bleeding risk',
      management: 'Monitor INR closely. Consider alternative therapy or dose reduction.',
      documentation: 'excellent'
    },
    {
      id: 'di002',
      drug1: 'metformin',
      drug2: 'furosemide',
      severity: 'moderate',
      description: 'Risk of lactic acidosis',
      clinicalSignificance: 'Furosemide may increase risk of metformin-induced lactic acidosis',
      management: 'Monitor renal function and lactate levels',
      documentation: 'good'
    },
    {
      id: 'di003',
      drug1: 'digoxin',
      drug2: 'amiodarone',
      severity: 'major',
      description: 'Increased digoxin levels',
      clinicalSignificance: 'Amiodarone significantly increases serum digoxin concentrations',
      management: 'Reduce digoxin dose by 50% when starting amiodarone. Monitor levels.',
      documentation: 'excellent'
    }
  ];

  private static clinicalProtocols: ClinicalProtocol[] = [
    {
      id: 'cp001',
      name: 'Sepsis Management Protocol',
      condition: 'sepsis',
      department: 'Emergency',
      triggers: ['fever', 'hypotension', 'tachycardia', 'alteredMentalState'],
      steps: [
        {
          id: 'step001',
          stepNumber: 1,
          action: 'Obtain blood cultures before antibiotics',
          timing: 'Within 1 hour',
          responsible: ['Nurse'],
          documentation: ['bloodCultureTime', 'collectionSite']
        },
        {
          id: 'step002',
          stepNumber: 2,
          action: 'Administer broad-spectrum antibiotics',
          timing: 'Within 1 hour',
          responsible: ['Doctor', 'Pharmacist'],
          documentation: ['antibioticName', 'dose', 'administrationTime']
        },
        {
          id: 'step003',
          stepNumber: 3,
          action: 'Fluid resuscitation if hypotensive',
          timing: 'Within 3 hours',
          responsible: ['Doctor', 'Nurse'],
          documentation: ['fluidType', 'volume', 'response']
        }
      ],
      isActive: true,
      version: '2.1',
      lastUpdated: '2024-01-15T10:00:00Z'
    }
  ];

  // Check for drug interactions
  static checkDrugInteractions(medications: Medication[]): ClinicalAlert[] {
    const alerts: ClinicalAlert[] = [];
    
    for (let i = 0; i < medications.length; i++) {
      for (let j = i + 1; j < medications.length; j++) {
        const med1 = medications[i].name.toLowerCase();
        const med2 = medications[j].name.toLowerCase();
        
        const interaction = this.drugInteractions.find(di => 
          (di.drug1 === med1 && di.drug2 === med2) ||
          (di.drug1 === med2 && di.drug2 === med1)
        );

        if (interaction) {
          alerts.push({
            id: `alert_${interaction.id}_${Date.now()}`,
            patientId: '', // Will be set by caller
            type: 'drugInteraction',
            severity: interaction.severity as 'low' | 'medium' | 'high' | 'critical',
            message: `Drug Interaction: ${medications[i].name} + ${medications[j].name}`,
            details: `${interaction.description}. ${interaction.management}`,
            actionRequired: interaction.severity === 'major' || interaction.severity === 'contraindicated',
            suggestedActions: [
              'Review medication regimen',
              'Consider alternative therapy',
              'Monitor patient closely',
              'Consult pharmacist'
            ],
            timestamp: new Date().toISOString(),
            isAcknowledged: false
          });
        }
      }
    }
    
    return alerts;
  }

  // Check for allergy conflicts
  static checkAllergyConflicts(patient: Patient, newMedication: string): ClinicalAlert[] {
    const alerts: ClinicalAlert[] = [];
    
    // This would typically check against patient allergies
    // For now, simulate some common allergy checks
    const commonAllergies = ['penicillin', 'sulfa', 'aspirin', 'iodine'];
    const medName = newMedication.toLowerCase();
    
    commonAllergies.forEach(allergy => {
      if (medName.includes(allergy)) {
        alerts.push({
          id: `allergy_${allergy}_${Date.now()}`,
          patientId: patient.id,
          type: 'allergyWarning',
          severity: 'high',
          message: `Potential Allergy: ${newMedication}`,
          details: `Patient may have allergy to ${allergy}. Verify allergy history before administration.`,
          actionRequired: true,
          suggestedActions: [
            'Verify patient allergy history',
            'Consider alternative medication',
            'Consult physician',
            'Have emergency medications available'
          ],
          timestamp: new Date().toISOString(),
          isAcknowledged: false
        });
      }
    });
    
    return alerts;
  }

  // Check dosage alerts
  static checkDosageAlerts(medication: Medication, patient: Patient): ClinicalAlert[] {
    const alerts: ClinicalAlert[] = [];
    
    // Age-based dosing alerts
    if (patient.age >= 65) {
      const geriatricMeds = ['digoxin', 'warfarin', 'benzodiazepine'];
      const medName = medication.name.toLowerCase();
      
      if (geriatricMeds.some(med => medName.includes(med))) {
        alerts.push({
          id: `geriatric_${medication.id}_${Date.now()}`,
          patientId: patient.id,
          type: 'dosageAlert',
          severity: 'medium',
          message: `Geriatric Dosing Alert: ${medication.name}`,
          details: `Consider dose reduction for elderly patients. Standard adult doses may be too high.`,
          actionRequired: true,
          suggestedActions: [
            'Review geriatric dosing guidelines',
            'Consider dose reduction',
            'Monitor for adverse effects',
            'Consult pharmacist'
          ],
          timestamp: new Date().toISOString(),
          isAcknowledged: false
        });
      }
    }

    // Weight-based dosing alerts
    if (patient.weight && patient.weight < 50) {
      alerts.push({
        id: `weight_${medication.id}_${Date.now()}`,
        patientId: patient.id,
        type: 'dosageAlert',
        severity: 'medium',
        message: `Low Weight Dosing Alert: ${medication.name}`,
        details: `Patient weight (${patient.weight}kg) is below average. Consider weight-based dosing.`,
        actionRequired: true,
        suggestedActions: [
          'Calculate weight-based dose',
          'Review dosing guidelines',
          'Consider dose adjustment',
          'Monitor for toxicity'
        ],
        timestamp: new Date().toISOString(),
        isAcknowledged: false
      });
    }
    
    return alerts;
  }

  // Check clinical protocols
  static checkClinicalProtocols(patient: Patient): ClinicalAlert[] {
    const alerts: ClinicalAlert[] = [];
    
    // Check sepsis protocol triggers
    if (patient.vitals.temperature > 101.3 && patient.vitals.heartRate > 90) {
      alerts.push({
        id: `protocolSepsis${Date.now()}`,
        patientId: patient.id,
        type: 'clinicalGuideline',
        severity: 'high',
        message: 'Sepsis Protocol Triggered',
        details: 'Patient meets criteria for sepsis evaluation. Consider sepsis protocol.',
        actionRequired: true,
        suggestedActions: [
          'Initiate sepsis protocol',
          'Obtain blood cultures',
          'Consider antibiotics',
          'Monitor vital signs closely'
        ],
        timestamp: new Date().toISOString(),
        isAcknowledged: false
      });
    }

    // Check fall risk protocol
    if (patient.vitals.fallRisk === 'high' && patient.age >= 65) {
      alerts.push({
        id: `protocolFall${Date.now()}`,
        patientId: patient.id,
        type: 'fallRisk',
        severity: 'medium',
        message: 'High Fall Risk Patient',
        details: 'Patient has high fall risk. Implement fall prevention measures.',
        actionRequired: true,
        suggestedActions: [
          'Place fall risk armband',
          'Implement bed alarm',
          'Ensure call bell within reach',
          'Frequent safety rounds'
        ],
        timestamp: new Date().toISOString(),
        isAcknowledged: false
      });
    }
    
    return alerts;
  }

  // Comprehensive clinical decision support check
  static performClinicalCheck(patient: Patient, newMedication?: Medication): ClinicalAlert[] {
    let allAlerts: ClinicalAlert[] = [];
    
    // Check drug interactions
    allAlerts = allAlerts.concat(this.checkDrugInteractions(patient.medications));
    
    // Check clinical protocols
    allAlerts = allAlerts.concat(this.checkClinicalProtocols(patient));
    
    // If adding new medication
    if (newMedication) {
      allAlerts = allAlerts.concat(this.checkAllergyConflicts(patient, newMedication.name));
      allAlerts = allAlerts.concat(this.checkDosageAlerts(newMedication, patient));
    }
    
    // Set patient ID for all alerts
    allAlerts.forEach(alert => {
      alert.patientId = patient.id;
    });
    
    return allAlerts;
  }

  // Get clinical protocol by condition
  static getClinicalProtocol(condition: string): ClinicalProtocol | undefined {
    return this.clinicalProtocols.find(protocol => 
      protocol.condition.toLowerCase() === condition.toLowerCase()
    );
  }

  // Get all active protocols for department
  static getProtocolsForDepartment(department: string): ClinicalProtocol[] {
    return this.clinicalProtocols.filter(protocol => 
      protocol.department.toLowerCase() === department.toLowerCase() && protocol.isActive
    );
  }
}