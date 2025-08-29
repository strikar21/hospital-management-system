// PACS/Imaging Service - Handles medical imaging integration
import { ImagingStudy, ImagingImage, ImagingReport } from '../types';

export class ImagingService {
  // Mock imaging database
  private static mockImagingStudies: ImagingStudy[] = [
    {
      id: 'img001',
      patientId: 'P001',
      studyType: 'xray',
      bodyPart: 'chest',
      createdAt: '2024-08-27T09:30:00Z',
      status: 'completed',
      images: [
        {
          id: 'img001_1',
          url: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMTExIi8+CiAgPGNpcmNsZSBjeD0iMTUwIiBjeT0iMTAwIiByPSI0MCIgZmlsbD0iIzMzMyIgc3Ryb2tlPSIjNjY2IiBzdHJva2Utd2lkdGg9IjIiLz4KICA8ZWxsaXBzZSBjeD0iMTUwIiBjeT0iMTgwIiByeD0iNjAiIHJ5PSI0MCIgZmlsbD0iIzIyMiIgc3Ryb2tlPSIjNTU1IiBzdHJva2Utd2lkdGg9IjIiLz4KICA8dGV4dCB4PSIxNTAiIHk9IjI3MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iIzk5OSIgZm9udC1mYW1pbHk9Im1vbm9zcGFjZSIgZm9udC1zaXplPSIxMnB4Ij5DSEVTVCBYLUrbwsbit01PPC90ZXh0Pgo8L3N2Zz4=',
          thumbnail: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMTExIi8+CiAgPGNpcmNsZSBjeD0iNTAiIGN5PSIzNSIgcj0iMTUiIGZpbGw9IiMzMzMiLz4KICA8ZWxsaXBzZSBjeD0iNTAiIGN5PSI2NSIgcng9IjIwIiByeT0iMTUiIGZpbGw9IiMyMjIiLz4KPC9zdmc+',
          series: 'Series 1',
          instanceNumber: 1,
          viewPosition: 'PA'
        },
        {
          id: 'img001_2',
          url: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMTExIi8+CiAgPGVsbGlwc2UgY3g9IjE1MCIgY3k9IjE1MCIgcng9IjgwIiByeT0iMTAwIiBmaWxsPSIjMjIyIiBzdHJva2U9IiM0NDQiIHN0cm9rZS13aWR0aD0iMyIvPgogIDxyZWN0IHg9IjEyMCIgeT0iMTIwIiB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIGZpbGw9IiMzMzMiLz4KICA8dGV4dCB4PSIxNTAiIHk9IjI3MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iIzk5OSIgZm9udC1mYW1pbHk9Im1vbm9zcGFjZSIgZm9udC1zaXplPSIxMnB4Ij5DSEVTVCBYLUBBWSBMQVRFUKFMPC90ZXh0Pgo8L3N2Zz4=',
          thumbnail: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMTExIi8+CiAgPGVsbGlwc2UgY3g9IjUwIiBjeT0iNTAiIHJ4PSIzMCIgcnk9IjM1IiBmaWxsPSIjMjIyIi8+CiAgPHJlY3QgeD0iNDAiIHk9IjQwIiB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIGZpbGw9IiMzMzMiLz4KPC9zdmc+',
          series: 'Series 1',
          instanceNumber: 2,
          viewPosition: 'Lateral'
        }
      ],
      report: {
        id: 'rpt001',
        findings: 'Bilateral lung fields appear clear. No evidence of consolidation or pleural effusion. Cardiac silhouette is within normal limits.',
        impression: 'Normal chest X-ray examination.',
        recommendations: 'No immediate follow-up required based on current imaging.',
        performedBy: 'Dr. Wilson (Radiologist)',
        createdAt: '2024-08-27T11:15:00Z',
        status: 'final'
      },
      performedBy: 'Dr. Smith',
      technologist: 'Tech Rodriguez',
      radiologist: 'Dr. Wilson',
      urgency: 'routine'
    },
    {
      id: 'img002',
      patientId: 'P001',
      studyType: 'ct',
      bodyPart: 'abdomen',
      createdAt: '2024-08-26T14:00:00Z',
      status: 'completed',
      images: [
        {
          id: 'img002_1',
          url: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8ZGVmcz4KICAgIDxyYWRpYWxHcmFkaWVudCBpZD0iY3QiPgogICAgICA8c3RvcCBvZmZzZXQ9IjAlIiBzdG9wLWNvbG9yPSIjNDQ0Ii8+CiAgICAgIDxzdG9wIG9mZnNldD0iMTAwJSIgc3RvcC1jb2xvcj0iIzExMSIvPgogICAgPC9yYWRpYWxHcmFkaWVudD4KICA8L2RlZnM+CiAgPHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0iIzAwMCIvPgogIDxjaXJjbGUgY3g9IjE1MCIgY3k9IjE1MCIgcj0iMTIwIiBmaWxsPSJ1cmwoI2N0KSIvPgogIDxlbGxpcHNlIGN4PSIxMjAiIGN5PSIxMjAiIHJ4PSIyNSIgcnk9IjM1IiBmaWxsPSIjMjIyIi8+CiAgPGVsbGlwc2UgY3g9IjE4MCIgY3k9IjEyMCIgcng9IjI1IiByeT0iMzUiIGZpbGw9IiMyMjIiLz4KICA8dGV4dCB4PSIxNTAiIHk9IjI4MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZmlsbD0iIzk5OSIgZm9udC1mYW1pbHk9Im1vbm9zcGFjZSIgZm9udC1zaXplPSIxMnB4Ij5BQkRPTUVOIENUIFNDQU48L3RleHQ+Cjwvc3ZnPg==',
          thumbnail: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMDAwIi8+CiAgPGNpcmNsZSBjeD0iNTAiIGN5PSI1MCIgcj0iNDAiIGZpbGw9IiMzMzMiLz4KICA8ZWxsaXBzZSBjeD0iNDAiIGN5PSI0MCIgcng9IjEwIiByeT0iMTUiIGZpbGw9IiMyMjIiLz4KICA8ZWxsaXBzZSBjeD0iNjAiIGN5PSI0MCIgcng9IjEwIiByeT0iMTUiIGZpbGw9IiMyMjIiLz4KPC9zdmc+',
          series: 'Axial Series',
          instanceNumber: 1
        }
      ],
      report: {
        id: 'rpt002',
        findings: 'Abdominal organs appear within normal limits. Liver, spleen, pancreas, and kidneys show no abnormal enhancement. No evidence of free fluid or mass lesions.',
        impression: 'Normal CT abdomen examination.',
        recommendations: 'Continue clinical management as appropriate.',
        performedBy: 'Dr. Chen (Radiologist)',
        createdAt: '2024-08-26T16:45:00Z',
        status: 'final'
      },
      performedBy: 'Dr. Smith',
      technologist: 'Tech Martinez',
      radiologist: 'Dr. Chen',
      urgency: 'routine'
    },
    {
      id: 'img003',
      patientId: 'P001',
      studyType: 'ultrasound',
      bodyPart: 'cardiac',
      createdAt: '2024-08-25T10:00:00Z',
      status: 'completed',
      images: [
        {
          id: 'img003_1',
          url: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMDAwIi8+CiAgPGNpcmNsZSBjeD0iMTUwIiBjeT0iMTUwIiByPSI4MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjNjY2IiBzdHJva2Utd2lkdGg9IjMiLz4KICA8cGF0aCBkPSJNIDEwMCAxNTAgQSA1MCA1MCA0NSAwIDEgMjAwIDE1MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjOTk5IiBzdHJva2Utd2lkdGg9IjQiLz4KICA8Y2lyY2xlIGN4PSIxNTAiIGN5PSIxNTAiIHI9IjMwIiBmaWxsPSIjMzMzIi8+CiAgPHRleHQgeD0iMTUwIiB5PSIyODAiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiM5OTkiIGZvbnQtZmFtaWx5PSJtb25vc3BhY2UiIGZvbnQtc2l6ZT0iMTJweCI+Q0FSRElBQyBVTFRSQVNPVU5EPC90ZXh0Pgo8L3N2Zz4=',
          thumbnail: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMDAwIi8+CiAgPGNpcmNsZSBjeD0iNTAiIGN5PSI1MCIgcj0iMzAiIGZpbGw9Im5vbmUiIHN0cm9rZT0iIzY2NiIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPGNpcmNsZSBjeD0iNTAiIGN5PSI1MCIgcj0iMTUiIGZpbGw9IiMzMzMiLz4KPC9zdmc+',
          series: 'Echo Series',
          instanceNumber: 1
        }
      ],
      report: {
        id: 'rpt003',
        findings: 'Left ventricular function appears normal. No regional wall motion abnormalities noted. Ejection fraction estimated at 65%. Valvular function within normal limits.',
        impression: 'Normal echocardiogram.',
        recommendations: 'No immediate cardiac intervention required.',
        performedBy: 'Dr. Johnson (Cardiologist)',
        createdAt: '2024-08-25T11:30:00Z',
        status: 'final'
      },
      performedBy: 'Dr. Smith',
      technologist: 'Echo Tech Davis',
      radiologist: 'Dr. Johnson',
      urgency: 'routine'
    }
  ];

