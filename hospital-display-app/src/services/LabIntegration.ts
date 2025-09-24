import { BaseService } from './BaseService';

export interface LabResult {
  id: string;
  testName: string;
  value: string;
  unit: string;
  referenceRange: string;
  abnormalFlag: 'normal' | 'high' | 'low' | 'critical';
  timestamp: string;
}

export class LabIntegrationService extends BaseService {
  static async getpatientlabresults(patientId: string): Promise<LabResult[]> {
    // Placeholder implementation - returns empty array for now
    // In production this would fetch lab results from external lab systems
    return [];
  }

  static async updateinvestigationwithresults(investigation: any): Promise<any> {
    // Placeholder for updating investigation with lab results
    return investigation;
  }

  static getlabresultcolor(abnormalFlag: string): string {
    switch (abnormalFlag) {
      case 'critical': return 'bg-red-100 border-red-300 text-red-800';
      case 'high': return 'bg-orange-100 border-orange-300 text-orange-800';
      case 'low': return 'bg-yellow-100 border-yellow-300 text-yellow-800';
      default: return 'bg-green-100 border-green-300 text-green-800';
    }
  }

  static hasUrgentResults(labResults: LabResult[]): boolean {
    return labResults.some(result => result.abnormalFlag === 'critical');
  }

  static analyzeResults(labResults: LabResult[]): any {
    // Placeholder for lab result analysis
    return {
      criticalCount: labResults.filter(r => r.abnormalFlag === 'critical').length,
      abnormalCount: labResults.filter(r => r.abnormalFlag !== 'normal').length,
      totalCount: labResults.length
    };
  }
}