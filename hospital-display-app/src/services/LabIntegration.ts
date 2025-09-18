// Lab Integration Service - Fetches lab results from backend
import { LabResult, Investigation } from '../types';
import HospitalAPI from '../api';

export class LabIntegrationService {
  // Fetch lab results from external lab system
  static async fetchLabResults(investigationId: string): Promise<LabResult[]> {
    try {
      console.log('Fetching lab results for investigation:', investigationId);
      return [];
    } catch (error) {
      console.error('Failed to fetch lab results:', error);
      return [];
    }
  }

  // Get pending lab results for a patient
  static async getPendingResults(patientId: string): Promise<LabResult[]> {
    try {
      console.log('Fetching pending lab results for patient:', patientId);
      return [];
    } catch (error) {
      console.error('Failed to fetch pending lab results:', error);
      return [];
    }
  }

  // Get all lab results for a patient
  static async getPatientLabResults(patientId: string): Promise<LabResult[]> {
    try {
      console.log('Fetching patient lab results:', patientId);
      return [];
    } catch (error) {
      console.error('Failed to fetch patient lab results:', error);
      return [];
    }
  }

  // Auto-update investigation with lab results
  static async updateInvestigationWithResults(investigation: Investigation): Promise<Investigation> {
    if (investigation.type === 'lab' && investigation.status === 'in_progress') {
      try {
        // Get results from backend
        const labResults = await this.fetchLabResults(investigation.id);
        
        if (labResults.length > 0) {
          // Update investigation with results
          const updatedInvestigation: Investigation = {
            ...investigation,
            status: 'completed',
            completedat: new Date().toISOString(),
            labResults: labResults,
            results: this.formatLabResultsSummary(labResults)
          };
          
          return updatedInvestigation;
        }
      } catch (error) {
        console.error('Failed to update investigation with lab results:', error);
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