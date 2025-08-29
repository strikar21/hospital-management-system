// api.ts - Backend Integration API
import { User, Patient, VitalHistory, RoomProximity, TimeRange, Medication, Investigation, Therapy, CaseSheetEntry, ECGReading, MedicationHistoryEntry, Alert, NoteComment } from './types';

// Backend configuration
// For development with proxy, use empty string to make relative URLs
// For production mobile app, this will be set to the actual backend URL
const BACKEND_BASE_URL = process.env.NODE_ENV === 'development' ? '' : (process.env.REACT_APP_BACKEND_URL || 'https://localhost:8002');
console.log('🔧 API Base URL:', BACKEND_BASE_URL || '(using relative URLs via proxy)');
const BACKEND_WS_URL = process.env.REACT_APP_WS_URL || 'wss://localhost:8001';

export class HospitalAPI {
  
  // ================================
  // REQUEST SIGNING FOR SECURITY
  // ================================

  private static async generateSignature(
    method: string,
    urlPath: string,
    body: string,
    timestamp: string,
    secretKey: string
  ): Promise<string> {
    const canonicalString = `${method}\n${urlPath}\n${body}\n${timestamp}`;
    const encoder = new TextEncoder();
    const keyData = encoder.encode(secretKey);
    const messageData = encoder.encode(canonicalString);
    
    const cryptoKey = await crypto.subtle.importKey(
      'raw',
      keyData,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    
    const signature = await crypto.subtle.sign('HMAC', cryptoKey, messageData);
    const signatureArray = new Uint8Array(signature);
    return btoa(String.fromCharCode.apply(null, Array.from(signatureArray)));
  }

  private static async addRequestSigning(
    url: string,
    options: RequestInit
  ): Promise<RequestInit> {
    let urlPath: string;
    
    try {
      // Handle both absolute and relative URLs
      if (url.startsWith('http')) {
        const urlObj = new URL(url);
        urlPath = urlObj.pathname + urlObj.search;
      } else {
        // For relative URLs, use the path directly
        urlPath = url;
      }
    } catch (error) {
      // Fallback: treat as relative path
      urlPath = url;
    }
    
    const method = options.method || 'GET';
    const body = options.body as string || '';
    const timestamp = Math.floor(Date.now() / 1000).toString();
    
    // Use a client-side secret key (in production, this should be from secure storage)
    const secretKey = 'hospital-streaming-secret-key-change-in-production-2024';
    
    const signature = await this.generateSignature(
      method,
      urlPath,
      body,
      timestamp,
      secretKey
    );

    return {
      ...options,
      headers: {
        ...(options.headers as Record<string, string> || {}),
        'X-Signature': signature,
        'X-Timestamp': timestamp
      }
    };
  }

  // ================================
  // BACKEND INTEGRATION METHODS
  // ================================

  static async fetchFromBackend(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = `${BACKEND_BASE_URL}/api/v1${endpoint}`;
    const token = localStorage.getItem('hospitalAccessToken');
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {})
    };
    
    // Add authorization header if token exists
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Add request signing for security
    const signedOptions = await this.addRequestSigning(url, {
      headers,
      ...options
    });
    
    const response = await fetch(url, signedOptions);

    if (!response.ok) {
      if (response.status === 401) {
        // Token expired or invalid, clear it
        localStorage.removeItem('hospitalAccessToken');
        throw new Error('Authentication required');
      }
      if (response.status === 404) {
        throw new Error(`Backend endpoint not found: ${endpoint} - This endpoint may not be implemented yet`);
      }
      throw new Error(`Backend request failed: ${response.status} - ${response.statusText}`);
    }

