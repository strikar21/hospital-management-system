// api.ts - Backend Integration API
import { User, Patient, VitalHistory, RoomProximity, TimeRange, Medication, Investigation, Therapy, ECGReading, NoteComment } from './types';
import SecureStorage from './utils/secureStorage';

// Backend configuration
import { API_CONFIG, getApiUrl, getWsUrl } from './config/apiConfig';

const BACKEND_BASE_URL = API_CONFIG.BACKEND_BASE_URL;
console.log('🔧 API Base URL:', BACKEND_BASE_URL);
const BACKEND_WS_URL = API_CONFIG.WS_BASE_URL;

class HospitalAPI {
  
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
    
    // Use environment variable for secret key - fallback for development only
    const secretKey = process.env.REACT_APP_HOSPITAL_SECRET_KEY || 
      (process.env.NODE_ENV === 'development' ? 'dev-key-only-not-for-production' : '');
    
    if (!secretKey && process.env.NODE_ENV === 'production') {
      console.error('🚨 CRITICAL: No secret key configured for production. Set REACT_APP_HOSPITAL_SECRET_KEY');
      throw new Error('Authentication secret key not configured');
    }
    
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
    const url = getApiUrl(endpoint);
    const token = SecureStorage.getToken();
    
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
      return new WebSocket(getWsUrl(endpoint));
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
      SecureStorage.setToken(response.accessToken);
      
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
      
      // Production authentication - backend only

