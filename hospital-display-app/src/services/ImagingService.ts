import { BaseService } from './BaseService';

export interface ImagingStudy {
  id: string;
  studyType: string;
  studyDate: string;
  description: string;
  status: 'scheduled' | 'in-progress' | 'completed' | 'cancelled';
  urgency: 'routine' | 'urgent' | 'stat';
  findings: string;
  abnormalFindings: boolean;
  images: any[];
}

export class ImagingService extends BaseService {
  static async getPatientImagingStudies(patientId: string): Promise<ImagingStudy[]> {
    // Placeholder implementation - returns empty array for now
    // In production this would fetch imaging studies from PACS or other imaging systems
    return [];
  }

  static formatStudyDescription(study: ImagingStudy): string {
    return `${study.studyType} - ${study.description}`;
  }

  static getStudyTypeColor(studyType: string): string {
    switch (studyType.toLowerCase()) {
      case 'ct': return 'bg-blue-100 border-blue-300 text-blue-800';
      case 'mri': return 'bg-purple-100 border-purple-300 text-purple-800';
      case 'xray': return 'bg-gray-100 border-gray-300 text-gray-800';
      case 'ultrasound': return 'bg-green-100 border-green-300 text-green-800';
      default: return 'bg-indigo-100 border-indigo-300 text-indigo-800';
    }
  }

  static getUrgencyColor(urgency: string): string {
    switch (urgency) {
      case 'stat': return 'bg-red-100 text-red-800';
      case 'urgent': return 'bg-orange-100 text-orange-800';
      default: return 'bg-green-100 text-green-800';
    }
  }

  static hasAbnormalFindings(study: ImagingStudy): boolean {
    return study.abnormalFindings;
  }

  static openDicomViewer(image: any): void {
    // Placeholder for DICOM viewer integration
    console.log('Opening DICOM viewer for image:', image);
  }

  static generateReport(study: ImagingStudy): string {
    // Placeholder for report generation
    return `Imaging Report for ${study.studyType} study on ${study.studyDate}`;
  }
}