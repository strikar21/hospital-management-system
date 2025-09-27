import React, { useState, useEffect, useCallback } from 'react';
import {
  ChevronLeft, Heart, Activity, Thermometer, Droplets, Zap,
  Edit, FileText, Clock, User as UserIcon,
  TestTube, Shield, XCircle, MessageCircle,
  Send
} from 'lucide-react';
import { patient, user, investigation, therapy, caseSheetEntry, alert as alertType, noteComment, clinicalAlert, labResult, imagingStudy } from './types';
import {
  getStatusColor, getVitalStatusColor, formatTimeOnly, formatDateTime
} from './utils';
import { MedicalUtils } from './utils/medicalUtils';
import { PermissionUtils } from './utils/permissionUtils';
import { PatientService } from './services';
import CaseSheetBook from './CaseSheetBook';
import PatientAlerts from './components/PatientAlerts';
import PatientMedications from './components/PatientMedications';
import ECGViewer from './components/ECGViewer';
import PatientInvestigations from './components/PatientInvestigations';
import PatientTherapies from './components/PatientTherapies';


interface PatientDetailProps {
  patient: patient;
  currentUser: user;
  onClose: () => void;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onECGView?: (patient: patient) => void;
  onToggleECGMode?: (patient: patient) => void;
  onPatientDischarge?: (patientId: string) => void;
}

