// Lab Integration Service - Simulates automatic lab result import
import { LabResult, Investigation } from '../types';

export class LabIntegrationService {
  // Mock lab results database
  private static mockLabResults: LabResult[] = [
    {
      id: 'lab001',
      patientId: 'P001',
      testName: 'Complete Blood Count',
      testCode: 'CBC',
      result: '12.5',
      normalRange: '12.0-15.5',
      units: 'g/dL',
      status: 'final',
      abnormalFlag: 'normal',
      createdAt: '2024-08-27T08:00:00Z',
      completedAt: '2024-08-27T10:30:00Z',
      performingLab: 'Central Lab',
      performedBy: 'Dr. Smith',
      performedBy: 'Lab Tech Johnson'
    },
    {
      id: 'lab002',
      patientId: 'P001',
      testName: 'White Blood Cell Count',
      testCode: 'WBC',
      result: '15.2',
      normalRange: '4.0-11.0',
      units: '10³/μL',
      status: 'final',
      abnormalFlag: 'high',
      createdAt: '2024-08-27T08:00:00Z',
      completedAt: '2024-08-27T10:30:00Z',
      performingLab: 'Central Lab',
      performedBy: 'Dr. Smith',
      performedBy: 'Lab Tech Johnson'
    },
    {
      id: 'lab003',
      patientId: 'P001',
      testName: 'Hemoglobin',
      testCode: 'HGB',
      result: '12.1',
      normalRange: '12.0-15.5',
      units: 'g/dL',
      status: 'final',
      abnormalFlag: 'normal',
      createdAt: '2024-08-27T08:00:00Z',
      completedAt: '2024-08-27T10:30:00Z',
      performingLab: 'Central Lab',
      performedBy: 'Dr. Smith'
    },
    {
      id: 'lab004',
      patientId: 'P001',
      testName: 'Creatinine',
      testCode: 'CREAT',
      result: '2.1',
      normalRange: '0.6-1.2',
      units: 'mg/dL',
      status: 'final',
      abnormalFlag: 'high',
      createdAt: '2024-08-27T14:00:00Z',
      completedAt: '2024-08-27T16:15:00Z',
      performingLab: 'Chemistry Lab',
      performedBy: 'Dr. Smith',
      performedBy: 'Lab Tech Williams'
    },
    {
      id: 'lab005',
      patientId: 'P001',
      testName: 'Blood Glucose',
      testCode: 'GLUC',
      result: '245',
      normalRange: '70-100',
      units: 'mg/dL',
      status: 'final',
      abnormalFlag: 'criticalHigh',
      createdAt: '2024-08-27T14:00:00Z',
      completedAt: '2024-08-27T16:15:00Z',
      performingLab: 'Chemistry Lab',
      performedBy: 'Dr. Smith',
      performedBy: 'Lab Tech Williams'
    }
  ];

  // Simulate fetching lab results from external lab system
  static async fetchLabResults(investigationId: string): Promise<LabResult[]> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Return mock results based on investigation
    return this.mockLabResults.filter(result => 
      // In real implementation, this would match by investigation order ID
      result.patientId === 'P001'
    );
  }

  // Get pending lab results for a patient
  static async getPendingResults(patientId: string): Promise<LabResult[]> {
    await new Promise(resolve => setTimeout(resolve, 500));
    
    return this.mockLabResults.filter(result => 
      result.patientId === patientId && result.status === 'preliminary'
    );
  }

  // Get all lab results for a patient
  static async getPatientLabResults(patientId: string): Promise<LabResult[]> {
    await new Promise(resolve => setTimeout(resolve, 800));
    
    return this.mockLabResults.filter(result => result.patientId === patientId);
  }

  // Auto-update investigation with lab results
  static async updateInvestigationWithResults(investigation: Investigation): Promise<Investigation> {
    if (investigation.type === 'lab' && investigation.status === 'inProgress') {
      // Simulate getting results from lab system
      const labResults = await this.fetchLabResults(investigation.id);
      
      if (labResults.length > 0) {
        // Update investigation with results
        const updatedInvestigation: Investigation = {
          ...investigation,
          status: 'completed',
          completedAt: new Date().toISOString(),
          labResults: labResults,
          results: this.formatLabResultsSummary(labResults)
        };
        
        return updatedInvestigation;
      }
    }
    
    return investigation;
  }

  // Format lab results into a readable summary
  static formatLabResultsSummary(labResults: LabResult[]): string {
    const abnormalResults = labResults.filter(result => 
      result.abnormalFlag !== 'normal'
    );
    
    if (abnormalResults.length === 0) {
      return `All ${labResults.length} tests within normal limits`;
    }
    
    const summary = abnormalResults.map(result => 
      `${result.testName}: ${result.result} ${result.units} (${result.abnormalFlag.toUpperCase()})`
    ).join('; ');
    
    return `${abnormalResults.length} abnormal: ${summary}`;
  }

  // Get lab result status color for UI
  static getLabResultColor(abnormalFlag: string): string {
    switch (abnormalFlag) {
      case 'criticalHigh':
      case 'criticalLow':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'high':
      case 'low':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'normal':
        return 'text-green-600 bg-green-50 border-green-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  }

  // Check if lab results need immediate attention
  static hasUrgentResults(labResults: LabResult[]): boolean {
    return labResults.some(result => 
      result.abnormalFlag === 'criticalHigh' || result.abnormalFlag === 'criticalLow'
    );
  }

  // Get lab results that need physician review
  static getResultsNeedingReview(labResults: LabResult[]): LabResult[] {
    return labResults.filter(result => 
      result.abnormalFlag !== 'normal' && !result.performedBy
    );
  }

  // Simulate real-time lab result notifications
  static simulateLabResultNotification(patientId: string, callback: (results: LabResult[]) => void): void {
    // Simulate getting new results every 30 seconds
    setInterval(() => {
      const newResults = this.mockLabResults.filter(result => 
        result.patientId === patientId && 
        new Date(result.completedAt) > new Date(Date.now() - 30000) // Last 30 seconds
      );
      
      if (newResults.length > 0) {
        callback(newResults);
      }
    }, 30000);
  }

  // Generate lab result report for printing/export
  static generateLabReport(patientId: string, labResults: LabResult[]): string {
    const reportHeader = `LAB RESULTS REPORT
Patient ID: ${patientId}
Generated: ${new Date().toLocaleString()}
Laboratory: Central Hospital Lab
----------------------------------------\n`;

    const resultLines = labResults.map(result => 
      `${result.testName} (${result.testCode}):
  Result: ${result.result} ${result.units}
  Normal Range: ${result.normalRange}
  Status: ${result.abnormalFlag.toUpperCase()}
  Collection: ${new Date(result.createdAt).toLocaleString()}
  Verified by: ${result.performedBy || 'Pending verification'}
`
    ).join('\n');

    const abnormalCount = labResults.filter(r => r.abnormalFlag !== 'normal').length;
    const footer = `\n----------------------------------------
Total Tests: ${labResults.length}
Abnormal Results: ${abnormalCount}
Status: ${abnormalCount > 0 ? 'REQUIRES REVIEW' : 'NORMAL'}`;

    return reportHeader + resultLines + footer;
  }
}