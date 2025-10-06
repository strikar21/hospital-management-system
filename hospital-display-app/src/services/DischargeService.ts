import { BaseService } from './BaseService';
import { dischargeRequest } from '../types/PatientTypes';

export class DischargeService extends BaseService {

  static async requestDischarge(
    patientId: string,
    requestedBy: string,
    reason: string,
    notes?: string
  ): Promise<dischargeRequest> {
    const response = await this.fetchFromBackend('/discharge/request', {
      method: 'POST',
      body: JSON.stringify({ patientId, requestedBy, reason, notes })
    });
    return response;
  }

  static async approveDischarge(
    requestId: number,
    approvedBy: string,
    approvalNotes?: string
  ): Promise<dischargeRequest> {
    const response = await this.fetchFromBackend('/discharge/approve', {
      method: 'POST',
      body: JSON.stringify({ requestId, approvedBy, approvalNotes })
    });
    return response;
  }

  static async completeDischarge(
    requestId: number,
    performedBy: string,
    dischargeNotes?: string
  ): Promise<dischargeRequest> {
    const response = await this.fetchFromBackend('/discharge/complete', {
      method: 'POST',
      body: JSON.stringify({ requestId, performedBy, dischargeNotes })
    });
    return response;
  }

  static async getPendingRequests(): Promise<dischargeRequest[]> {
    const response = await this.fetchFromBackend('/discharge/pending');
    return Array.isArray(response) ? response : [];
  }

  static async getApprovedRequests(): Promise<dischargeRequest[]> {
    const response = await this.fetchFromBackend('/discharge/approved');
    return Array.isArray(response) ? response : [];
  }
}