  // Get all imaging studies for a patient
  static async getPatientImagingStudies(patientId: string): Promise<ImagingStudy[]> {
    await new Promise(resolve => setTimeout(resolve, 800));
    return this.mockImagingStudies.filter(study => study.patientId === patientId);
  }

  // Get specific imaging study
  static async getImagingStudy(studyId: string): Promise<ImagingStudy | null> {
    await new Promise(resolve => setTimeout(resolve, 400));
    return this.mockImagingStudies.find(study => study.id === studyId) || null;
  }

  // Get images for a study
  static async getStudyImages(studyId: string): Promise<ImagingImage[]> {
    await new Promise(resolve => setTimeout(resolve, 600));
    const study = this.mockImagingStudies.find(s => s.id === studyId);
    return study?.images || [];
  }

  // Get imaging report
  static async getImagingReport(studyId: string): Promise<ImagingReport | null> {
    await new Promise(resolve => setTimeout(resolve, 300));
    const study = this.mockImagingStudies.find(s => s.id === studyId);
    return study?.report || null;
  }

  // Update study status
  static async updateStudyStatus(studyId: string, status: ImagingStudy['status']): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 500));
    const study = this.mockImagingStudies.find(s => s.id === studyId);
    if (study) {
      study.status = status;
    }
  }

  // Get study type color for UI
  static getStudyTypeColor(studyType: string): string {
    switch (studyType) {
      case 'xray':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'ct':
        return 'text-purple-600 bg-purple-50 border-purple-200';
      case 'mri':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'ultrasound':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'mammography':
        return 'text-pink-600 bg-pink-50 border-pink-200';
      case 'pet':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'nuclear':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  }

  // Get urgency color
  static getUrgencyColor(urgency: string): string {
    switch (urgency) {
      case 'stat':
        return 'text-red-600 bg-red-100';
      case 'urgent':
        return 'text-orange-600 bg-orange-100';
      case 'routine':
        return 'text-green-600 bg-green-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  }

  // Check if study has abnormal findings
  static hasAbnormalFindings(study: ImagingStudy): boolean {
    if (!study.report) return false;
    
    const abnormalKeywords = ['abnormal', 'lesion', 'mass', 'tumor', 'fracture', 'infection', 'inflammation'];
    const findings = study.report.findings.toLowerCase();
    
    return abnormalKeywords.some(keyword => findings.includes(keyword));
  }

  // Get studies that need immediate attention
  static getUrgentStudies(studies: ImagingStudy[]): ImagingStudy[] {
    return studies.filter(study => 
      study.urgency === 'stat' || 
      study.urgency === 'urgent' ||
      this.hasAbnormalFindings(study)
    );
  }

  // Format study description for display
  static formatStudyDescription(study: ImagingStudy): string {
    const typeMap = {
      'xray': 'X-Ray',
      'ct': 'CT Scan',
      'mri': 'MRI',
      'ultrasound': 'Ultrasound',
      'mammography': 'Mammography',
      'pet': 'PET Scan',
      'nuclear': 'Nuclear Medicine'
    };
    
    const type = typeMap[study.studyType as keyof typeof typeMap] || study.studyType.toUpperCase();
    const bodyPart = study.bodyPart.charAt(0).toUpperCase() + study.bodyPart.slice(1);
    
    return `${type} - ${bodyPart}`;
  }

  // Simulate DICOM viewer integration
  static openDicomViewer(imageUrl: string): void {
    // In real implementation, this would open a DICOM viewer
    window.open(imageUrl, '_blank', 'width=800,height=600');
  }

  // Generate imaging report for printing
  static generateImagingReport(study: ImagingStudy): string {
    const reportHeader = `IMAGING STUDY REPORT
Study ID: ${study.id}
Patient ID: ${study.patientId}
Study Type: ${this.formatStudyDescription(study)}
Study Date: ${new Date(study.createdAt).toLocaleString()}
Status: ${study.status.toUpperCase()}
Urgency: ${study.urgency.toUpperCase()}
----------------------------------------\n`;

    const clinicalInfo = `CLINICAL INFORMATION:
Ordered by: ${study.performedBy}
Technologist: ${study.technologist || 'N/A'}
Radiologist: ${study.radiologist || 'N/A'}
Number of Images: ${study.images.length}

`;

    const reportBody = study.report ? `FINDINGS:
${study.report.findings}

IMPRESSION:
${study.report.impression}

RECOMMENDATIONS:
${study.report.recommendations}

Reported by: ${study.report.performedBy}
Report Date: ${new Date(study.report.createdAt).toLocaleString()}
Status: ${study.report.status.toUpperCase()}
` : 'REPORT: Pending radiologist interpretation\n';

    const footer = `\n----------------------------------------
Report generated: ${new Date().toLocaleString()}
CONFIDENTIAL - For authorized personnel only`;

    return reportHeader + clinicalInfo + reportBody + footer;
  }
}