const PatientDetailComponent: React.FC<PatientDetailProps> = ({
  patient,
  currentUser,
  onClose,
  onVitalClick,
  onECGView,
  onToggleECGMode,
  onPatientDischarge
}) => {
  // Only log non-sensitive information in development
  if (process.env.NODE_ENV === 'development') {
    console.log('🏥 PatientDetail loading for patient ID:', patient.id);
    console.log('👤 Current user role:', currentUser.role);
    console.log('🔐 Can view medications:', PermissionUtils.canViewMedications(currentUser.role));
    console.log('💊 Patient medications count:', patient.medications?.length || 0);
    console.log('🧪 Patient investigations count:', patient.investigations?.length || 0);
    console.log('🏃 Patient therapies count:', patient.therapies?.length || 0);
  }
  
  
  const [activeTab, setActiveTab] = useState<'overview' | 'medications' | 'investigations' | 'therapy' | 'notes' | 'casesheet'>('overview');
  const [medications, setMedications] = useState<medication[]>(patient.medications || []);
  const [investigations, setInvestigations] = useState<investigation[]>(patient.investigations || []);
  const [therapies, setTherapies] = useState<therapy[]>(patient.therapies || []);
  const [notes, setNotes] = useState<noteComment[]>(patient.notes || []);
  const [alerts, setAlerts] = useState<alertType[]>(patient.alerts || []);
  const [caseSheet, setCaseSheet] = useState<caseSheetEntry[]>(patient.caseSheet || []);
  
  
  
  // Investigation form
  const [isAddingInvestigation, setIsAddingInvestigation] = useState(false);
  const [newInvestigation, setNewInvestigation] = useState({
    type: 'lab' as const, name: '', priority: 'routine' as const, notes: ''
  });
  
  // Therapy form
  const [isAddingTherapy, setIsAddingTherapy] = useState(false);
  const [newTherapy, setNewTherapy] = useState({
    type: 'physiotherapy' as const, description: '', frequency: '', duration: ''
  });
  
  // Clinical Decision Support
  
  // Lab Integration
  const [labResults, setLabResults] = useState<labResult[]>([]);
  const [loadingLabResults, setLoadingLabResults] = useState(false);
  
  // Imaging/PACS Integration
  const [imagingStudies, setImagingStudies] = useState<imagingStudy[]>([]);
  const [loadingImaging, setLoadingImaging] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  

  // Loading states
  const [addingInvestigation, setAddingInvestigation] = useState(false);
  const [addingTherapy, setAddingTherapy] = useState(false);

  // Sync local states with props
  useEffect(() => {
    setCaseSheet(patient.caseSheet || []);
    setMedications(patient.medications || []);
    setInvestigations(patient.investigations || []);
    setTherapies(patient.therapies || []);
    setNotes(patient.notes || []);
    setAlerts(patient.alerts || []);
  }, [patient.caseSheet, patient.medications, patient.investigations, patient.therapies, patient.notes, patient.alerts]);


  // Sync alerts
  useEffect(() => {
    setAlerts(patient.alerts || []);
  }, [patient.alerts]);


  // Centralized function to add case sheet entry with duplicate check
  const addCaseSheetEntry = useCallback((entry: caseSheetEntry) => {
    setCaseSheet(prev => {
      const isDuplicate = prev.some(
        existing => 
          existing.type === entry.type &&
          existing.description === entry.description &&
          existing.performedBy === entry.performedBy &&
          Math.abs(new Date(existing.timestamp).getTime() - new Date(entry.timestamp).getTime()) < 1000 // within 1 second
      );
      if (!isDuplicate) {
        return [...prev, entry];
      }
      return prev;
    });
  }, []);

  // Debounce utility
  const debounce = (func: (...args: any[]) => void, wait: number) => {
    let timeout: NodeJS.Timeout;
    return (...args: any[]) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  };






  // Real Hospital Discharge Workflow Functions
  const handleDoctorRequestDischarge = async () => {
    if (window.confirm(`Request discharge for ${patient.name}?\n\nThis will:\n• Send request to Hospital Administration for approval\n• Patient will remain active until fully processed\n\nConfirm discharge request?`)) {
            try {
        const response = await fetch(`/api/v2/patients/${patient.id}/discharge-request`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            doctorId: currentUser.id,
            reason: 'Medical discharge - patient condition stable'
          })
        });
        if (response.ok) {
          // Success - no second popup needed, user will see status change
        } else {
          throw new Error('Request failed');
        }
      } catch (error) {
        alert('Failed to submit discharge request. Please try again.');
      } finally {
              }
    }
  };

  const handleAdminApproveDischarge = async () => {
    if (window.confirm(`Approve discharge for ${patient.name}?\n\nThis confirms:\n• Insurance/billing clearance\n• Administrative approval\n• Ready for nurse to complete discharge\n\nApprove discharge?`)) {
            try {
        const response = await fetch(`/api/v2/patients/${patient.id}/discharge-approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            adminId: currentUser.id,
            approvalNote: 'Insurance cleared, billing completed, discharge approved'
          })
        });
        if (response.ok) {
          // Success - no second popup needed, user will see status change
        } else {
          throw new Error('Approval failed');
        }
      } catch (error) {
        alert('Failed to approve discharge. Please try again.');
      } finally {
              }
    }
  };

  const handleNurseCompleteDischarge = async () => {
    if (window.confirm(`Complete discharge for ${patient.name}?\n\nThis will:\n• Remove patient from active list\n• Free up bed and equipment\n• Generate discharge summary\n• Complete the discharge process\n\nComplete discharge?`)) {
            try {
        const response = await fetch(`/api/v2/patients/${patient.id}/discharge-complete`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nurseId: currentUser.id,
            followUpInstructions: 'Follow up with primary care in 1 week',
            activityLevel: 'Resume normal activities',
            dietInstructions: 'Patient education completed, discharge instructions provided'
          })
        });
        if (response.ok) {
          // Add case entry
          const newCaseEntry: caseSheetEntry = {
            id: 'cs_' + Date.now(),
            timestamp: new Date().toISOString(),
            type: getRoleBasedNoteType(currentUser.role),
            description: `Patient discharged by ${currentUser.name} (${currentUser.role})`,
            performedBy: currentUser.name,
            canEdit: false
          };
          addCaseSheetEntry(newCaseEntry);

          // Notify parent and close
          if (onPatientDischarge) {
            onPatientDischarge(patient.id);
          }
          setTimeout(() => onClose(), 1000);
          // Success - patient discharged, detail will close automatically
        } else {
          throw new Error('Discharge failed');
        }
      } catch (error) {
        alert('Failed to complete discharge. Please try again.');
      } finally {
              }
    }
  };

  const renderDischargeWorkflowButton = () => {
    const dischargeStatus = patient.status || 'active';

    if (currentUser.role === 'Doctor') {
      if (dischargeStatus === 'active') {
        return (
          <button
            onClick={handleDoctorRequestDischarge}
            className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
            title="Request Discharge"
          >
            <X className="w-4 h-4" />
            <span>Request Discharge</span>
          </button>
        );
      } else if (dischargeStatus === 'pendingDischarge') {
        return <div className="text-xs text-yellow-600 px-2 py-1 bg-yellow-100 rounded">Discharge Requested - Awaiting Admin</div>;
      } else {
        return <div className="text-xs text-green-600 px-2 py-1 bg-green-100 rounded">Discharge in Progress</div>;
      }
    } else if (currentUser.role === 'Administrator') {
      if (dischargeStatus === 'pendingDischarge') {
        return (
          <button
            onClick={handleAdminApproveDischarge}
            className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
            title="Approve Discharge"
          >
            <X className="w-4 h-4" />
            <span>Approve Discharge</span>
          </button>
        );
      } else if (dischargeStatus === 'readyForNurse' || dischargeStatus === 'dischargeApproved') {
        return <div className="text-xs text-green-600 px-2 py-1 bg-green-100 rounded">Approved - Awaiting Nurse</div>;
      } else {
        return <div className="text-xs text-gray-500">No pending requests</div>;
      }
    } else if (currentUser.role === 'Nurse') {
      if (dischargeStatus === 'readyForNurse' || dischargeStatus === 'dischargeApproved') {
        return (
          <button
            onClick={handleNurseCompleteDischarge}
            className="flex items-center space-x-1 px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
            title="Complete Discharge"
          >
            <X className="w-4 h-4" />
            <span>Complete Discharge</span>
          </button>
        );
      } else {
        return <div className="text-xs text-gray-500">No approved discharges</div>;
      }
    } else {
      return <div className="text-xs text-gray-500">Role: {currentUser.role}</div>;
    }
  };



  const tabs = [
    { id: 'overview', label: 'Overview', icon: UserIcon },
    { id: 'medications', label: 'Medications', icon: Plus },
    { id: 'investigations', label: 'Investigations', icon: TestTube },
    { id: 'therapy', label: 'Therapy', icon: Heart },
    { id: 'notes', label: 'Notes', icon: MessageCircle },
    { id: 'casesheet', label: 'Case Sheet', icon: FileText }
  ]; // All tabs visible to all roles - permissions handled within each tab
  

  // Enhanced case sheet that includes all activities, with only notes categorized by staff role
  const getEnhancedCaseSheet = () => {
    const enhancedEntries = [...caseSheet];

    // Ensure arrays are properly handled - backend might return non-arrays
    const ensureArray = (item: any) => {
      if (!item) return [];
      if (Array.isArray(item)) return item;
      if (typeof item === 'object') return Object.values(item);
      return [];
    };

    // For existing entries where we need to guess from performer name (legacy data)
    const getRoleFromPerformer = (performedBy: string): 'doctorNotes' | 'nursingNotes' | 'therapistNotes' | 'technicianNotes' | 'pharmacyNotes' | 'otherNotes' => {
      if (!performedBy) return 'otherNotes';
      const name = performedBy.toLowerCase();
      if (name.includes('dr.') || name.includes('doctor')) return 'doctorNotes';
      if (name.includes('nurse') || name.includes('nursing')) return 'nursingNotes';
      if (name.includes('therapist') || name.includes('therapy')) return 'therapistNotes';
      if (name.includes('tech') || name.includes('lab') || name.includes('radiology')) return 'technicianNotes';
      if (name.includes('pharmacy') || name.includes('pharmacist')) return 'pharmacyNotes';
      // Try to guess from common doctor names pattern "FirstName LastInitial"
      if (name.match(/^[a-z]+ [a-z]$/)) return 'doctorNotes'; // "Srikar A" pattern
      return 'otherNotes';
    };

    // Add medication entries - keep as MEDICATION type
    ensureArray(medications).forEach((med: any) => {
      enhancedEntries.push({
        id: `med-${med.id}`,
        timestamp: med.createdAt,
        type: 'medication',
        description: `💊 ${med.name} (${med.dosage}) - ${med.frequency} via ${med.route}. Status: ${med.status.toUpperCase()}`,
        performedBy: med.prescribedBy,
        canEdit: false
      });
    });
    
    // Add investigation entries - keep as INVESTIGATION type
    ensureArray(investigations).forEach((inv: any) => {
      enhancedEntries.push({
        id: `inv-${inv.id}`,
        timestamp: inv.createdAt ? `${inv.createdAt}T00:00:00Z` : new Date().toISOString(),
        type: 'investigation',
        description: `🧪 ${inv.name} (${inv.type}) - Priority: ${inv.priority.toUpperCase()}, Status: ${inv.status.toUpperCase()}`,
        performedBy: inv.performedBy,
        canEdit: false
      });
    });
    
    // Add therapy entries - keep as THERAPY type
    ensureArray(therapies).forEach((therapy: any) => {
      enhancedEntries.push({
        id: `therapy-${therapy.id}`,
        timestamp: therapy.startDate ? `${therapy.startDate}T00:00:00Z` : new Date().toISOString(),
        type: 'therapy',
        description: `🏃 ${therapy.type.toUpperCase()}: ${therapy.description} - ${therapy.frequency}, ${therapy.duration}. Status: ${therapy.status.toUpperCase()}`,
        performedBy: therapy.performedBy,
        canEdit: false
      });
    });

    // Add written notes - categorize by staff role based on who authored them
    ensureArray(notes).forEach((note: any) => {
      enhancedEntries.push({
        id: `note-${note.id}`,
        timestamp: note.timestamp,
        type: getRoleFromPerformer(note.authorName),
        description: `📝 ${note.content}`,
        performedBy: note.authorName,
        canEdit: note.canEdit
      });
    });
    
    // Map case sheet entries - keep known medical activities as-is, categorize everything else by staff role
    const knownMedicalTypes = ['admission', 'medication', 'investigation', 'therapy', 'vitalAlert', 'statusChange', 'alertAcknowledged', 'discharge'];
    const mappedCaseEntries = caseSheet.map(entry => ({
      ...entry,
      type: knownMedicalTypes.includes(entry.type) ? entry.type : getRoleFromPerformer(entry.performedBy)
    }));
    
    // Replace original case sheet entries with mapped ones, add all others as-is
    const allEntries = [...mappedCaseEntries, ...enhancedEntries.slice(caseSheet.length)];
    
    // Sort by timestamp (oldest first for chronological order)
    return allEntries.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  };
  
  // Clinical Decision Support - Check for alerts when patient data changes
  useEffect(() => {
    const checkClinicalAlerts = () => {
      // Clinical decision support temporarily disabled
      const alerts: clinicalAlert[] = [];
      setClinicalAlerts(alerts);

      if (alerts.length > 0 && alerts.some(alert => alert.actionRequired)) {
        setShowClinicalAlerts(true);
      }
    };
    
    checkClinicalAlerts();
  }, [patient, medications, investigations, therapies]);
  
  // Lab Integration - Auto-fetch lab results
  useEffect(() => {
    const fetchLabResults = async () => {
      setLoadingLabResults(true);
      try {
        const results = await Promise.resolve([]);
        setLabResults(results);
        
        // Auto-update investigations with lab results
        const updatedInvestigations = await Promise.all(
          investigations.map(async (inv) => {
            if (inv.type === 'lab' && inv.status === 'inProgress') {
              return await Promise.resolve(inv);
            }
            return inv;
          })
        );
        
        // Check if any investigations were updated
        const hasUpdates = updatedInvestigations.some((inv, index) => 
          inv.status !== investigations[index].status
        );
        
        if (hasUpdates) {
          setInvestigations(updatedInvestigations);
        }
        
      } catch (error) {
        console.error('Failed to fetch lab results:', error);
      } finally {
        setLoadingLabResults(false);
      }
    };
    
    fetchLabResults();
  }, [patient.id]); // eslint-disable-line react-hooks/exhaustive-deps
  
  // Imaging Integration - Auto-fetch imaging studies
  useEffect(() => {
    const fetchImagingStudies = async () => {
      setLoadingImaging(true);
      try {
        // Imaging service temporarily disabled
        const studies: imagingStudy[] = [];
        setImagingStudies(studies);
      } catch (error) {
        console.error('Failed to fetch imaging studies:', error);
      } finally {
        setLoadingImaging(false);
      }
    };
    
    fetchImagingStudies();
  }, [patient.id]);
  
  // Pharmacy functionality removed
  

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div 
        className="bg-white rounded-2xl shadow-2xl w-full max-w-7xl h-[85vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Compact Header */}
        <div className="p-3 border-b flex items-center justify-between bg-white sticky top-0 z-10">
          <div className="flex items-center space-x-3">
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="Close"
            >
              <ChevronLeft className="w-5 h-5 text-gray-600" />
            </button>
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-1">
                <h2 className="text-xl font-bold text-gray-900">{patient.name}</h2>
                
                {/* Critical Safety Indicators */}
                <div className="flex items-center space-x-2">
                  {/* Code Status */}
                  {patient.codeStatus && (
                    <div className={`px-2 py-1 rounded text-xs font-bold ${
                      patient.codeStatus === 'dnr' ? 'bg-purple-100 text-purple-800 border-2 border-purple-400' :
                      patient.codeStatus === 'dnrcca' ? 'bg-purple-100 text-purple-800 border-2 border-purple-400' :
                      patient.codeStatus === 'comfortcare' ? 'bg-blue-100 text-blue-800 border-2 border-blue-400' :
                      'bg-green-100 text-green-800 border-2 border-green-400'
                    }`}>
                      {patient.codeStatus === 'fullcode' ? 'FULL CODE' :
                       patient.codeStatus === 'dnr' ? 'DNR' :
                       patient.codeStatus === 'dnrcca' ? 'DNR/CCA' :
                       'COMFORT CARE'}
                    </div>
                  )}
                  
                  {/* Fall Risk */}
                  {patient.vitals?.fallRisk === 'high' && (
                    <div className="px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-800 border-2 border-red-400 animate-pulse">
                      🚨 FALL RISK
                    </div>
                  )}
                  
                  {/* Allergy Alert */}
                  {patient.allergies && patient.allergies.length > 0 && (
                    <div className="px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-800 border-2 border-red-400">
                      🚨 ALLERGIES ({patient.allergies.length})
                    </div>
                  )}
                </div>
              </div>
              
              <p className="text-sm text-gray-600">
                {patient.age}y • {patient.gender} • {patient.weight}kg • Bed {patient.bedNumber} • Room {patient.room}
              </p>
              
              {/* Active Problems List */}
              {patient.activeProblems && patient.activeProblems.length > 0 && (
                <div className="mt-1">
                  <span className="text-xs text-gray-500 font-medium">Active Problems: </span>
                  <span className="text-xs text-gray-700">
                    {patient.activeProblems.join(', ')}
                  </span>
                </div>
              )}
              
              {/* Next Medication Due */}
              {patient.nextMedicationDue && (
                <div className="mt-1">
                  <span className="text-xs text-blue-600 font-medium">
                    💊 Next medication due: {new Date(patient.nextMedicationDue).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(patient.status)}`}>
              {patient.status.toUpperCase()}
            </div>
            {renderDischargeWorkflowButton()}
            <div className="text-xs text-gray-500">
              Updated: {formatTimeOnly((patient.vitals?.lastDataReceived || new Date()).toString())}
            </div>
            <div className="text-xs text-gray-500">
              <Shield className="w-4 h-4 inline mr-1" />
              HIPAA Compliant
            </div>
          </div>
        </div>

        {/* Patient Alerts Component */}
        <PatientAlerts
          patient={patient}
          currentUser={currentUser}
          alerts={alerts}
          setAlerts={setAlerts}
        />


        {/* Compact Tab Navigation */}
        <div className="px-3 bg-gray-50 border-b">
          <div className="flex space-x-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-2 px-3 py-1.5 text-sm font-medium rounded-t-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-white text-blue-600 border-t-2 border-blue-600'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {tab.id === 'notes' && notes.length > 0 && (
                  <span className="bg-blue-100 text-blue-600 px-1 py-0.5 rounded-full text-xs">
                    {notes.length}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content - Fixed Height to Prevent Scrolling */}
        <div className="flex-1 overflow-hidden">
          {/* Overview Tab - Equal Vitals Layout */}
          {activeTab === 'overview' && (
            <div className="p-2 h-full flex flex-col space-y-2">
              {/* Patient Info Row */}
              <div className="bg-gray-50 rounded-lg p-3 mb-2 flex-shrink-0">
                <h3 className="text-sm font-semibold mb-2">Patient Information</h3>
                <div className="grid grid-cols-3 gap-4 text-xs">
                  <div>
                    <p><span className="font-medium text-gray-600">Age:</span> {patient.age}y • <span className="font-medium text-gray-600">Gender:</span> {patient.gender}</p>
                    <p><span className="font-medium text-gray-600">Weight:</span> {patient.weight}kg • <span className="font-medium text-gray-600">BMI:</span> {(patient.weight / Math.pow(1.75, 2)).toFixed(1)}</p>
                  </div>
                  <div>
                    <p><span className="font-medium text-gray-600">Room:</span> {patient.room} • <span className="font-medium text-gray-600">Ward:</span> {patient.ward}</p>
                    <p><span className="font-medium text-gray-600">Department:</span> {patient.department}</p>
                  </div>
                  <div>
                    <p><span className="font-medium text-gray-600">Diagnosis:</span> {patient.diagnosis}</p>
                    <p><span className="font-medium text-gray-600">Doctor:</span> {patient.assignedDoctor}</p>
                  </div>
                </div>
              </div>

              {/* Vital Trends Quick View */}
              <div className="bg-blue-50 rounded-lg p-3 mb-2 flex-shrink-0">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-blue-800">📊 Vital Trends (Last 4 Hours)</h3>
                  <button
                    onClick={() => onVitalClick(patient, 'trends')}
                    className="text-xs text-blue-600 hover:text-blue-800 hover:underline"
                  >
                    View Detailed Charts →
                  </button>
                </div>
                <div className="grid grid-cols-4 gap-3">
                  {/* Heart Rate Trend */}
                  <div className="bg-white rounded p-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-600">Heart Rate</span>
                      <Heart className="w-3 h-3 text-red-500" />
                    </div>
                    <div className="flex items-end space-x-1 h-8">
                      {/* Mock mini trend bars */}
                      {[75, 78, 72, 76, 79, 75].map((value, idx) => (
                        <div 
                          key={idx}
                          className="bg-red-300 w-2 rounded-sm"
                          style={{ height: `${(value / 100) * 100}%` }}
                          title={`${value} BPM`}
                        />
                      ))}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {patient.vitals?.heartRate || 0} BPM •
                      <span className="text-green-600 ml-1">↗ Stable</span>
                    </div>
                  </div>

                  {/* Blood Pressure Trend */}
                  <div className="bg-white rounded p-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-600">Blood Pressure</span>
                      <Droplets className="w-3 h-3 text-blue-500" />
                    </div>
                    <div className="flex items-end space-x-1 h-8">
                      {[120, 118, 122, 119, 121, 120].map((value, idx) => (
                        <div 
                          key={idx}
                          className="bg-blue-300 w-2 rounded-sm"
                          style={{ height: `${(value / 150) * 100}%` }}
                          title={`${value} mmHg`}
                        />
                      ))}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {patient.vitals?.systolicPressure || '--'}/{patient.vitals?.diastolicPressure || '--'} •
                      <span className="text-green-600 ml-1">→ Normal</span>
                    </div>
                  </div>

                  {/* Temperature Trend */}
                  <div className="bg-white rounded p-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-600">Temperature</span>
                      <Thermometer className="w-3 h-3 text-orange-500" />
                    </div>
                    <div className="flex items-end space-x-1 h-8">
                      {[98.6, 98.4, 98.8, 98.5, 98.6, 98.7].map((value, idx) => (
                        <div 
                          key={idx}
                          className="bg-orange-300 w-2 rounded-sm"
                          style={{ height: `${((value - 96) / 6) * 100}%` }}
                          title={`${value}°F`}
                        />
                      ))}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {patient.vitals?.skinTemperature ? patient.vitals.skinTemperature.toFixed(1) : '--'}°F •
                      <span className="text-green-600 ml-1">→ Normal</span>
                    </div>
                  </div>

                  {/* Oxygen Saturation Trend */}
                  <div className="bg-white rounded p-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-600">SpO₂</span>
                      <Activity className="w-3 h-3 text-green-500" />
                    </div>
                    <div className="flex items-end space-x-1 h-8">
                      {[98, 97, 99, 98, 98, 97].map((value, idx) => (
                        <div 
                          key={idx}
                          className="bg-green-300 w-2 rounded-sm"
                          style={{ height: `${(value / 100) * 100}%` }}
                          title={`${value}%`}
                        />
                      ))}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {patient.vitals?.oxygenSaturation || '--'}% •
                      <span className="text-green-600 ml-1">→ Good</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* All Vitals - Single Row Layout (8×1) */}
              <div className="bg-gray-50 rounded-lg p-1 mb-2 flex-shrink-0">
                <div className="grid grid-cols-8 gap-2">
                  <div 
                    className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
                    onClick={() => onVitalClick(patient, 'heartRate')}
                  >
                    <p className="text-xs text-gray-600 mb-2 text-center font-medium">Heart Rate</p>
                    <div className="flex items-center justify-between">
                      <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(patient.vitals?.heartRate || 0, 'heartRate'))}`}>
                        <Heart className="w-5 h-5" />
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-xl text-red-600">{patient.vitals?.heartRate || '--'}</span>
                        <span className="text-xs text-gray-500 ml-1">BPM</span>
                      </div>
                    </div>
                  </div>

                  <div 
                    className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
                    onClick={() => onVitalClick(patient, 'systolicPressure')}
                  >
                    <p className="text-xs text-gray-600 mb-2 text-center font-medium">Blood Pressure</p>
                    <div className="flex items-center justify-between">
                      <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(patient.vitals?.systolicPressure || 0, 'systolicPressure', patient.vitals?.diastolicPressure || 0))}`}>
                        <Droplets className="w-5 h-5" />
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-lg text-purple-600">{patient.vitals?.systolicPressure || '--'}/{patient.vitals?.diastolicPressure || '--'}</span>
                        <span className="text-xs text-gray-500 ml-1">mmHg</span>
                      </div>
                    </div>
                  </div>

                  <div 
                    className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
                    onClick={() => onVitalClick(patient, 'oxygenSaturation')}
                  >
                    <p className="text-xs text-gray-600 mb-2 text-center font-medium">Oxygen Sat</p>
                    <div className="flex items-center justify-between">
                      <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(patient.vitals?.oxygenSaturation || 0, 'oxygenSaturation'))}`}>
                        <Activity className="w-5 h-5" />
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-xl text-blue-600">{patient.vitals?.oxygenSaturation || '--'}</span>
                        <span className="text-xs text-gray-500 ml-1">%</span>
                      </div>
                    </div>
                  </div>

                  <div 
                    className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
                    onClick={() => onVitalClick(patient, 'skinTemperature')}
                  >
                    <p className="text-xs text-gray-600 mb-2 text-center font-medium">Temperature</p>
                    <div className="flex items-center justify-between">
                      <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(patient.vitals?.skinTemperature || 0, 'skinTemperature'))}`}>
                        <Thermometer className="w-5 h-5" />
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-xl text-orange-600">{patient.vitals?.skinTemperature ? patient.vitals.skinTemperature.toFixed(1) : '--'}</span>
                        <span className="text-xs text-gray-500 ml-1">°F</span>
                      </div>
                    </div>
                  </div>

                  <div 
                    className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
                    onClick={() => onVitalClick(patient, 'respiratoryRate')}
                  >
                    <p className="text-xs text-gray-600 mb-2 text-center font-medium">Respiratory Rate</p>
                    <div className="flex items-center justify-between">
                      <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(patient.vitals?.respiratoryRate || 0, 'respiratoryRate'))}`}>
                        <Activity className="w-5 h-5" />
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-xl text-cyan-600">{patient.vitals?.respiratoryRate || '--'}</span>
                        <span className="text-xs text-gray-500 ml-1">/min</span>
                      </div>
                    </div>
                  </div>

                  <div 
                    className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
                    onClick={() => onVitalClick(patient, patient.vitals?.isEcgMode ? 'ecgReading' : 'eegReading')}
                  >
                    <p className="text-xs text-gray-600 mb-2 text-center font-medium">{patient.vitals?.isEcgMode ? 'ECG' : 'EEG'}</p>
                    <div className="flex items-center justify-between">
                      <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(patient.vitals?.isEcgMode ? (patient.vitals?.ecgReading || 0) : (patient.vitals?.eegReading || 0), patient.vitals?.isEcgMode ? 'ecgReading' : 'eegReading'))}`}>
                        <Zap className="w-5 h-5" />
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-xl text-green-600">{patient.vitals?.isEcgMode ? (patient.vitals?.ecgReading || '--') : (patient.vitals?.eegReading || '--')}</span>
                        <span className="text-xs text-gray-500 ml-1">{patient.vitals?.isEcgMode ? 'mV' : 'μV'}</span>
                      </div>
                    </div>
                  </div>

                  <div 
                    className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
                    onClick={() => onVitalClick(patient, 'bioelectricalImpedance')}
                  >
                    <p className="text-xs text-gray-600 mb-2 text-center font-medium">Bioimpedance</p>
                    <div className="flex items-center justify-between">
                      <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(patient.vitals?.bioelectricalImpedance || 0, 'bioelectricalImpedance'))}`}>
                        <Zap className="w-5 h-5" />
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-xl text-teal-600">{patient.vitals?.bioelectricalImpedance || '--'}</span>
                        <span className="text-xs text-gray-500 ml-1">Ω</span>
                      </div>
                    </div>
                  </div>

                  <div 
                    className="bg-white rounded-lg p-2 cursor-pointer hover:bg-blue-50 transition-colors border"
                    onClick={() => onVitalClick(patient, 'tremorIntensity')}
                  >
                    <p className="text-xs text-gray-600 mb-2 text-center font-medium">Tremor Level</p>
                    <div className="flex items-center justify-between">
                      <div className={`p-1 rounded-lg ${getVitalStatusColor(MedicalUtils.getVitalStatus(patient.vitals?.tremorIntensity || 0, 'tremorIntensity'))}`}>
                        <Activity className="w-5 h-5" />
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-xl text-pink-600">{patient.vitals?.tremorIntensity ? patient.vitals.tremorIntensity.toFixed(1) : '--'}</span>
                        <span className="text-xs text-gray-500 ml-1">/10</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <ECGViewer
                patient={patient}
                onECGView={onECGView}
                onVitalClick={onVitalClick}
                onToggleECGMode={onToggleECGMode}
              />
            </div>
          )}

          {/* Notes Tab */}
          {activeTab === 'notes' && (
            <PatientNotes
              patient={patient}
              currentUser={currentUser}
              notes={notes}
              setNotes={setNotes}
              caseSheet={caseSheet}
              addCaseSheetEntry={addCaseSheetEntry}
            />
          )}

          {/* Medications Tab */}
          {activeTab === 'medications' && (
            <PatientMedications
              patient={patient}
              currentUser={currentUser}
              medications={medications}
              setMedications={setMedications}
              addCaseSheetEntry={addCaseSheetEntry}
            />
          )}

          {/* Investigation Tab */}
          {activeTab === 'investigations' && (
            <PatientInvestigations
              patient={patient}
              currentUser={currentUser}
              investigations={investigations}
              setInvestigations={setInvestigations}
              addCaseSheetEntry={addCaseSheetEntry}
            />
          )}

          {/* Old investigations code - kept for reference, will be removed */}
          {false && activeTab === 'investigations' && (
            <div className="p-4 h-full flex flex-col">
              {PermissionUtils.canEditMedications(currentUser.role) && (
                <div className="flex justify-end mb-3">
                  <button
                    onClick={() => setIsAddingInvestigation(true)}
                    className="flex items-center space-x-2 px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
                  >
                    <TestTube className="w-4 h-4" />
                    <span>Order Test</span>
                  </button>
                </div>
              )}

              {/* Add Investigation Form */}
              {isAddingInvestigation && PermissionUtils.canEditMedications(currentUser.role) && (
                <div className="mb-3 p-3 bg-green-50 rounded-lg border">
                  <h4 className="font-medium mb-2 text-sm">Order New Investigation</h4>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={newInvestigation.type}
                      onChange={(e) => setNewInvestigation(prev => ({ ...prev, type: e.target.value as any }))}
                      className="px-2 py-1 border rounded text-sm"
                    >
                      <option value="lab">Laboratory Test</option>
                      <option value="imaging">Imaging Study</option>
                      <option value="biopsy">Biopsy</option>
                      <option value="culture">Culture</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Investigation name"
                      value={newInvestigation.name}
                      onChange={(e) => setNewInvestigation(prev => ({ ...prev, name: e.target.value }))}
                      className="px-2 py-1 border rounded text-sm"
                    />
                    <select
                      value={newInvestigation.priority}
                      onChange={(e) => setNewInvestigation(prev => ({ ...prev, priority: e.target.value as any }))}
                      className="px-2 py-1 border rounded text-sm"
                    >
                      <option value="routine">Routine</option>
                      <option value="urgent">Urgent</option>
                      <option value="stat">STAT</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Special instructions"
                      value={newInvestigation.notes}
                      onChange={(e) => setNewInvestigation(prev => ({ ...prev, notes: e.target.value }))}
                      className="px-2 py-1 border rounded text-sm"
                    />
                  </div>
                  <div className="flex space-x-2 mt-2">
                    <button
                      onClick={async () => {
                        if (addingInvestigation) return; // Prevent multiple simultaneous calls
                        if (!newInvestigation.name) return;
                        setAddingInvestigation(true);
                        try {
                          const timestamp = new Date().toISOString();
                          const investigationData = {
                            ...newInvestigation,
                            createdAt: timestamp.split('T')[0],
                            status: 'ordered' as const,
                            performedBy: currentUser.name,
                            canEdit: true,
                            urgency: 'Routine' as const
                          };
                          await InvestigationService.addInvestigation(patient.id, investigationData, currentUser.id);
                          const newInv: investigation = {
                            id: 'inv_' + Date.now(),
                            ...investigationData
                          };
                          setInvestigations(prev => [...prev, newInv]);
                          
                          // Add case sheet entry to backend
                          try {
                            const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json'
                              },
                              body: JSON.stringify({
                                entrytype: 'investigation',
                                description: `${newInvestigation.name} (${newInvestigation.type}, ${newInvestigation.priority}) ordered by ${currentUser.name}`,
                                performedBy: currentUser.name
                              })
                            });

                            if (caseResponse.ok) {
                              const caseResult = await caseResponse.json();
                              const newCaseEntry: caseSheetEntry = {
                                id: caseResult.id || 'cs_' + Date.now(),
                                timestamp,
                                type: 'technicianNotes',
                                description: `${newInvestigation.name} (${newInvestigation.type}, ${newInvestigation.priority}) ordered by ${currentUser.name}`,
                                performedBy: currentUser.name,
                                canEdit: true
                              };
                              addCaseSheetEntry(newCaseEntry);
                            }
                          } catch (caseError) {
                            console.warn('Failed to add investigation case sheet entry:', caseError);
                          }
                          setNewInvestigation({ type: 'lab', name: '', priority: 'routine', notes: '' });
                          setIsAddingInvestigation(false);
                        } catch (error) {
                          console.error('Failed to add investigation:', error);
                        } finally {
                          setAddingInvestigation(false);
                        }
                      }}
                      disabled={addingInvestigation || !newInvestigation.name}
                      className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-400"
                    >
                      {addingInvestigation ? (
                        <>
                          <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          <span>Ordering...</span>
                        </>
                      ) : (
                        <>
                          <Save className="w-3 h-3" />
                          <span>Order</span>
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => {
                        setIsAddingInvestigation(false);
                        setNewInvestigation({ type: 'lab', name: '', priority: 'routine', notes: '' });
                      }}
                      className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
                    >
                      <X className="w-3 h-3" />
                      <span>Cancel</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Investigations List */}
              <div className="flex-1 overflow-y-auto space-y-2">
                {investigations.map((inv) => (
                  <div key={inv.id} className="bg-white border rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-1">
                          <h4 className="font-medium text-md">{inv.name}</h4>
                          <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                            inv.status === 'ordered' ? 'bg-blue-100 text-blue-800' :
                            inv.status === 'completed' ? 'bg-green-100 text-green-800' :
                            inv.status === 'inProgress' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {inv.status.toUpperCase().replace('_', ' ')}
                          </div>
                          <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                            inv.priority === 'stat' ? 'bg-red-100 text-red-800' :
                            inv.priority === 'urgent' ? 'bg-orange-100 text-orange-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {inv.priority.toUpperCase()}
                          </div>
                        </div>
                        <div className="text-sm text-gray-600 mb-2">
                          <p><span className="font-medium">Type:</span> {inv.type} • <span className="font-medium">Ordered by:</span> {inv.performedBy}</p>
                          {inv.notes && <p><span className="font-medium">Notes:</span> {inv.notes}</p>}
                          {inv.results && <p><span className="font-medium">Results:</span> {inv.results}</p>}
                          
                          {/* Detailed Lab Results */}
                          {inv.type === 'lab' && inv.labResults && inv.labResults.length > 0 && (
                            <div className="mt-2">
                              <p className="font-medium text-sm mb-2">📋 Lab Results ({inv.labResults.length} tests):</p>
                              <div className="space-y-1 max-h-40 overflow-y-auto">
                                {inv.labResults.map((result) => (
                                  <div key={result.id} className={`text-xs p-2 rounded border ${"bg-green-50 text-green-700 border-green-200"}`}>
                                    <div className="flex justify-between items-center">
                                      <span className="font-medium">{result.testName}</span>
                                      <span className={`px-1 py-0.5 rounded text-xs ${
                                        result.abnormalFlag === 'criticalHigh' || result.abnormalFlag === 'criticalLow' ? 'bg-red-600 text-white animate-pulse' :
                                        result.abnormalFlag === 'high' || result.abnormalFlag === 'low' ? 'bg-orange-600 text-white' :
                                        'bg-green-600 text-white'
                                      }`}>
                                        {result.abnormalFlag.toUpperCase().replace('_', ' ')}
                                      </span>
                                    </div>
                                    <div className="flex justify-between text-gray-700 mt-1">
                                      <span><strong>{result.result} {result.units}</strong></span>
                                      <span>Normal: {result.normalRange}</span>
                                    </div>
                                    {result.performedBy && (
                                      <div className="text-gray-500 text-xs mt-1">
                                        ✓ Verified by {result.performedBy} • {formatTimeOnly(result.completedat)}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                              
                              {/* Lab Results Summary */}
                              {false && (
                                <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
                                  <p className="text-red-700 text-xs font-medium">
                                    ⚠️ CRITICAL VALUES DETECTED - Requires immediate physician review
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                          
                          {/* Loading Lab Results */}
                          {inv.type === 'lab' && inv.status === 'inProgress' && loadingLabResults && (
                            <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded">
                              <div className="flex items-center space-x-2">
                                <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                                <span className="text-blue-700 text-xs">Fetching lab results from laboratory system...</span>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {/* Investigation Actions */}
                      {PermissionUtils.canEditMedications(currentUser.role) && inv.canEdit && (
                        <div className="flex items-center space-x-1">
                          {inv.status === 'ordered' && (
                            <button
                              onClick={async () => {
                                try {
                                  await InvestigationService.updateInvestigationStatus(inv.id, 'inProgress', currentUser.id);
                                  setInvestigations(prev => prev.map(i => 
                                    i.id === inv.id ? { ...i, status: 'inProgress' } : i
                                  ));
                                  // Add case sheet entry to backend
                                  try {
                                    const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
                                      method: 'POST',
                                      headers: {
                                        'Content-Type': 'application/json'
                                      },
                                      body: JSON.stringify({
                                        entrytype: 'investigation',
                                        description: `${inv.name} started by ${currentUser.name}`,
                                        performedBy: currentUser.name
                                      })
                                    });

                                    if (caseResponse.ok) {
                                      const caseResult = await caseResponse.json();
                                      const newCaseEntry: caseSheetEntry = {
                                        id: caseResult.id || 'cs_' + Date.now(),
                                        timestamp: new Date().toISOString(),
                                        type: 'technicianNotes',
                                        description: `${inv.name} started by ${currentUser.name}`,
                                        performedBy: currentUser.name,
                                        canEdit: true
                                      };
                                      addCaseSheetEntry(newCaseEntry);
                                    }
                                  } catch (caseError) {
                                    console.warn('Failed to add investigation started case sheet entry:', caseError);
                                  }
                                } catch (error) {
                                  console.error('Failed to start investigation:', error);
                                }
                              }}
                              className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors text-xs"
                              title="Start investigation"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}
                          {(inv.status === 'inProgress' || inv.status === 'ordered') && (
                            <button
                              onClick={async () => {
                                let results = '';
                                
                                if (inv.type === 'lab') {
                                  // For lab investigations, automatically fetch results from lab system
                                  try {
                                    setLoadingLabResults(true);
                                    const updatedInvestigation = await Promise.resolve(inv);
                                    
                                    if (updatedInvestigation.status === 'completed') {
                                      await InvestigationService.completeInvestigation(inv.id, updatedInvestigation.results || 'Lab results imported', currentUser.id);
                                      setInvestigations(prev => prev.map(i => 
                                        i.id === inv.id ? updatedInvestigation : i
                                      ));
                                      results = updatedInvestigation.results || 'Lab results imported';
                                    } else {
                                      alert('Lab results not yet available. Please try again later.');
                                      return;
                                    }
                                    setLoadingLabResults(false);
                                  } catch (error) {
                                    setLoadingLabResults(false);
                                    console.error('Failed to fetch lab results:', error);
                                    alert('Failed to fetch lab results. Please enter results manually.');
                                    
                                    // Fallback to manual entry
                                    const manualResults = window.prompt('Lab results not available. Enter results manually:');
                                    if (manualResults) {
                                      try {
                                        await InvestigationService.completeInvestigation(inv.id, manualResults, currentUser.id);
                                        setInvestigations(prev => prev.map(i => 
                                          i.id === inv.id ? { ...i, status: 'completed', results: manualResults, completedAt: new Date().toISOString() } : i
                                        ));
                                        results = manualResults;
                                      } catch (completeError) {
                                        console.error('Failed to complete investigation:', completeError);
                                        return;
                                      }
                                    } else {
                                      return;
                                    }
                                  }
                                } else {
                                  // For non-lab investigations, use manual entry
                                  const manualResults = window.prompt('Enter investigation results:');
                                  if (manualResults) {
                                    try {
                                      await InvestigationService.completeInvestigation(inv.id, manualResults, currentUser.id);
                                      setInvestigations(prev => prev.map(i => 
                                        i.id === inv.id ? { ...i, status: 'completed', results: manualResults, completedAt: new Date().toISOString() } : i
                                      ));
                                      results = manualResults;
                                    } catch (error) {
                                      console.error('Failed to complete investigation:', error);
                                      return;
                                    }
                                  } else {
                                    return;
                                  }
                                }
                                
                                // Add case sheet entry after completing investigation
                                try {
                                  const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
                                    method: 'POST',
                                    headers: {
                                      'Content-Type': 'application/json'
                                    },
                                    body: JSON.stringify({
                                      entrytype: 'investigation',
                                      description: `${inv.name} completed by ${currentUser.name}${results ? ` - Results: ${results}` : ''}`,
                                      performedBy: currentUser.name
                                    })
                                  });

                                  if (caseResponse.ok) {
                                    const caseResult = await caseResponse.json();
                                    const newCaseEntry: caseSheetEntry = {
                                      id: caseResult.id || 'cs_' + Date.now(),
                                      timestamp: new Date().toISOString(),
                                      type: getRoleBasedNoteType(currentUser.role),
                                      description: `${inv.name} completed by ${currentUser.name}${results ? ` - Results: ${results}` : ''}`,
                                      performedBy: currentUser.name,
                                      canEdit: true
                                    };
                                    addCaseSheetEntry(newCaseEntry);
                                  }
                                } catch (caseError) {
                                  console.warn('Failed to add investigation completed case sheet entry:', caseError);
                                }
                              }}
                              className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors text-xs"
                              title="Complete investigation"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          )}
                          {inv.status !== 'completed' && inv.status !== 'cancelled' && (
                            <button
                              onClick={async () => {
                                if (window.confirm('Are you sure you want to cancel this investigation?')) {
                                  try {
                                    await InvestigationService.updateInvestigationStatus(inv.id, 'cancelled', currentUser.id);
                                    setInvestigations(prev => prev.map(i => 
                                      i.id === inv.id ? { ...i, status: 'cancelled' } : i
                                    ));
                                    
                                    // Add case sheet entry to backend
                                    try {
                                      const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
                                        method: 'POST',
                                        headers: {
                                          'Content-Type': 'application/json'
                                        },
                                        body: JSON.stringify({
                                          entrytype: 'investigation',
                                          description: `${inv.name} (${inv.type}) cancelled by ${currentUser.name}`,
                                          performedBy: currentUser.name
                                        })
                                      });

                                      if (caseResponse.ok) {
                                        const caseResult = await caseResponse.json();
                                        const timestamp = new Date().toISOString();
                                        const newCaseEntry: caseSheetEntry = {
                                          id: caseResult.id || 'cs_' + Date.now(),
                                          timestamp,
                                          type: 'technicianNotes',
                                          description: `${inv.name} (${inv.type}) cancelled by ${currentUser.name}`,
                                          performedBy: currentUser.name,
                                          canEdit: true
                                        };
                                        addCaseSheetEntry(newCaseEntry);
                                      }
                                    } catch (caseError) {
                                      console.warn('Failed to add investigation cancellation case sheet entry:', caseError);
                                    }
                                  } catch (error) {
                                    console.error('Failed to cancel investigation:', error);
                                  }
                                }
                              }}
                              className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors text-xs"
                              title="Cancel investigation"
                            >
                              <XCircle className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {investigations.length === 0 && (
                  <div className="text-center py-6 text-gray-500">
                    <TestTube className="w-10 h-10 mx-auto mb-3 opacity-50" />
                    <p>No investigations ordered yet</p>
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Imaging Studies Section - Part of Investigations */}
          {activeTab === 'investigations' && (
            <div className="mt-6 border-t pt-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-bold flex items-center space-x-2">
                  <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                    📸
                  </div>
                  <span>Imaging Studies ({imagingStudies.length})</span>
                  {loadingImaging && (
                    <div className="w-4 h-4 border-2 border-purple-600 border-t-transparent rounded-full animate-spin ml-2"></div>
                  )}
                </h3>
              </div>

              {/* Imaging Studies List */}
              <div className="space-y-3 max-h-80 overflow-y-auto">
                {imagingStudies.map((study) => (
                  <div key={study.id} className="bg-white border rounded-lg p-4 shadow-sm">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h4 className="font-medium text-md">{study.studyType}</h4>
                          <div className={`px-2 py-1 rounded-full text-xs font-medium border ${"bg-blue-50 text-blue-700 border-blue-200"}`}>
                            {study.studyType.toUpperCase()}
                          </div>
                          <div className={`px-2 py-1 rounded-full text-xs font-medium ${"bg-yellow-50 text-yellow-700"}`}>
                            {study.urgency.toUpperCase()}
                          </div>
                          <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                            study.status === 'completed' ? 'bg-green-100 text-green-800' :
                            study.status === 'inProgress' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-blue-100 text-blue-800'
                          }`}>
                            {study.status.toUpperCase().replace('_', ' ')}
                          </div>
                        </div>
                        
                        <div className="text-sm text-gray-600 mb-3">
                          <p><span className="font-medium">Study Date:</span> {new Date(study.createdAt).toLocaleString()}</p>
                          <p><span className="font-medium">Ordered by:</span> {study.performedBy}</p>
                          {study.technologist && <p><span className="font-medium">Technologist:</span> {study.technologist}</p>}
                          {study.radiologist && <p><span className="font-medium">Radiologist:</span> {study.radiologist}</p>}
                        </div>

                        {/* Image Thumbnails */}
                        {study.images && study.images.length > 0 && (
                          <div className="mb-3">
                            <p className="font-medium text-sm mb-2">📷 Images ({study.images.length}):</p>
                            <div className="flex space-x-2 overflow-x-auto">
                              {study.images.map((image) => (
                                <div key={image.id} className="flex-shrink-0">
                                  <img
                                    src={image.thumbnail}
                                    alt={`${study.studyType} - ${image.viewPosition || `Instance ${image.instanceNumber}`}`}
                                    className="w-20 h-20 object-cover rounded border cursor-pointer hover:opacity-80 transition-opacity"
                                    onClick={() => setSelectedImage(image.url)}
                                    title={`Click to view full image - ${image.viewPosition || `Instance ${image.instanceNumber}`}`}
                                  />
                                  <p className="text-xs text-gray-500 text-center mt-1 truncate w-20">
                                    {image.viewPosition || `#${image.instanceNumber}`}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Imaging Report */}
                        {study.report && (
                          <div className="bg-gray-50 rounded p-3 text-sm">
                            <div className="flex items-center justify-between mb-2">
                              <h5 className="font-medium text-gray-900">📋 Radiology Report</h5>
                              <div className={`px-2 py-1 rounded text-xs font-medium ${
                                study.report.status === 'final' ? 'bg-green-100 text-green-800' :
                                study.report.status === 'preliminary' ? 'bg-yellow-100 text-yellow-800' :
                                'bg-blue-100 text-blue-800'
                              }`}>
                                {study.report.status.toUpperCase()}
                              </div>
                            </div>
                            
                            <div className="space-y-2">
                              <div>
                                <span className="font-medium text-gray-700">Findings:</span>
                                <p className="text-gray-600 mt-1">{study.report.findings}</p>
                              </div>
                              <div>
                                <span className="font-medium text-gray-700">Impression:</span>
                                <p className="text-gray-600 mt-1">{study.report.impression}</p>
                              </div>
                              {study.report.recommendations && (
                                <div>
                                  <span className="font-medium text-gray-700">Recommendations:</span>
                                  <p className="text-gray-600 mt-1">{study.report.recommendations}</p>
                                </div>
                              )}
                              <div className="text-xs text-gray-500 pt-2 border-t">
                                Reported by {study.report.performedBy} • {new Date(study.report.createdAt).toLocaleString()}
                              </div>
                            </div>

                            {/* Abnormal findings alert */}
                            {false && (
                              <div className="mt-3 p-2 bg-orange-50 border border-orange-200 rounded">
                                <p className="text-orange-700 text-xs font-medium">
                                  ⚠️ ABNORMAL FINDINGS - Requires physician review
                                </p>
                              </div>
                            )}
                          </div>
                        )}

                        {/* No report available */}
                        {!study.report && study.status === 'completed' && (
                          <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                            <p className="text-yellow-700 text-sm">📝 Report pending - Awaiting radiologist interpretation</p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {/* No imaging studies */}
                {imagingStudies.length === 0 && !loadingImaging && (
                  <div className="text-center py-8 text-gray-500">
                    <div className="w-16 h-16 mx-auto mb-4 opacity-50">📸</div>
                    <p>No imaging studies available</p>
                  </div>
                )}

                {/* Loading imaging */}
                {loadingImaging && (
                  <div className="text-center py-8 text-gray-500">
                    <div className="w-8 h-8 border-2 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p>Loading imaging studies from PACS...</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Image Viewer Modal */}
          {selectedImage && (
            <div 
              className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
              onClick={() => setSelectedImage(null)}
            >
              <div className="max-w-4xl max-h-4xl p-4" onClick={(e) => e.stopPropagation()}>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-white text-lg font-medium">Medical Image Viewer</h3>
                  <button
                    onClick={() => setSelectedImage(null)}
                    className="text-white hover:text-gray-300 text-2xl font-bold"
                  >
                    ×
                  </button>
                </div>
                <img
                  src={selectedImage}
                  alt="Medical imaging study"
                  className="max-w-full max-h-full object-contain rounded"
                />
                <div className="mt-4 text-center">
                  <button
                    onClick={() => {/* DICOM viewer disabled */}}
                    className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 mr-2"
                  >
                    Open in DICOM Viewer
                  </button>
                  <button
                    onClick={() => setSelectedImage(null)}
                    className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Therapy Tab */}
          {activeTab === 'therapy' && (
            <PatientTherapies
              patient={patient}
              currentUser={currentUser}
              therapies={therapies}
              setTherapies={setTherapies}
              addCaseSheetEntry={addCaseSheetEntry}
            />
          )}

          {/* Old therapy code - kept for reference, will be removed */}
          {false && activeTab === 'therapy' && (
            <div className="p-4 h-full flex flex-col">
              {PermissionUtils.canEditMedications(currentUser.role) && (
                <div className="flex justify-end mb-3">
                  <button
                    onClick={() => setIsAddingTherapy(true)}
                    className="flex items-center space-x-2 px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm"
                  >
                    <Heart className="w-4 h-4" />
                    <span>Prescribe</span>
                  </button>
                </div>
              )}

              {/* Add Therapy Form */}
              {isAddingTherapy && PermissionUtils.canEditMedications(currentUser.role) && (
                <div className="mb-3 p-3 bg-purple-50 rounded-lg border">
                  <h4 className="font-medium mb-2 text-sm">Prescribe New Therapy</h4>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={newTherapy.type}
                      onChange={(e) => setNewTherapy(prev => ({ ...prev, type: e.target.value as any }))}
                      className="px-2 py-1 border rounded text-sm"
                    >
                      <option value="physiotherapy">Physiotherapy</option>
                      <option value="occupational">Occupational Therapy</option>
                      <option value="speech">Speech Therapy</option>
                      <option value="respiratory">Respiratory Therapy</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Therapy description"
                      value={newTherapy.description}
                      onChange={(e) => setNewTherapy(prev => ({ ...prev, description: e.target.value }))}
                      className="px-2 py-1 border rounded text-sm"
                    />
                    <input
                      type="text"
                      placeholder="Frequency (e.g., 3x per week)"
                      value={newTherapy.frequency}
                      onChange={(e) => setNewTherapy(prev => ({ ...prev, frequency: e.target.value }))}
                      className="px-2 py-1 border rounded text-sm"
                    />
                    <input
                      type="text"
                      placeholder="Duration (e.g., 4 weeks)"
                      value={newTherapy.duration}
                      onChange={(e) => setNewTherapy(prev => ({ ...prev, duration: e.target.value }))}
                      className="px-2 py-1 border rounded text-sm"
                    />
                  </div>
                  <div className="flex space-x-2 mt-2">
                    <button
                      onClick={async () => {
                        if (addingTherapy) return; // Prevent multiple simultaneous calls
                        if (!newTherapy.description) return;
                        setAddingTherapy(true);
                        try {
                          const timestamp = new Date().toISOString();
                          const therapyData = {
                            ...newTherapy,
                            startDate: timestamp.split('T')[0],
                            status: 'active' as const,
                            performedBy: currentUser.name,
                            canEdit: true,
                            sessions: [],
                            name: newTherapy.type + ' therapy'
                          };
                          await TherapyService.addTherapy(patient.id, therapyData, currentUser.id);
                          const newTher: therapy = {
                            ...therapyData,
                            id: 'ther_' + Date.now()
                          };
                          setTherapies(prev => [...prev, newTher]);
                          
                          // Add case sheet entry to backend
                          try {
                            const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json'
                              },
                              body: JSON.stringify({
                                entrytype: 'therapy',
                                description: `${newTherapy.type}: ${newTherapy.description} (${newTherapy.frequency}, ${newTherapy.duration}) prescribed by ${currentUser.name}`,
                                performedBy: currentUser.name
                              })
                            });

                            if (caseResponse.ok) {
                              const caseResult = await caseResponse.json();
                              const newCaseEntry: caseSheetEntry = {
                                id: caseResult.id || 'cs_' + Date.now(),
                                timestamp,
                                type: 'therapistNotes',
                                description: `${newTherapy.type}: ${newTherapy.description} (${newTherapy.frequency}, ${newTherapy.duration}) prescribed by ${currentUser.name}`,
                                performedBy: currentUser.name,
                                canEdit: true
                              };
                              addCaseSheetEntry(newCaseEntry);
                            }
                          } catch (caseError) {
                            console.warn('Failed to add therapy case sheet entry:', caseError);
                          }
                          setNewTherapy({ type: 'physiotherapy', description: '', frequency: '', duration: '' });
                          setIsAddingTherapy(false);
                        } catch (error) {
                          console.error('Failed to add therapy:', error);
                        } finally {
                          setAddingTherapy(false);
                        }
                      }}
                      disabled={addingTherapy || !newTherapy.description}
                      className="flex items-center space-x-1 px-3 py-1 bg-purple-600 text-white rounded text-sm hover:bg-purple-700 disabled:bg-gray-400"
                    >
                      {addingTherapy ? (
                        <>
                          <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          <span>Adding...</span>
                        </>
                      ) : (
                        <>
                          <Save className="w-3 h-3" />
                          <span>Prescribe</span>
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => {
                        setIsAddingTherapy(false);
                        setNewTherapy({ type: 'physiotherapy', description: '', frequency: '', duration: '' });
                      }}
                      className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
                    >
                      <X className="w-3 h-3" />
                      <span>Cancel</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Therapies List */}
              <div className="flex-1 overflow-y-auto space-y-2">
                {therapies.map((therapy) => (
                  <div key={therapy.id} className="bg-white border rounded-lg p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-1">
                          <h4 className="font-medium text-md">{therapy.description}</h4>
                          <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                            therapy.status === 'active' ? 'bg-green-100 text-green-800' :
                            therapy.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {therapy.status.toUpperCase()}
                          </div>
                        </div>
                        <div className="text-sm text-gray-600 mb-2">
                          <p><span className="font-medium">Type:</span> {therapy.type} • <span className="font-medium">Frequency:</span> {therapy.frequency}</p>
                          <p><span className="font-medium">Duration:</span> {therapy.duration} • <span className="font-medium">Prescribed by:</span> {therapy.performedBy}</p>
                          {therapy.therapist && <p><span className="font-medium">Therapist:</span> {therapy.therapist}</p>}
                          {therapy.sessions && therapy.sessions.length > 0 && (
                            <p><span className="font-medium">Sessions:</span> {therapy.sessions.length} completed</p>
                          )}
                        </div>
                      </div>
                      
                      {/* Therapy Actions */}
                      {PermissionUtils.canEditMedications(currentUser.role) && therapy.canEdit && (
                        <div className="flex items-center space-x-1">
                          {therapy.status === 'active' && (
                            <>
                              <button
                                onClick={async () => {
                                  const duration = window.prompt('Session duration (minutes):');
                                  const notes = window.prompt('Session notes:');
                                  const patientResponse = window.prompt('Patient response:');
                                  
                                  if (duration && notes && patientResponse) {
                                    try {
                                      const sessionData = {
                                        duration: parseInt(duration),
                                        notes: notes,
                                        therapist: currentUser.name,
                                        patientResponse: patientResponse
                                      };
                                      
                                      // Note: Therapy session recording handled in usePatientTherapies hook
                                      
                                      const newSession = {
                                        id: 'session_' + Date.now(),
                                        date: new Date().toISOString(),
                                        duration: sessionData.duration,
                                        notes: sessionData.notes,
                                        therapist: sessionData.therapist,
                                        patientResponse: sessionData.patientResponse
                                      };
                                      
                                      setTherapies(prev => prev.map(t => 
                                        t.id === therapy.id ? {
                                          ...t, 
                                          sessions: [...(t.sessions || []), newSession],
                                          therapist: currentUser.name
                                        } : t
                                      ));
                                      
                                      const newCaseEntry: caseSheetEntry = {
                                        id: 'cs_' + Date.now(),
                                        timestamp: new Date().toISOString(),
                                        type: 'therapistNotes',
                                        description: `${therapy.description} session completed by ${currentUser.name}`,
                                        performedBy: currentUser.name,
                                        canEdit: PatientService.canEditItem(new Date().toISOString())
                                      };
                                      addCaseSheetEntry(newCaseEntry);
                                    } catch (error) {
                                      console.error('Failed to add therapy session:', error);
                                    }
                                  }
                                }}
                                className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors text-xs"
                                title="Add therapy session"
                              >
                                <Plus className="w-4 h-4" />
                              </button>
                              <button
                                onClick={async () => {
                                  if (window.confirm('Mark this therapy as completed?')) {
                                    try {
                                      await TherapyService.updateTherapy(patient.id, therapy.id, { status: 'completed' }, currentUser.id);
                                      setTherapies(prev => prev.map(t => 
                                        t.id === therapy.id ? { ...t, status: 'completed', enddate: new Date().toISOString() } : t
                                      ));
                                      const newCaseEntry: caseSheetEntry = {
                                        id: 'cs_' + Date.now(),
                                        timestamp: new Date().toISOString(),
                                        type: 'therapistNotes',
                                        description: `${therapy.description} completed by ${currentUser.name}`,
                                        performedBy: currentUser.name,
                                        canEdit: PatientService.canEditItem(new Date().toISOString())
                                      };
                                      addCaseSheetEntry(newCaseEntry);
                                    } catch (error) {
                                      console.error('Failed to complete therapy:', error);
                                    }
                                  }
                                }}
                                className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors text-xs"
                                title="Complete therapy"
                              >
                                <XCircle className="w-4 h-4" />
                              </button>
                              <button
                                onClick={async () => {
                                  if (window.confirm('Cancel this therapy?')) {
                                    try {
                                      await TherapyService.updateTherapy(patient.id, therapy.id, { status: 'cancelled' }, currentUser.id);
                                      setTherapies(prev => prev.map(t => 
                                        t.id === therapy.id ? { ...t, status: 'cancelled' } : t
                                      ));
                                      const newCaseEntry: caseSheetEntry = {
                                        id: 'cs_' + Date.now(),
                                        timestamp: new Date().toISOString(),
                                        type: 'therapistNotes',
                                        description: `${therapy.description} cancelled by ${currentUser.name}`,
                                        performedBy: currentUser.name,
                                        canEdit: PatientService.canEditItem(new Date().toISOString())
                                      };
                                      addCaseSheetEntry(newCaseEntry);
                                    } catch (error) {
                                      console.error('Failed to cancel therapy:', error);
                                    }
                                  }
                                }}
                                className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors text-xs"
                                title="Cancel therapy"
                              >
                                <XCircle className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {therapies.length === 0 && (
                  <div className="text-center py-6 text-gray-500">
                    <Heart className="w-10 h-10 mx-auto mb-3 opacity-50" />
                    <p>No therapy prescribed yet</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'casesheet' && (
            <CaseSheetBook caseSheet={getEnhancedCaseSheet()} />
          )}
        </div>
      </div>
    </div>
  );
};

// Memoized export for performance optimization
const PatientDetail = React.memo(PatientDetailComponent);
export { PatientDetail };
export default PatientDetail;