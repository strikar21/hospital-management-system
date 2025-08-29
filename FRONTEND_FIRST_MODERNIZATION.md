# Frontend-First CamelCase Modernization Strategy

## Strategy Overview
1. **Phase 1**: Complete frontend camelCase cleanup (Week 1-2)
2. **Phase 2**: Define clean API contracts from frontend needs (Week 2) 
3. **Phase 3**: Build fresh backend to match cleaned frontend (Week 3-4)
4. **Phase 4**: Integration and testing (Week 5)

## Phase 1: Complete Frontend Cleanup (Week 1-2)

### Current Frontend Snake_Case Analysis
- **17 files** with snake_case
- **522 total occurrences** 
- **Major files**: api.ts (106), PatientDetail.tsx (72), EnhancedVitalChart.tsx (50)

### 1.1 Fix Core Types (Day 1)

```typescript
// src/types.ts - COMPLETE MODERNIZATION
export interface Patient {
    id: string;
    name: string;
    bedNumber: string;
    ward: string;
    assignedDoctor: string;
    age?: number;
    gender?: string;
    diagnosis?: string;
    admissionDate?: string;
    currentStatus: 'stable' | 'critical' | 'emergency';
    codeStatus: 'fullCode' | 'dnr' | 'dnrCca' | 'comfortCare';
    activeProblems?: string[];
    lastMedicationTime?: string;
    nextMedicationDue?: string;
    vitals?: PatientVitals;
    allergies?: Allergy[];
    medications?: Medication[];
    caseSheet?: CaseSheetEntry[];
    handoffNotes?: HandoffNote[];
    createdAt: string;
    updatedAt?: string;
    isActive: boolean;
}

export interface PatientVitals {
    heartRate?: number;
    bloodPressure?: string;
    bloodPressureValue?: number;
    temperature?: number;
    respiratoryRate?: number;
    oxygenSat?: number;
    ecg?: number;
    eeg?: number;
    isEcgMode?: boolean;
    bioimpedance?: number;
    tremor?: number;
    fallRisk?: 'low' | 'medium' | 'high';
    lastUpdated?: string;
    lastSync?: string;
}

export interface VitalHistory {
    timestamp: string;
    deviceId: string;
    patientId: string;
    vitalType: string;
    value: number;
    unit: string;
    qualityIndicator?: string;
    metadata?: any;
}

export interface Device {
    id: number;
    deviceId: string;
    name: string;
    deviceType: string;
    status: 'online' | 'offline' | 'maintenance';
    location?: string;
    macAddress?: string;
    ipAddress?: string;
    firmwareVersion?: string;
    batteryLevel?: number;
    signalStrength?: number;
    assignmentStatus: 'free' | 'assigned' | 'maintenance';
    assignedTo?: string;
    assignedAt?: string;
    lastSeen?: string;
    lastHeartbeat?: string;
    createdAt: string;
    updatedAt?: string;
    isActive: boolean;
}

export interface Staff {
    id: string;
    staffId: string;
    firstName: string;
    lastName: string;
    name: string;
    email?: string;
    role: string;
    department?: string;
    nfcId?: string;
    isActive: boolean;
    createdAt: string;
    updatedAt?: string;
}

export interface Allergy {
    id: string;
    allergen: string;
    allergenType: string;
    reaction: string;
    severity: 'mild' | 'moderate' | 'severe';
    verificationStatus: 'unverified' | 'verified';
    recordedDate: string;
    recordedBy: string;
}

export interface Medication {
    id: string;
    name: string;
    dosage: string;
    frequency: string;
    route: string;
    status: 'active' | 'stopped' | 'held';
    startDate: string;
    endDate?: string;
    prescribedBy: string;
    canEdit: boolean;
}

export interface CaseSheetEntry {
    id: string;
    timestamp: string;
    type: string;
    description: string;
    performedBy: string;
    canEdit: boolean;
    details?: any;
}

export interface HandoffNote {
    id: string;
    patientId: string;
    shift: string;
    fromNurse: string;
    toNurse: string;
    priority: 'low' | 'medium' | 'high';
    content: string;
    status: string;
    acknowledgedBy?: string;
    acknowledgedAt?: string;
}
```

### 1.2 Modernize Main API File (Day 2-3)