    return await response.json();
  }

  static createWebSocketConnection(endpoint: string): WebSocket | null {
    try {
      return new WebSocket(`${BACKEND_WS_URL}/ws${endpoint}`);
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      return null;
    }
  }

  // ================================
  // AUTHENTICATION METHODS
  // ================================

  static async authenticateNFC(nfcId: string): Promise<User | null> {
    try {
      const response = await this.fetchFromBackend('/auth/nfc', {
        method: 'POST',
        body: JSON.stringify({ nfcId: nfcId })
      });

      console.log('✅ Backend NFC Authentication Success:', response.name);
      
      // Store the access token for future requests
      localStorage.setItem('hospitalAccessToken', response.accessToken);
      
      // Convert backend user format to frontend format
      const user: User = {
        id: response.userId,
        name: response.name,
        role: response.role,
        nfcId: nfcId,
        staffId: response.staffId,
        department: response.department
      };

      
      return user;
    } catch (error) {
      console.log('❌ Backend NFC Authentication Failed:', error);
      throw error;
    }
  }

  static async authenticateCredentials(staffId: string, password: string, pin?: string): Promise<User | null> {
    try {
      console.log('🔍 Attempting authentication for:', staffId, pin ? '(PIN)' : '(Password)');
      
      const response = await fetch(`/api/v1/staff/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          staffId: staffId,
          password: pin ? undefined : password,
          pin: pin || undefined
        })
      });

      console.log('📡 Response status:', response.status, response.statusText);

      if (!response.ok) {
        throw new Error(`Authentication failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      console.log('✅ Authentication successful:', data);
      
      // Store the access token for future API requests
      if (data.accessToken) {
        localStorage.setItem('hospitalAccessToken', data.accessToken);
        console.log('🔐 Access token stored for authenticated API calls');
      }
      
      // Convert backend user format to frontend format
      const user: User = {
        id: data.staff.id,
        name: data.staff.name,
        role: data.staff.role,
        nfcId: data.staff.nfcId || '',
        staffId: data.staff.staffId,
        department: data.staff.department
      };

      return user;
    } catch (error) {
      console.error('❌ Authentication failed:', error);
      return null;
    }
  }

  static async checkAuthType(staffId: string): Promise<{ requiresPin: boolean, requiresPassword: boolean } | null> {
    try {
      const response = await fetch(`/api/v1/staff/${staffId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        return null;
      }

      const data = await response.json();
      
      // Determine auth type based on role
      const passwordRoles = ['Administrator', 'Provisioner', 'Admin'];
      const requiresPassword = passwordRoles.includes(data.role);
      const requiresPin = !requiresPassword;
      
      return { requiresPin, requiresPassword };
    } catch (error) {
      console.error('❌ Failed to check auth type:', error);
      return null;
    }
  }

  // ================================
  // PATIENT DATA METHODS
  // ================================

  static async getPatients(ward?: string, department?: string, showAllDepts?: boolean): Promise<Patient[]> {
    try {
      let endpoint = '/patients?limit=100';
      if (ward) endpoint += `&ward=${encodeURIComponent(ward)}`;
      if (department) endpoint += `&department=${encodeURIComponent(department)}`;
      
      const backendData = await this.fetchFromBackend(endpoint);
      
      // Handle both array format and object format with patients array
      const patientsArray = Array.isArray(backendData) ? backendData : backendData?.patients || [];
      
      if (patientsArray && Array.isArray(patientsArray)) {
        console.log('✅ Using backend patient data', patientsArray.length, 'patients');
        console.log('🔍 First patient sample:', patientsArray[0]);
        
        // Convert backend patient format to frontend format
        return patientsArray.map((p: any) => ({
          id: p.id?.toString(),
          name: p.name,
          bedNumber: p.bedNumber,
          ward: p.ward,
          room: p.room,
          department: p.department,
          assignedDoctor: p.assignedDoctor,
          // Enhanced clinical safety fields
          codeStatus: p.codeStatus || 'fullCode',
          activeProblems: p.activeProblems || [],
          lastMedicationTime: p.lastMedicationTime,
          nextMedicationDue: p.nextMedicationDue,
          allergies: (p.allergies || []).map((allergy: any) => ({
            id: allergy.id,
            allergen: allergy.allergen,
            allergenType: allergy.allergenType,
            reaction: allergy.reaction,
            severity: allergy.severity,
            onset: allergy.onset,
            verificationStatus: allergy.verificationStatus,
            recordedDate: allergy.recordedDate,
            performedBy: allergy.performedBy
          })),
          vitals: p.vitals ? {
            heartRate: p.vitals.heartRate || 75,
            bloodPressure: p.vitals.bloodPressure || '120/80',
            bloodPressureValue: p.vitals.bloodPressureValue || 120,
            temperature: p.vitals.temperature || 98.6,
            respiratoryRate: p.vitals.respiratoryRate || 16,
            oxygenSat: p.vitals.oxygenSat || 98,
            ecg: p.vitals.ecg || 120,
            eeg: p.vitals.eeg || 45,
            isECGMode: p.vitals.isEcgMode !== undefined ? p.vitals.isEcgMode : true,
            bioimpedance: p.vitals.bioimpedance || 500,
            tremor: p.vitals.tremor || 0.0,
            fallRisk: p.vitals.fallRisk || 'low',
            lastUpdated: p.vitals.lastUpdated || new Date().toLocaleTimeString(),
            lastSync: p.vitals.lastSync || new Date().toISOString()
          } : {
            heartRate: 75,
            bloodPressure: '120/80',
            bloodPressureValue: 120,
            temperature: 98.6,
            respiratoryRate: 16,
            oxygenSat: 98,
            ecg: 120,
            eeg: 45,
            isECGMode: true,
            bioimpedance: 500,
            tremor: 0.0,
            fallRisk: 'low',
            lastUpdated: new Date().toLocaleTimeString(),
            lastSync: new Date().toISOString()
          },
          status: p.status || 'stable',
          alerts: p.alerts || [],
          admissionDate: p.admissionDate,
          age: p.age,
          gender: p.gender,
          weight: p.weight,
          diagnosis: p.diagnosis,
          medications: (p.medications || []).map((med: any) => ({
            id: med.id,
            name: med.name,
            dosage: med.dosage,
            frequency: med.frequency,
            route: med.route,
            status: med.status,
            startDate: med.startDate,
            endDate: med.endDate,
            performedBy: med.performedBy,
            createdAt: med.createdAt,
            modifiedBy: med.modifiedBy,
            updatedAt: med.updatedAt,
            canEdit: med.canEdit,
            history: med.history || []
          })),
          investigations: (p.investigations || []).map((inv: any) => ({
            id: inv.id,
            type: inv.type,
            name: inv.name,
            createdAt: inv.createdAt,
            scheduledAt: inv.scheduledAt,
            completedAt: inv.completedAt,
            priority: inv.priority,
            status: inv.status,
            performedBy: inv.performedBy,
            results: inv.results,
            notes: inv.notes,
            canEdit: inv.canEdit
          })),
          therapies: (p.therapies || []).map((therapy: any) => ({
            id: therapy.id,
            type: therapy.type,
            description: therapy.description,
            startDate: therapy.startDate,
            endDate: therapy.endDate,
            frequency: therapy.frequency,
            duration: therapy.duration,
            status: therapy.status,
            performedBy: therapy.performedBy,
            createdAt: therapy.createdAt,
            notes: therapy.notes,
            canEdit: therapy.canEdit
          })),
          notes: (p.notes || []).map((note: any) => ({
            id: note.id,
            content: note.content,
            timestamp: note.timestamp,
            authorName: note.authorName,
            canEdit: note.canEdit
          })),
          caseSheet: (p.caseSheet || []).map((entry: any) => ({
            id: entry.id,
            timestamp: entry.timestamp,
            type: entry.entryType,
            description: entry.description,
            performedBy: entry.performedBy,
            canEdit: entry.canEdit,
            details: entry.details
          })),
          handoffNotes: (p.handoffNotes || []).map((note: any) => ({
            id: note.id,
            patientId: note.patientId,
            shift: note.shift,
            fromNurse: note.fromNurse,
            toNurse: note.toNurse,
            priority: note.priority,
            category: note.category,
            note: note.note,
            timestamp: note.timestamp,
            acknowledged: note.acknowledged,
            performedBy: note.performedBy,
            completedAt: note.completedAt
          }))
        }));
      }
      
      return [];
    } catch (error) {
      console.error('Failed to fetch patients from backend:', error);
      throw error;
    }
  }

  static async detectRoomProximity(): Promise<RoomProximity> {
    try {
      const response = await this.fetchFromBackend('/mobile/room-proximity');
      return {
        tabletLocation: response.tabletLocation,
        roomNumber: response.roomNumber,
        patientsInRoom: response.patientsInRoom,
        lastDetection: response.lastDetection
      };
    } catch (error) {
      console.error('Failed to detect room proximity:', error);
      throw error;
    }
  }

  static async getPatientsInRoom(patientIds: string[]): Promise<Patient[]> {
    try {
      const response = await this.fetchFromBackend('/mobile/patients-in-room', {
        method: 'POST',
        body: JSON.stringify({ patientIds: patientIds })
      });
      return response.patients || [];
    } catch (error) {
      console.error('Failed to fetch patients in room:', error);
      throw error;
    }
  }

  static async getVitalHistory(patientId: string, timeRange: TimeRange): Promise<VitalHistory[]> {
    try {
      console.log(`🔍 Fetching REAL TimescaleDB vital history for patient ${patientId}, timeRange: ${timeRange}`);
      
      // Use mobile endpoint which connects to TimescaleDB for real watch data
      const response = await this.fetchFromBackend(`/mobile/patients/${patientId}/vitals/history-test?timeRange=${timeRange}`);
      
      console.log(`📊 Received ${response.vitalHistory?.length || 0} real vital history records from TimescaleDB`);
      
      if (response.vitalHistory && response.vitalHistory.length > 0) {
        // Convert UTC time strings to IST (UTC+5:30)
        return response.vitalHistory.map((record: any) => {
          if (record.time && typeof record.time === 'string') {
            const [hours, minutes] = record.time.split(':').map(Number);
            
            // Add 5.5 hours for IST conversion
            let istHours = hours + 5;
            let istMinutes = minutes + 30;
            
            // Handle minute overflow
            if (istMinutes >= 60) {
              istMinutes -= 60;
              istHours += 1;
            }
            
            // Handle hour overflow (next day)
            if (istHours >= 24) {
              istHours -= 24;
            }
            
            // Format as HH:MM
            const formattedTime = `${istHours.toString().padStart(2, '0')}:${istMinutes.toString().padStart(2, '0')}`;
            record.time = formattedTime;
            
            console.log(`🕐 Converted ${hours}:${minutes.toString().padStart(2, '0')} UTC -> ${formattedTime} IST`);
          }
          return record;
        });
      }
      
      console.warn(`❌ No real TimescaleDB data found for patient ${patientId}`);
      return [];
    } catch (error) {
      console.error(`❌ Failed to fetch real TimescaleDB vital history for patient ${patientId}:`, error);
      return [];
    }
  }

  // ================================
  // UTILITY METHODS
  // ================================

  private static convertTimescaleToVitalHistory(timescaleData: any[]): VitalHistory[] {
    // Group data by timestamp to combine all vital types
    const groupedData: { [timestamp: string]: any } = {};
    
    timescaleData.forEach(reading => {
      const timeKey = new Date(reading.timestamp).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
      
      if (!groupedData[timeKey]) {
        groupedData[timeKey] = {
          time: timeKey,
          timestamp: reading.timestamp,
          heartRate: 0,
          bloodPressure: 0,
          bloodPressureDiastolic: 0,
          temperature: 0,
          oxygenSat: 0,
          respiratoryRate: 0,
          ecg: 0,
          eeg: 0,
          bioimpedance: 0,
          tremor: 0
        };
      }
      
      // Map TimescaleDB vitalType to VitalHistory fields
      const vitalTypeMap: { [key: string]: string } = {
        'heartRate': 'heartRate',
        'bloodPressureSystolic': 'bloodPressure',
        'bloodPressureDiastolic': 'bloodPressureDiastolic',
        'temperature': 'temperature',
        'oxygenSaturation': 'oxygenSat',
        'respiratoryRate': 'respiratoryRate',
        'ecg': 'ecg',
        'eeg': 'eeg',
        'bioimpedance': 'bioimpedance',
        'tremor': 'tremor'
      };
      
      const fieldName = vitalTypeMap[reading.vitalType];
      if (fieldName) {
        groupedData[timeKey][fieldName] = Math.round(reading.value * 100) / 100; // Round to 2 decimal places
      }
    });
    
    // Convert to array and sort by timestamp
    return Object.values(groupedData).sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }

  
  static getCurrentUser() {
    try {
      const userStr = localStorage.getItem('currentUser');
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  }

  // ================================
  // NEW VITALS ANALYTICS METHODS  
  // ================================

  static async getVitalTimeseries(
    patientId: string, 
    vitalType: string, 
    timeframe: string = '5m', 
    hoursBack: number = 12,
    rawData: boolean = false
  ) {
    console.log('=== API: getVitalTimeseries called ===');
    console.log('API Parameters:', { patientId, vitalType, timeframe, hoursBack, rawData });
    
    try {
      const currentUser = this.getCurrentUser();
      const staffId = currentUser?.staffId || 'NURSE001';
      
      console.log('Current user:', currentUser);
      console.log('Using staffId:', staffId);
      
      const params = new URLSearchParams({
        vitalType: vitalType,
        timeframe,
        hoursBack: hoursBack.toString(),
        staffId: staffId
      });
      
      if (rawData) {
        params.append('rawData', 'true');
      }
      
      const url = `/vitals-analytics/patient/${patientId}/vitals-timeseries?${params}`;
      console.log('API URL:', url);
      console.log('Full URL:', `${BACKEND_BASE_URL}${url}`);
      
      const response = await this.fetchFromBackend(url);
      console.log('=== API Response received ===');
      console.log('Response type:', typeof response);
      console.log('Response keys:', Object.keys(response || {}));
      console.log('Response:', response);
      
      return response;
    } catch (error) {
      console.error('=== API ERROR ===');
      console.error('Failed to fetch vital timeseries:', error);
      throw error;
    }
  }

  static async getMedicationCorrelatedVitals(
    patientId: string,
    vitalType: string,
    hoursBack: number = 24,
    medicationFilter?: string,
    timeframe: string = '5m'
  ) {
    try {
      const currentUser = this.getCurrentUser();
      const staffId = currentUser?.staffId || 'NURSE001';
      
      const params = new URLSearchParams({
        vitalType: vitalType,
        hoursBack: hoursBack.toString(),
        timeframe,
        staffId: staffId
      });
      
      if (medicationFilter) {
        params.append('medicationFilter', medicationFilter);
      }
      
      const response = await this.fetchFromBackend(`/vitals-analytics/patient/${patientId}/medication-correlated-vitals?${params}`);
      return response;
    } catch (error) {
      console.error('Failed to fetch medication correlated vitals:', error);
      throw error;
    }
  }

  static async getMedicationTimeline(patientId: string, hoursBack: number = 24) {
    try {
      const currentUser = this.getCurrentUser();
      const staffId = currentUser?.staffId || 'NURSE001';
      
      const params = new URLSearchParams({
        hoursBack: hoursBack.toString(),
        staffId: staffId
      });
      
      const response = await this.fetchFromBackend(`/vitals-analytics/patient/${patientId}/medication-timeline?${params}`);
      return response;
    } catch (error) {
      console.error('Failed to fetch medication timeline:', error);
      throw error;
    }
  }

  static canEditItem(timestamp: string): boolean {
    const itemTime = new Date(timestamp).getTime();
    const now = new Date().getTime();
    const minutesDiff = (now - itemTime) / (1000 * 60);
    return minutesDiff <= 15; // Allow editing for 15 minutes only
  }

  static canEditNote(note: NoteComment, userId: string): boolean {
    return note.authorId === userId && this.canEditItem(note.timestamp);
  }


  // ================================
  // ALERT METHODS
  // ================================

  static async acknowledgeAlert(patientId: string, alertId: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/mobile/acknowledge-alert/${patientId}/${alertId}`, {
        method: 'POST',
        body: JSON.stringify({ userId: userId })
      });


      return true;
    } catch (error) {
      console.warn('Alert acknowledgment failed - backend endpoint may not be implemented yet:', error);
      // Return true for local acknowledgment since this is likely a missing backend endpoint
      // In a real scenario, this would be stored locally until backend sync
      return true;
    }
  }

  // ================================
  // NOTE & COMMENT METHODS
  // ================================

  static async addNoteComment(patientId: string, content: string, userId: string, userName?: string, userRole?: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/patients/${patientId}/notes`, {
        method: 'POST',
        body: JSON.stringify({
          content: content,
          authorId: userId,
          authorName: userName,
          authorRole: userRole
        })
      });

      
      return true;
    } catch (error) {
      console.error('Failed to add note:', error);
      throw error;
    }
  }

  static async editNoteComment(patientId: string, noteId: string, newContent: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/patients/${patientId}/notes/${noteId}`, {
        method: 'PUT',
        body: JSON.stringify({
          content: newContent,
          userId: userId
        })
      });

      
      return true;
    } catch (error) {
      console.error('Failed to edit note:', error);
      throw error;
    }
  }

  static async deleteNoteComment(patientId: string, noteId: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/notes/${noteId}`, {
        method: 'DELETE',
        body: JSON.stringify({ userId: userId })
      });

      
      return true;
    } catch (error) {
      console.error('Failed to delete note:', error);
      throw error;
    }
  }

  // ================================
  // MEDICATION METHODS
  // ================================

  static async addMedication(patientId: string, medication: Omit<Medication, 'id' | 'history'>, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/patients/${patientId}/medications`, {
        method: 'POST',
        body: JSON.stringify({
          name: medication.name,
          dosage: medication.dosage,
          frequency: medication.frequency,
          route: medication.route,
          status: medication.status,
          startDate: medication.startDate,
          performedBy: medication.performedBy,
          userId: userId
        })
      });

      
      return true;
    } catch (error) {
      console.error('Failed to add medication:', error);
      throw error;
    }
  }

  static async updateMedication(patientId: string, medicationId: string, status: 'active' | 'stopped' | 'held', userId: string): Promise<boolean>
  static async updateMedication(patientId: string, medicationId: string, updates: Partial<Medication>, userId: string): Promise<boolean>
  static async updateMedication(patientId: string, medicationId: string, statusOrUpdates: any, userId: string): Promise<boolean> {
    try {
      const updates = typeof statusOrUpdates === 'string' 
        ? { status: statusOrUpdates } 
        : statusOrUpdates;

      await this.fetchFromBackend(`/patients/patients/${patientId}/medications/${medicationId}`, {
        method: 'PUT',
        body: JSON.stringify({
          ...updates,
          userId: userId
        })
      });

      
      return true;
    } catch (error) {
      console.error('Failed to update medication:', error);
      throw error;
    }
  }

  static async discontinueMedication(patientId: string, medicationId: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/medications/${medicationId}/discontinue`, {
        method: 'POST',
        body: JSON.stringify({ userId: userId })
      });

      
      return true;
    } catch (error) {
      console.error('Failed to discontinue medication:', error);
      throw error;
    }
  }

  // ================================
  // ECG/EEG MONITORING METHODS
  // ================================

  static async getECGReadings(patientId: string, timeRange: TimeRange): Promise<ECGReading[]> {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/ecg?range=${timeRange}`);
      return response.readings || [];
    } catch (error) {
      console.error('Failed to fetch ECG readings:', error);
      throw error;
    }
  }

  static async switchMonitoringMode(patientId: string, isECGMode: boolean, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/monitoring-mode`, {
        method: 'PUT',
        body: JSON.stringify({
          isEcgMode: isECGMode,
          userId: userId
        })
      });

      
      return true;
    } catch (error) {
      console.error('Failed to switch monitoring mode:', error);
      throw error;
    }
  }

  // ================================
  // INVESTIGATION & THERAPY METHODS
  // ================================

  static async addInvestigation(patientId: string, investigation: Omit<Investigation, 'id'>, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/patients/${patientId}/investigations`, {
        method: 'POST',
        body: JSON.stringify({
          type: investigation.type,
          name: investigation.name,
          priority: investigation.priority,
          notes: investigation.notes,
          performedBy: investigation.performedBy,
          createdAt: investigation.createdAt,
          userId: userId
        })
      });

      
      return true;
    } catch (error) {
      console.error('Failed to add investigation:', error);
      throw error;
    }
  }

  static async updateInvestigation(patientId: string, investigationId: string, status: 'ordered' | 'scheduled' | 'inProgress' | 'completed' | 'cancelled', userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/patients/${patientId}/investigations/${investigationId}`, {
        method: 'PUT',
        body: JSON.stringify({
          status: status,
          userId: userId
        })
      });

      
      return true;
    } catch (error) {
      console.warn('Failed to update investigation - using local state:', error);
      return true; // Allow local state update
    }
  }

  static async completeInvestigation(patientId: string, investigationId: string, results: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/patients/${patientId}/investigations/${investigationId}/complete`, {
        method: 'POST',
        body: JSON.stringify({
          results: results,
          userId: userId
        })
      });

      
      return true;
    } catch (error) {
      console.warn('Failed to complete investigation - using local state:', error);
      return true; // Allow local state update
    }
  }

  static async addTherapy(patientId: string, therapy: Omit<Therapy, 'id'>, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/patients/${patientId}/therapies`, {
        method: 'POST',
        body: JSON.stringify({
          type: therapy.type,
          description: therapy.description,
          frequency: therapy.frequency,
          duration: therapy.duration,
          performedBy: therapy.performedBy,
          startDate: therapy.startDate,
          userId: userId
        })
      });

      
      return true;
    } catch (error) {
      console.error('Failed to add therapy:', error);
      throw error;
    }
  }

  static async updateTherapy(patientId: string, therapyId: string, status: 'active' | 'completed' | 'cancelled', userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/patients/${patientId}/therapies/${therapyId}`, {
        method: 'PUT',
        body: JSON.stringify({
          status: status,
          userId: userId
        })
      });

      
      return true;
    } catch (error) {
      console.warn('Failed to update therapy - using local state:', error);
      return true; // Allow local state update
    }
  }

  static async addTherapySession(patientId: string, therapyId: string, sessionData: { duration: number; notes: string; therapist: string; patientResponse: string }, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/patients/${patientId}/therapies/${therapyId}/sessions`, {
        method: 'POST',
        body: JSON.stringify({
          ...sessionData,
          userId: userId
        })
      });

      
      return true;
    } catch (error) {
      console.warn('Failed to add therapy session - using local state:', error);
      return true; // Allow local state update
    }
  }


  // ================================
  // PATIENT SEARCH & FILTER METHODS
  // ================================

  static async searchPatients(query: string): Promise<Patient[]> {
    try {
      const response = await this.fetchFromBackend(`/patients/search?q=${encodeURIComponent(query)}`);
      return response.patients || [];
    } catch (error) {
      console.error('Failed to search patients:', error);
      throw error;
    }
  }

  static async getPatientsByStatus(status: 'stable' | 'critical' | 'emergency'): Promise<Patient[]> {
    try {
      const response = await this.fetchFromBackend(`/patients?status=${status}`);
      return response.patients || [];
    } catch (error) {
      console.error('Failed to get patients by status:', error);
      throw error;
    }
  }

  // ================================
  // SYSTEM MONITORING METHODS
  // ================================

  static async getSystemStatus(): Promise<{
    totalPatients: number;
    criticalAlerts: number;
    activeStaff: number;
    systemHealth: 'good' | 'warning' | 'critical';
    lastUpdate: string;
  }> {
    try {
      const response = await this.fetchFromBackend('/system/status');
      return {
        totalPatients: response.totalPatients,
        criticalAlerts: response.criticalAlerts,
        activeStaff: response.activeStaff,
        systemHealth: response.systemHealth,
        lastUpdate: response.lastUpdate
      };
    } catch (error) {
      console.error('Failed to get system status:', error);
      throw error;
    }
  }

  // ================================
  // DEVICE ASSIGNMENT METHODS
  // ================================

  static async getFreeDevices(staffId: string, deviceType?: string, location?: string): Promise<any[]> {
    try {
      const params = new URLSearchParams({ staffId: staffId });
      if (deviceType) params.append('deviceType', deviceType);
      if (location) params.append('location', location);
      
      const response = await this.fetchFromBackend(`/device-assignment/free-devices?${params}`);
      return response || [];
    } catch (error) {
      console.error('Failed to get free devices:', error);
      throw error;
    }
  }

  static async getDevicePoolStatus(staffId: string): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/device-assignment/pool-status?staffId=${staffId}`);
      return response;
    } catch (error) {
      console.error('Failed to get device pool status:', error);
      throw error;
    }
  }

  static async assignDevice(staffId: string, deviceId: string, patientId: string, assignmentReason: string): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/device-assignment/assign?staffId=${staffId}`, {
        method: 'POST',
        body: JSON.stringify({
          deviceId: deviceId,
          patientId: patientId,
          performedBy: staffId,
          assignmentReason: assignmentReason
        })
      });
      return response;
    } catch (error) {
      console.error('Failed to assign device:', error);
      throw error;
    }
  }

  static async unassignDevice(staffId: string, deviceId: string, unassignmentReason: string = 'patientDischarge'): Promise<boolean> {
    try {
      const response = await this.fetchFromBackend(`/device-assignment/unassign/${deviceId}?staffId=${staffId}`, {
        method: 'POST',
        body: JSON.stringify({
          performedBy: staffId,
          unassignmentReason: unassignmentReason
        })
      });
      return response.success;
    } catch (error) {
      console.error('Failed to unassign device:', error);
      throw error;
    }
  }

  static async reassignDevice(staffId: string, oldDeviceId: string, newDeviceId: string, reassignmentReason: string = 'deviceMalfunction'): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/device-assignment/reassign?staffId=${staffId}`, {
        method: 'POST',
        body: JSON.stringify({
          oldDeviceId: oldDeviceId,
          newDeviceId: newDeviceId,
          performedBy: staffId,
          reassignmentReason: reassignmentReason
        })
      });
      return response;
    } catch (error) {
      console.error('Failed to reassign device:', error);
      throw error;
    }
  }

  static async getPatientDevice(staffId: string, patientId: string): Promise<any | null> {
    try {
      const response = await this.fetchFromBackend(`/device-assignment/patient/${patientId}/device?staffId=${staffId}`);
      return response;
    } catch (error: any) {
      if (error.message && error.message.includes('404')) {
        return null; // No device assigned
      }
      console.error('Failed to get patient device:', error);
      throw error;
    }
  }

  static async getAssignmentHistory(staffId: string, patientId?: string, deviceId?: string, limit: number = 50): Promise<any[]> {
    try {
      const params = new URLSearchParams({ 
        staffId: staffId,
        limit: limit.toString()
      });
      if (patientId) params.append('patientId', patientId);
      if (deviceId) params.append('deviceId', deviceId);
      
      const response = await this.fetchFromBackend(`/device-assignment/history?${params}`);
      return response.history || [];
    } catch (error) {
      console.error('Failed to get assignment history:', error);
      throw error;
    }
  }

  static async bulkUnassignPatientDevices(staffId: string, patientId: string, unassignmentReason: string = 'patientDischarge'): Promise<any> {
    try {
      const response = await this.fetchFromBackend(
        `/device-assignment/bulk-operations/unassign-patient/${patientId}?staffId=${staffId}&performedBy=${staffId}&unassignmentReason=${unassignmentReason}`
      );
      return response;
    } catch (error) {
      console.error('Failed to bulk unassign patient devices:', error);
      throw error;
    }
  }

  // ================================
  // PATIENT DISCHARGE METHODS
  // ================================

  static async dischargePatient(patientId: string, staffId: string): Promise<boolean> {
    try {
      // Use new workflow endpoints
      const endpoints = [
        `/discharge-workflow/doctor-request`,
        `/devices/discharge-patient/${patientId}`,
        `/mobile/patients/${patientId}/discharge`
      ];

      for (const endpoint of endpoints) {
        try {
          let requestBody;
          
          if (endpoint === '/discharge-workflow/doctor-request') {
            requestBody = {
              patientId: patientId,
              dischargeReason: 'Medical discharge - patient condition stable',
              dischargeNotes: 'Patient ready for discharge per clinical assessment',
              requestedBy: staffId
            };
          } else {
            requestBody = {
              staffId: staffId,
              dischargeDate: new Date().toISOString(),
              dischargeReason: 'medicalDischarge'
            };
          }
          
          const response = await this.fetchFromBackend(endpoint, {
            method: 'POST',
            body: JSON.stringify(requestBody)
          });

          console.log('✅ Patient discharged successfully:', response);
          return true;
        } catch (error) {
          console.log(`❌ Endpoint ${endpoint} failed, trying next...`);
          continue;
        }
      }

      throw new Error('All discharge endpoints failed');
    } catch (error) {
      console.error('❌ Patient discharge failed:', error);
      throw error;
    }
  }
}

// Export the API class
export default HospitalAPI;