      // Try backend authentication
      const response = await fetch(getApiUrl('/auth/simple-login'), {
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
        SecureStorage.setToken(data.accessToken);
        console.log('🔐 Access token stored for authenticated API calls');
      }
      
      // Convert backend user format to frontend format
      const user: User = {
        id: data.id,
        name: data.name,
        role: data.role,
        nfcId: data.nfcCardId || '',
        staffId: data.id, // Backend uses id as staffId
        department: data.department || ''
      };

      return user;
    } catch (error) {
      console.error('❌ Authentication failed:', error);
      return null;
    }
  }

  static async checkAuthType(staffId: string): Promise<{ requiresPin: boolean, requiresPassword: boolean } | null> {
    try {
      // Production authentication type checking - backend only

      const response = await fetch(getApiUrl(`/staff/${staffId}`), {
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

  /**
   * Logout user and clear all secure storage
   */
  static logout(): void {
    SecureStorage.clearAll();
    console.log('🔐 User logged out, secure storage cleared');
  }

  // ================================
  // PATIENT DATA METHODS
  // ================================

  static async getPatient(patientId: string): Promise<Patient | null> {
    try {
      console.log(`🔍 Fetching complete patient data for: ${patientId}`);
      const backendData = await this.fetchFromBackend(`/patients/${patientId}`);
      
      if (backendData && backendData.id) {
        console.log('✅ Got complete patient data:', backendData);
        
        // Convert backend patient format to frontend format (same as in getPatients)
        const p = backendData;
        const patientObj = {
          id: p.id?.toString(),
          name: (() => {
            const names = [p.firstName, p.lastName].filter(Boolean);
            const fullName = names.join(' ');
            // Only filter if the entire name is just placeholder words
            if (['Patient', 'patient', 'Client', 'client', 'User', 'user', 'Test', 'test'].includes(fullName.trim())) {
              return p.firstName || p.lastName || 'Unknown Patient';
            }
            return fullName || 'Unknown Patient';
          })(), // Handle missing/empty names and filter only complete placeholder names
          bedNumber: p.bedNumber,
          ward: p.department || 'General Ward',
          room: p.roomNumber,
          department: p.department || 'General',
          assignedDoctor: p.attendingphysicianname || p.attendingPhysician,
          codeStatus: p.codeStatus || 'fullCode',
          activeProblems: p.activeProblems || [],
          lastMedicationTime: p.lastMedicationTime,
          nextMedicationDue: p.nextMedicationDue,
          allergies: (() => {
            if (!p.allergies) return [];
            
            if (typeof p.allergies === 'string') {
              if (!p.allergies.trim()) return [];
              
              const allergyStrings = p.allergies.split(',').map((s: string) => s.trim()).filter((s: string) => s);
              return allergyStrings.map((allergen: string, index: number) => ({
                id: `allergy_${index}`,
                allergen: allergen,
                allergenType: 'unknown',
                reaction: 'unknown',
                severity: 'unknown',
                onset: null,
                verificationStatus: 'unverified',
                recordedDate: null,
                performedBy: null
              }));
            }
            
            if (Array.isArray(p.allergies)) {
              return p.allergies.map((allergy: any) => ({
                id: allergy.id,
                allergen: allergy.allergen,
                allergenType: allergy.allergenType,
                reaction: allergy.reaction,
                severity: allergy.severity,
                onset: allergy.onset,
                verificationStatus: allergy.verificationstatus, // Fixed: use backend field
                recordedDate: allergy.recordeddate, // Fixed: use backend field
                performedBy: allergy.performedbyname || allergy.performedby, // Fixed: use backend field
              }));
            }
            
            return [];
          })(),
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
          age: p.dateOfBirth ? new Date().getFullYear() - new Date(p.dateOfBirth).getFullYear() : 0,
          gender: p.gender || 'Unknown',
          weight: p.weight || 70,
          diagnosis: p.medicalHistory || p.diagnosis || 'Under evaluation',
          medications: (p.medications || []).map((med: any) => ({
            id: med.id,
            name: med.name,
            dosage: med.dosage,
            frequency: med.frequency,
            route: med.route,
            status: med.status,
            startdate: med.startdate,
            enddate: med.enddate,
            duration: med.duration,
            prescribedby: med.prescribedbyname || med.prescribedby,
            createdat: med.createdat,
            modifiedBy: med.modifiedby || null,
            updatedat: med.updatedat,
            canEdit: true,
            history: []
          })),
          investigations: (p.investigations || []).map((inv: any) => ({
            id: inv.id,
            type: inv.type,
            name: inv.name,
            createdat: inv.createdat,
            scheduledat: inv.scheduledat,
            completedat: inv.completedat,
            priority: inv.priority,
            status: inv.status,
            performedby: inv.performedbyname || inv.performedby,
            results: inv.results,
            notes: inv.notes,
            canEdit: true
          })),
          therapies: (p.therapies || []).map((therapy: any) => ({
            id: therapy.id,
            type: therapy.type,
            description: therapy.description,
            startdate: therapy.startdate,        // Fixed: use backend field
            enddate: therapy.enddate,            // Fixed: use backend field
            frequency: therapy.frequency,
            duration: therapy.duration,
            status: therapy.status,
            performedby: therapy.performedbyname || therapy.performedby, // Fixed: use backend field
            createdat: therapy.createdat,        // Fixed: use backend field
            notes: therapy.notes,
            sessions: [],
            canEdit: true
          })),
          notes: (p.notes || []).map((note: any) => ({
            id: note.id,
            content: note.content,
            authorId: note.authorid,             // Fixed: use backend field
            authorName: note.authorname,         // Fixed: use backend field
            authorRole: note.authorrole,         // Fixed: use backend field
            timestamp: note.timestamp,
            editedAt: note.editedat,             // Fixed: use backend field
            isEdited: note.isedited || false,   // Fixed: use backend field
            canEdit: this.canEditItem(note.timestamp)
          })),
          caseSheet: [],
          handoffNotes: (p.handoffNotes || []).map((note: any) => ({
            id: note.id,
            patientId: note.patientid,           // Fixed: use backend field
            shift: note.shift,
            fromNurse: note.fromnurse,           // Fixed: use backend field
            toNurse: note.tonurse,               // Fixed: use backend field
            priority: note.priority,
            category: note.category,
            note: note.note,
            timestamp: note.timestamp,
            acknowledged: note.acknowledged,
            performedBy: note.performedby,       // Fixed: use backend field
            completedAt: note.completedat        // Fixed: use backend field
          }))
        };
        
        // Add device assignment fields
        (patientObj as any).assignedDeviceId = p.assignedDeviceId;
        (patientObj as any).deviceStatus = p.deviceStatus;
        (patientObj as any).deviceBattery = p.deviceBattery;
        
        // Load case sheet entries separately
        try {
          const caseSheetEntries = await this.getCaseEntries(patientId);
          (patientObj as any).caseSheet = caseSheetEntries;
        } catch (error) {
          console.error('Failed to load case sheets:', error);
          (patientObj as any).caseSheet = [];
        }
        
        return patientObj;
      }
      
      return null;
    } catch (error) {
      console.error(`❌ Failed to fetch patient ${patientId}:`, error);
      return null;
    }
  }

  static async updatePatientVitals(patientId: string, vitals: any): Promise<boolean> {
    try {
      console.log(`🔄 Updating vitals for patient: ${patientId}`);
      await this.fetchFromBackend(`/patients/${patientId}/vitals`, {
        method: 'PUT',
        body: JSON.stringify(vitals)
      });
      
      console.log('✅ Patient vitals updated successfully');
      return true;
    } catch (error) {
      console.warn('Failed to update patient vitals - ignoring error:', error);
      return false; // Don't throw, just log and continue
    }
  }

  static async getPatients(ward?: string, department?: string, showAllDepts?: boolean): Promise<Patient[]> {
    try {
      let endpoint = '/patients?limit=100';
      if (ward) endpoint += `&ward=${encodeURIComponent(ward)}`;
      if (department) endpoint += `&department=${encodeURIComponent(department)}`;

      const backendData = await this.fetchFromBackend(endpoint);
      
      // Handle both array format and object format with patients array
      const patientsArray = Array.isArray(backendData) ? backendData : backendData?.patients || [];
      
      if (patientsArray && Array.isArray(patientsArray)) {
        // Filter out only fully discharged patients, keep active and pending_discharge
        const activePatients = patientsArray.filter((p: any) => p.status !== 'discharged');

        // Convert backend patient format to frontend format
        return activePatients.map((p: any) => ({
          id: p.id?.toString(),
          name: (() => {
            const names = [p.firstName, p.lastName].filter(Boolean);
            const fullName = names.join(' ');
            // Only filter if the entire name is just placeholder words
            if (['Patient', 'patient', 'Client', 'client', 'User', 'user', 'Test', 'test'].includes(fullName.trim())) {
              return p.firstName || p.lastName || 'Unknown Patient';
            }
            return fullName || 'Unknown Patient';
          })(), // Handle missing/empty names and filter only complete placeholder names
          bedNumber: p.bedNumber,
          ward: p.department || 'General Ward',
          room: p.roomNumber,
          department: p.department || 'General',
          assignedDoctor: p.attendingphysicianname || p.attendingPhysician,
          // Enhanced clinical safety fields
          codeStatus: p.codeStatus || 'fullCode',
          activeProblems: p.activeProblems || [],
          lastMedicationTime: p.lastMedicationTime,
          nextMedicationDue: p.nextMedicationDue,
          allergies: (() => {
            if (!p.allergies) return [];
            
            // Handle case where allergies might be a string
            if (typeof p.allergies === 'string') {
              if (!p.allergies.trim()) return [];
              
              // Parse common string formats
              const allergyStrings = p.allergies.split(',').map((s: string) => s.trim()).filter((s: string) => s);
              return allergyStrings.map((allergen: string, index: number) => ({
                id: `allergy_${index}`,
                allergen: allergen,
                allergenType: 'unknown',
                reaction: 'unknown',
                severity: 'unknown',
                onset: null,
                verificationStatus: 'unverified',
                recordedDate: null,
                performedBy: null
              }));
            }
            
            // Handle array format
            if (Array.isArray(p.allergies)) {
              return p.allergies.map((allergy: any) => ({
                id: allergy.id,
                allergen: allergy.allergen,
                allergenType: allergy.allergenType,
                reaction: allergy.reaction,
                severity: allergy.severity,
                onset: allergy.onset,
                verificationStatus: allergy.verificationstatus, // Fixed: use backend field
                recordedDate: allergy.recordeddate, // Fixed: use backend field
                performedBy: allergy.performedbyname || allergy.performedby, // Fixed: use backend field
              }));
            }
            
            return [];
          })(),
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
          age: p.dateOfBirth ? new Date().getFullYear() - new Date(p.dateOfBirth).getFullYear() : 0,
          gender: p.gender || 'Unknown',
          weight: p.weight || 70,
          diagnosis: p.medicalHistory || p.diagnosis || 'Under evaluation',
          medications: (p.medications || []).map((med: any) => ({
            id: med.id,
            name: med.name,
            dosage: med.dosage,
            frequency: med.frequency,
            route: med.route,
            status: med.status,
            startDate: med.startdate,        // Fixed: use backend field
            endDate: med.enddate,            // Fixed: use backend field
            duration: med.duration,
            prescribedby: med.prescribedbyname || med.prescribedby, // Fixed: use backend field
            createdAt: med.createdat,        // Fixed: use backend field
            modifiedBy: med.modifiedby || null, // Fixed: use backend field
            updatedAt: med.updatedat,        // Fixed: use backend field
            canEdit: true,
            history: []
          })),
          investigations: (p.investigations || []).map((inv: any) => ({
            id: inv.id,
            type: inv.type,
            name: inv.name,
            createdAt: inv.createdat,        // Fixed: backend uses lowercase
            scheduledAt: inv.scheduledat,    // Fixed: backend uses lowercase
            completedAt: inv.completedat,    // Fixed: backend uses lowercase
            priority: inv.priority,
            status: inv.status,
            performedBy: inv.performedbyname || inv.performedby, // Fixed: backend uses lowercase
            results: inv.results,
            notes: inv.notes,
            canEdit: true
          })),
          therapies: (p.therapies || []).map((therapy: any) => ({
            id: therapy.id,
            type: therapy.type,
            description: therapy.description,
            startdate: therapy.startdate,
            enddate: therapy.enddate,
            frequency: therapy.frequency,
            duration: therapy.duration,
            status: therapy.status,
            performedby: therapy.performedby,
            createdat: therapy.createdat,
            notes: therapy.notes,
            canEdit: true
          })),
          notes: (p.notes || []).map((note: any) => ({
            id: note.id,
            content: note.content,
            timestamp: note.timestamp,
            authorName: note.authorname,     // Fixed: use backend field
            canEdit: true
          })),
          caseSheet: [],
          handoffNotes: (p.handoffNotes || []).map((note: any) => ({
            id: note.id,
            patientId: note.patientid,           // Fixed: use backend field
            shift: note.shift,
            fromNurse: note.fromnurse,           // Fixed: use backend field
            toNurse: note.tonurse,               // Fixed: use backend field
            priority: note.priority,
            category: note.category,
            note: note.note,
            timestamp: note.timestamp,
            acknowledged: note.acknowledged,
            performedBy: note.performedby,       // Fixed: use backend field
            completedAt: note.completedat        // Fixed: use backend field
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
    try {
      if (!timestamp) {
        console.warn('🕒 Edit time check: No timestamp provided');
        return false;
      }

      const itemTime = new Date(timestamp).getTime();
      const now = new Date().getTime();
      
      // Handle invalid dates
      if (isNaN(itemTime)) {
        console.warn('🕒 Edit time check: Invalid timestamp format:', timestamp);
        return false;
      }
      
      const minutesDiff = (now - itemTime) / (1000 * 60);
      const canEdit = minutesDiff >= 0 && minutesDiff <= 15; // Must be positive (not future) and within 15 minutes
      
      console.log('🕒 Edit time check:', {
        timestamp,
        itemTime: new Date(timestamp).toISOString(),
        now: new Date(now).toISOString(),
        minutesDiff: Math.round(minutesDiff * 100) / 100,
        canEdit,
        isFuture: minutesDiff < 0,
        isValid: !isNaN(itemTime)
      });
      
      return canEdit;
    } catch (error) {
      console.error('🕒 Edit time check error:', error, 'timestamp:', timestamp);
      return false;
    }
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

  static async addNoteComment(patientId: string, content: string, userId: string, userName?: string, userRole?: string): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/notes?created_by=${encodeURIComponent(userId)}`, {
        method: 'POST',
        body: JSON.stringify({
          content: content,
          authorId: userId,
          authorName: userName,
          authorRole: userRole
        })
      });

      // Return the created note data from backend
      return response;
    } catch (error) {
      console.error('Failed to add note:', error);
      throw error;
    }
  }

  static async editNoteComment(patientId: string, noteId: string, newContent: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/notes/${noteId}`, {
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
      await this.fetchFromBackend(`/patients/${patientId}/medications?created_by=${encodeURIComponent(userId)}`, {
        method: 'POST',
        body: JSON.stringify({
          name: medication.name,
          dosage: medication.dosage,
          frequency: medication.frequency,
          route: medication.route,
          status: medication.status,
          startdate: medication.startdate,
          duration: medication.duration,
          prescribedby: medication.prescribedby
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

      await this.fetchFromBackend(`/patients/${patientId}/medications/${medicationId}`, {
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

  static async recordMedicationAdministration(patientId: string, medicationId: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/medications/${medicationId}`, {
        method: 'PUT',
        body: JSON.stringify({ 
          status: 'administered',
          updatedBy: userId
        })
      });

      return true;
    } catch (error) {
      console.error('Failed to record medication administration:', error);
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
      await this.fetchFromBackend(`/patients/${patientId}/investigations?created_by=${encodeURIComponent(userId)}`, {
        method: 'POST',
        body: JSON.stringify({
          type: investigation.type,
          name: investigation.name,
          priority: investigation.priority,
          notes: investigation.notes,
          performedby: investigation.performedby,
          createdat: investigation.createdat
        })
      });

      
      return true;
    } catch (error) {
      console.error('Failed to add investigation:', error);
      throw error;
    }
  }

  static async updateInvestigation(patientId: string, investigationId: string, status: 'ordered' | 'scheduled' | 'in_progress' | 'completed' | 'cancelled', userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/investigations/${investigationId}`, {
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
      await this.fetchFromBackend(`/patients/${patientId}/investigations/${investigationId}/complete`, {
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
      await this.fetchFromBackend(`/patients/${patientId}/therapies?created_by=${encodeURIComponent(userId)}`, {
        method: 'POST',
        body: JSON.stringify({
          type: therapy.type,
          description: therapy.description,
          frequency: therapy.frequency,
          duration: therapy.duration,
          performedby: therapy.performedby,
          startdate: therapy.startdate
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
      await this.fetchFromBackend(`/patients/${patientId}/therapies/${therapyId}`, {
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
      await this.fetchFromBackend(`/patients/${patientId}/therapies/${therapyId}/sessions`, {
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
      const response = await this.fetchFromBackend(`/watch-management/available`);
      return response?.availableWatches || [];
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
      const response = await this.fetchFromBackend(`/devices/assign`, {
        method: 'POST',
        body: JSON.stringify({
          deviceId: deviceId,
          patientId: patientId,
          assignedBy: staffId,
          notes: assignmentReason
        })
      });
      return response;
    } catch (error) {
      console.error('Failed to assign device:', error);
      throw error;
    }
  }

  static async unassignDevice(staffId: string, deviceId: string, unassignmentReason: string = 'patientDischarge'): Promise<boolean> {
    const caller = new Error().stack?.split('\n')[2]?.trim() || 'unknown';
    console.log('🌐 API.unassignDevice called:', { staffId, deviceId, unassignmentReason, caller });
    console.trace('API unassign call stack');
    try {
      const response = await this.fetchFromBackend(`/devices/unassign/${deviceId}?unassigned_by=${staffId}`, {
        method: 'POST'
      });
      return response.success;
    } catch (error) {
      console.error('Failed to unassign device:', error);
      throw error;
    }
  }

  static async reassignDevice(staffId: string, oldDeviceId: string, newDeviceId: string, reassignmentReason: string = 'deviceMalfunction'): Promise<any> {
    try {
      // Backend doesn't have reassign endpoint, so we unassign then assign
      await this.unassignDevice(staffId, oldDeviceId, reassignmentReason);
      const response = await this.assignDevice(staffId, newDeviceId, '', reassignmentReason);
      return response;
    } catch (error) {
      console.error('Failed to reassign device:', error);
      throw error;
    }
  }

  static async getPatientDevice(staffId: string, patientId: string): Promise<any | null> {
    try {
      const response = await this.fetchFromBackend(`/devices/assignments/?patient_id=${patientId}&active_only=true`);
      return response?.[0] || null; // Return first active assignment or null
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
  // NFC INTERACTION LOGGING
  // ================================

  static async logNfcTap(patientWatchId: string, staffNfcId: string, location?: string): Promise<boolean> {
    try {
      // Send to backend for storage
      await this.fetchFromBackend('/interactions/nfc-tap', {
        method: 'POST',
        body: JSON.stringify({
          patientWatchId,
          staffNfcId,
          timestamp: new Date().toISOString(),
          location: location || 'unknown',
          deviceType: 'esp32_watch',
          interactionType: 'staffPatientProximity'
        })
      });
      
      // Also log locally for audit trail
      try {
        const auditService = (await import('./services/auditService')).default;
        await auditService.logNfcInteraction(
          staffNfcId, 
          patientWatchId.replace('WATCH-', ''), // Extract patient ID from watch ID
          patientWatchId, 
          location,
          {
            nfcTapLogged: true,
            backendSynced: true
          }
        );
      } catch (auditError) {
        console.warn('Local audit logging failed for NFC interaction:', auditError);
      }
      
      console.log('✅ NFC interaction logged successfully:', { patientWatchId, staffNfcId, location });
      return true;
    } catch (error) {
      console.error('❌ Failed to log NFC interaction:', error);
      
      // Try to log locally even if backend fails (for offline resilience)
      try {
        const auditService = (await import('./services/auditService')).default;
        await auditService.logNfcInteraction(
          staffNfcId,
          patientWatchId.replace('WATCH-', ''),
          patientWatchId,
          location,
          {
            nfcTapLogged: true,
            backendSynced: false,
            offlineMode: true,
            error: error instanceof Error ? error.message : String(error)
          }
        );
      } catch (auditError) {
        console.error('Both backend and local audit logging failed:', auditError);
      }
      
      return false;
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

  // ================================
  // CASE SHEET METHODS
  // ================================

  static async getCaseEntries(patientId: string): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/case-entries`);
      if (!response || !Array.isArray(response)) {
        return [];
      }
      
      // Apply field mappings for case sheet entries
      return response.map((entry: any) => ({
        id: entry.id,
        timestamp: entry.timestamp,
        type: entry.entryType || entry.entrytype || entry.type,  // Fixed: backend sends entryType (camelCase)
        description: entry.description,
        performedBy: entry.performedbyname || entry.performedby || entry.performedBy,
        performedbyname: entry.performedbyname,  // Keep original field for CaseSheetBook component
        details: entry.details,
        canEdit: this.canEditItem(entry.timestamp)
      }));
    } catch (error) {
      console.error('❌ Failed to fetch case entries:', error);
      return [];
    }
  }

  static async addCaseEntry(patientId: string, entryData: {
    entryType: string;
    description: string;
    performedBy: string;
  }): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/case-entries`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(entryData)
      });
      return true;
    } catch (error) {
      console.error('❌ Failed to add case entry:', error);
      return false;
    }
  }
}


// Export the API class
export default HospitalAPI;

// ================================
// EXPORTED CONVENIENCE FUNCTIONS
// ================================

export const fetchAvailableDevices = async () => {
  try {
    return await HospitalAPI.fetchFromBackend('/devices/available');
  } catch (error) {
    console.error('Failed to fetch available devices:', error);
    return [];
  }
};

export const assignDeviceToPatient = async (patientId: string, deviceId: string, reason: string) => {
  try {
    const response = await HospitalAPI.fetchFromBackend(`/patients/${patientId}/assign-device`, {
      method: 'POST',
      body: JSON.stringify({
        deviceId,
        reason,
        assignedAt: new Date().toISOString()
      })
    });
    return { success: true, ...response };
  } catch (error) {
    console.error('Failed to assign device:', error);
    return { success: false, message: error instanceof Error ? error.message : 'Assignment failed' };
  }
};

export const replacePatientDevice = async (patientId: string, newDeviceId: string, reason: string) => {
  try {
    const response = await HospitalAPI.fetchFromBackend(`/patients/${patientId}/replace-device`, {
      method: 'PUT',
      body: JSON.stringify({
        newDeviceId,
        reason,
        replacedAt: new Date().toISOString()
      })
    });
    return { success: true, ...response };
  } catch (error) {
    console.error('Failed to replace device:', error);
    return { success: false, message: error instanceof Error ? error.message : 'Replacement failed' };
  }
};

export const detachDeviceFromPatient = async (patientId: string, reason: string) => {
  try {
    const response = await HospitalAPI.fetchFromBackend(`/patients/${patientId}/detach-device`, {
      method: 'DELETE',
      body: JSON.stringify({
        reason,
        detachedAt: new Date().toISOString()
      })
    });
    return { success: true, ...response };
  } catch (error) {
    console.error('Failed to detach device:', error);
    return { success: false, message: error instanceof Error ? error.message : 'Detachment failed' };
  }
};

export const addMedication = async (patientId: string, medication: any) => {
  try {
    const response = await HospitalAPI.fetchFromBackend(`/patients/${patientId}/medications`, {
      method: 'POST',
      body: JSON.stringify({
        ...medication,
        addedAt: new Date().toISOString(),
        status: 'active'
      })
    });
    return { success: true, medication: response };
  } catch (error) {
    console.error('Failed to add medication:', error);
    return { success: false, message: error instanceof Error ? error.message : 'Failed to add medication' };
  }
};

export const addInvestigation = async (patientId: string, investigation: any) => {
  try {
    const response = await HospitalAPI.fetchFromBackend(`/patients/${patientId}/investigations`, {
      method: 'POST',
      body: JSON.stringify({
        ...investigation,
        orderedDate: new Date().toISOString(),
        status: investigation.status || 'pending'
      })
    });
    return { success: true, investigation: response };
  } catch (error) {
    console.error('Failed to add investigation:', error);
    return { success: false, message: error instanceof Error ? error.message : 'Failed to add investigation' };
  }
};

export const addTherapy = async (patientId: string, therapy: any) => {
  try {
    const response = await HospitalAPI.fetchFromBackend(`/patients/${patientId}/therapies`, {
      method: 'POST',
      body: JSON.stringify({
        ...therapy,
        orderedDate: new Date().toISOString(),
        status: therapy.status || 'scheduled'
      })
    });
    return { success: true, therapy: response };
  } catch (error) {
    console.error('Failed to add therapy:', error);
    return { success: false, message: error instanceof Error ? error.message : 'Failed to add therapy' };
  }
};

export const addNote = async (patientId: string, content: string, noteType: string) => {
  try {
    const response = await HospitalAPI.fetchFromBackend(`/patients/${patientId}/notes`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        noteType,
        timestamp: new Date().toISOString(),
        canEdit: true,
        isEdited: false
      })
    });
    return { success: true, note: response };
  } catch (error) {
    console.error('Failed to add note:', error);
    return { success: false, message: error instanceof Error ? error.message : 'Failed to add note' };
  }
};