```typescript
// src/api.ts - MAJOR CLEANUP (Fix 106 snake_case instances)

export class HospitalAPI {
    
    // Storage keys - camelCase
    private static readonly ACCESS_TOKEN_KEY = 'hospitalAccessToken';
    
    static async fetchFromBackend(endpoint: string, options: RequestInit = {}): Promise<any> {
        const url = `${BACKEND_BASE_URL}/api/v1${endpoint}`;
        const token = localStorage.getItem(this.ACCESS_TOKEN_KEY);
        
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            ...(options.headers as Record<string, string> || {})
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const response = await fetch(url, { headers, ...options });
        
        if (!response.ok) {
            if (response.status === 401) {
                localStorage.removeItem(this.ACCESS_TOKEN_KEY);
                throw new Error('Authentication required');
            }
            throw new Error(`API Error: ${response.status}`);
        }
        
        return response.json();
    }
    
    static async authenticateNFC(nfcId: string): Promise<User | null> {
        try {
            const response = await this.fetchFromBackend('/auth/nfc', {
                method: 'POST',
                body: JSON.stringify({ nfcId: nfcId })  // camelCase
            });
            
            localStorage.setItem(this.ACCESS_TOKEN_KEY, response.accessToken);
            
            return {
                id: response.userId,
                name: response.name,
                role: response.role,
                nfcId: nfcId,
                staffId: response.staffId,
                department: response.department
            };
        } catch (error) {
            console.error('NFC Authentication failed:', error);
            throw error;
        }
    }
    
    static async authenticateCredentials(staffId: string, password: string, pin?: string): Promise<User | null> {
        try {
            const response = await fetch(`/api/v1/staff/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    staffId: staffId,      // camelCase
                    password: pin ? undefined : password,
                    pin: pin || undefined
                })
            });
            
            if (!response.ok) {
                throw new Error(`Authentication failed: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.accessToken) {
                localStorage.setItem(this.ACCESS_TOKEN_KEY, data.accessToken);
            }
            
            return {
                id: data.staff.id,
                name: data.staff.name,
                role: data.staff.role,
                nfcId: data.staff.nfcId || '',
                staffId: data.staff.staffId,
                department: data.staff.department
            };
        } catch (error) {
            console.error('Authentication failed:', error);
            return null;
        }
    }
    
    static async getPatients(limit: number = 100): Promise<Patient[]> {
        const response = await this.fetchFromBackend(`/patients?limit=${limit}`);
        
        return response.map((p: any) => ({
            id: p.id,
            name: p.name,
            bedNumber: p.bedNumber,
            ward: p.ward,
            assignedDoctor: p.assignedDoctor,
            age: p.age,
            gender: p.gender,
            diagnosis: p.diagnosis,
            admissionDate: p.admissionDate,
            currentStatus: p.currentStatus,
            codeStatus: p.codeStatus,
            activeProblems: p.activeProblems || [],
            lastMedicationTime: p.lastMedicationTime,
            nextMedicationDue: p.nextMedicationDue,
            vitals: p.vitals ? {
                heartRate: p.vitals.heartRate || 75,
                bloodPressure: p.vitals.bloodPressure || '120/80',
                bloodPressureValue: p.vitals.bloodPressureValue || 120,
                temperature: p.vitals.temperature || 98.6,
                respiratoryRate: p.vitals.respiratoryRate || 16,
                oxygenSat: p.vitals.oxygenSat || 98,
                ecg: p.vitals.ecg || 120,
                eeg: p.vitals.eeg || 45,
                isEcgMode: p.vitals.isEcgMode !== undefined ? p.vitals.isEcgMode : true,
                bioimpedance: p.vitals.bioimpedance || 500,
                tremor: p.vitals.tremor || 0.0,
                fallRisk: p.vitals.fallRisk || 'low',
                lastUpdated: p.vitals.lastUpdated || new Date().toLocaleTimeString(),
                lastSync: p.vitals.lastSync || new Date().toISOString()
            } : undefined,
            allergies: (p.allergies || []).map((allergy: any) => ({
                id: allergy.id,
                allergen: allergy.allergen,
                allergenType: allergy.allergenType,
                reaction: allergy.reaction,
                severity: allergy.severity,
                verificationStatus: allergy.verificationStatus,
                recordedDate: allergy.recordedDate,
                recordedBy: allergy.recordedBy
            })),
            caseSheet: (p.caseSheet || []).map((entry: any) => ({
                id: entry.id,
                timestamp: entry.timestamp,
                type: entry.type,
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
                content: note.content,
                status: note.status,
                acknowledgedBy: note.acknowledgedBy,
                acknowledgedAt: note.acknowledgedAt
            })),
            createdAt: p.createdAt,
            updatedAt: p.updatedAt,
            isActive: p.isActive
        }));
    }
    
    static async getPatientVitalHistory(
        patientId: string, 
        timeRange: TimeRange = '24h',
        vitalType?: string
    ): Promise<VitalHistory[]> {
        const params = new URLSearchParams({
            timeRange: timeRange,
            patientId: patientId
        });
        
        if (vitalType) params.append('vitalType', vitalType);
        
        const response = await this.fetchFromBackend(`/patients/${patientId}/vitals/history?${params}`);
        
        return response.map((record: any) => ({
            timestamp: record.timestamp,
            deviceId: record.deviceId,
            patientId: record.patientId,
            vitalType: record.vitalType,
            value: record.value,
            unit: record.unit,
            qualityIndicator: record.qualityIndicator,
            metadata: record.metadata
        }));
    }
}
```

### 1.3 Update All Component Files (Day 4-5)

#### Fix PatientDetail.tsx (72 snake_case instances)
```typescript
// src/PatientDetail.tsx - MODERNIZED
const PatientDetail: React.FC<PatientDetailProps> = ({ patient, onClose }) => {
    const [vitalHistory, setVitalHistory] = useState<VitalHistory[]>([]);
    const [selectedVitalType, setSelectedVitalType] = useState<string>('heartRate');
    const [timeRange, setTimeRange] = useState<TimeRange>('24h');
    
    useEffect(() => {
        const loadVitalHistory = async () => {
            try {
                const history = await HospitalAPI.getPatientVitalHistory(
                    patient.id, 
                    timeRange, 
                    selectedVitalType
                );
                setVitalHistory(history);
            } catch (error) {
                console.error('Failed to load vital history:', error);
            }
        };
        
        loadVitalHistory();
    }, [patient.id, timeRange, selectedVitalType]);
    
    const handleVitalTypeChange = (vitalType: string) => {
        setSelectedVitalType(vitalType);
    };
    
    return (
        <div className="patient-detail">
            <div className="patient-header">
                <h2>{patient.name}</h2>
                <span className={`status ${patient.currentStatus}`}>
                    {patient.currentStatus.toUpperCase()}
                </span>
            </div>
            
            <div className="patient-info">
                <div className="info-section">
                    <h3>Basic Information</h3>
                    <p><strong>Bed:</strong> {patient.bedNumber}</p>
                    <p><strong>Ward:</strong> {patient.ward}</p>
                    <p><strong>Doctor:</strong> {patient.assignedDoctor}</p>
                    <p><strong>Age:</strong> {patient.age}</p>
                    <p><strong>Gender:</strong> {patient.gender}</p>
                    <p><strong>Diagnosis:</strong> {patient.diagnosis}</p>
                </div>
                
                <div className="info-section">
                    <h3>Clinical Status</h3>
                    <p><strong>Code Status:</strong> {patient.codeStatus}</p>
                    <p><strong>Admission:</strong> {patient.admissionDate}</p>
                    {patient.activeProblems && patient.activeProblems.length > 0 && (
                        <div>
                            <strong>Active Problems:</strong>
                            <ul>
                                {patient.activeProblems.map((problem, index) => (
                                    <li key={index}>{problem}</li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </div>
            
            <div className="vitals-section">
                <h3>Current Vitals</h3>
                {patient.vitals && (
                    <div className="vitals-grid">
                        <div className="vital-item">
                            <span className="vital-label">Heart Rate:</span>
                            <span className="vital-value">{patient.vitals.heartRate} BPM</span>
                        </div>
                        <div className="vital-item">
                            <span className="vital-label">Blood Pressure:</span>
                            <span className="vital-value">{patient.vitals.bloodPressure}</span>
                        </div>
                        <div className="vital-item">
                            <span className="vital-label">Temperature:</span>
                            <span className="vital-value">{patient.vitals.temperature}°F</span>
                        </div>
                        <div className="vital-item">
                            <span className="vital-label">Oxygen Sat:</span>
                            <span className="vital-value">{patient.vitals.oxygenSat}%</span>
                        </div>
                        <div className="vital-item">
                            <span className="vital-label">Respiratory Rate:</span>
                            <span className="vital-value">{patient.vitals.respiratoryRate}/min</span>
                        </div>
                        <div className="vital-item">
                            <span className="vital-label">Fall Risk:</span>
                            <span className={`vital-value ${patient.vitals.fallRisk}`}>
                                {patient.vitals.fallRisk.toUpperCase()}
                            </span>
                        </div>
                    </div>
                )}
            </div>
            
            <div className="vital-history-section">
                <h3>Vital History</h3>
                <div className="controls">
                    <select 
                        value={selectedVitalType} 
                        onChange={(e) => handleVitalTypeChange(e.target.value)}
                    >
                        <option value="heartRate">Heart Rate</option>
                        <option value="bloodPressureSystolic">Blood Pressure (Systolic)</option>
                        <option value="temperature">Temperature</option>
                        <option value="oxygenSaturation">Oxygen Saturation</option>
                        <option value="respiratoryRate">Respiratory Rate</option>
                    </select>
                    
                    <select 
                        value={timeRange} 
                        onChange={(e) => setTimeRange(e.target.value as TimeRange)}
                    >
                        <option value="1h">Last Hour</option>
                        <option value="6h">Last 6 Hours</option>
                        <option value="24h">Last 24 Hours</option>
                        <option value="7d">Last 7 Days</option>
                    </select>
                </div>
                
                <EnhancedVitalChart 
                    data={vitalHistory}
                    vitalType={selectedVitalType}
                    patientId={patient.id}
                />
            </div>
        </div>
    );
};
```

### 1.4 Update Remaining Component Files (Day 5-6)

```bash
# Files to update with snake_case counts:
# - EnhancedVitalChart.tsx (50 instances)
# - DeviceAssignment.tsx (46 instances) 
# - NurseAdmissionProcessing.tsx (48 instances)
# - PatientAdmission.tsx (23 instances)
# - StaffManagement.tsx (44 instances)
# - And 12 other component files
```

### 1.5 Create Mock Data Service (Day 6-7)
```typescript
// src/services/mockData.ts - For testing cleaned frontend
export const mockPatients: Patient[] = [
    {
        id: 'P001',
        name: 'John Doe',
        bedNumber: 'A101',
        ward: 'ICU',
        assignedDoctor: 'Dr. Smith',
        age: 45,
        gender: 'Male',
        diagnosis: 'Post-surgical monitoring',
        admissionDate: '2024-01-01T10:00:00Z',
        currentStatus: 'stable',
        codeStatus: 'fullCode',
        activeProblems: ['Hypertension', 'Diabetes'],
        lastMedicationTime: '2024-01-01T14:00:00Z',
        nextMedicationDue: '2024-01-01T18:00:00Z',
        vitals: {
            heartRate: 75,
            bloodPressure: '120/80',
            bloodPressureValue: 120,
            temperature: 98.6,
            respiratoryRate: 16,
            oxygenSat: 98,
            ecg: 120,
            eeg: 45,
            isEcgMode: true,
            bioimpedance: 500,
            tremor: 0.1,
            fallRisk: 'low',
            lastUpdated: new Date().toLocaleTimeString(),
            lastSync: new Date().toISOString()
        },
        allergies: [
            {
                id: 'A001',
                allergen: 'Penicillin',
                allergenType: 'medication',
                reaction: 'rash',
                severity: 'moderate',
                verificationStatus: 'verified',
                recordedDate: '2024-01-01',
                recordedBy: 'Dr. Smith'
            }
        ],
        medications: [
            {
                id: 'M001',
                name: 'Metoprolol',
                dosage: '25mg',
                frequency: 'BID',
                route: 'PO',
                status: 'active',
                startDate: '2024-01-01',
                prescribedBy: 'Dr. Smith',
                canEdit: true
            }
        ],
        caseSheet: [
            {
                id: 'C001',
                timestamp: '2024-01-01T10:00:00Z',
                type: 'admission',
                description: 'Patient admitted for post-surgical monitoring',
                performedBy: 'Dr. Smith',
                canEdit: false
            }
        ],
        handoffNotes: [
            {
                id: 'H001',
                patientId: 'P001',
                shift: 'day',
                fromNurse: 'Nurse Johnson',
                toNurse: 'Nurse Davis',
                priority: 'medium',
                content: 'Monitor vital signs every 2 hours',
                status: 'active'
            }
        ],
        createdAt: '2024-01-01T10:00:00Z',
        updatedAt: '2024-01-01T14:00:00Z',
        isActive: true
    }
];

export const mockVitalHistory: VitalHistory[] = [
    {
        timestamp: '2024-01-01T10:00:00Z',
        deviceId: 'DEV001',
        patientId: 'P001',
        vitalType: 'heartRate',
        value: 75,
        unit: 'BPM',
        qualityIndicator: 'good'
    },
    {
        timestamp: '2024-01-01T10:15:00Z',
        deviceId: 'DEV001',
        patientId: 'P001',
        vitalType: 'heartRate',
        value: 78,
        unit: 'BPM',
        qualityIndicator: 'good'
    }
];
```

## Phase 2: Define API Contracts (Week 2)

Based on the cleaned frontend, define exactly what camelCase APIs the new backend needs to provide:

```typescript
// API-CONTRACTS.md - What the new backend must provide

// GET /api/v1/patients
interface GetPatientsResponse {
    patients: Patient[];
    total: number;
    page: number;
    limit: number;
}

// GET /api/v1/patients/:id/vitals/history
interface GetVitalHistoryResponse {
    vitalHistory: VitalHistory[];
    patientId: string;
    timeRange: string;
    vitalType?: string;
}

// POST /api/v1/auth/nfc
interface NFCAuthRequest {
    nfcId: string;
}

interface NFCAuthResponse {
    userId: string;
    staffId: string;
    name: string;
    role: string;
    department: string;
    accessToken: string;
    tokenType: string;
}

// All API contracts defined from cleaned frontend expectations
```

This approach ensures your cleaned frontend drives the backend design, resulting in a perfectly matched system with zero snake_case throughout.

**Ready to start the frontend cleanup?** I can begin with the types.ts file and work through each component systematically.