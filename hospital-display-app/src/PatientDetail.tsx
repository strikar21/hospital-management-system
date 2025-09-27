import React, { useState, useEffect, useCallback } from 'react';
import { 
  ChevronLeft, Heart, Activity, Thermometer, Droplets, Zap, AlertTriangle, 
  Plus, Edit, Save, X, Pause, Play, StopCircle, FileText, Clock, User as UserIcon,
  TestTube, Stethoscope, Shield, CheckCircle, XCircle, MessageCircle,
  Send
} from 'lucide-react';
import { patient, user, medication, investigation, therapy, caseSheetEntry, alert as alertType, noteComment, clinicalAlert, labResult, imagingStudy } from './types';
import {
  getStatusColor, getVitalStatusColor, getMedicationStatusColor, formatTimeOnly, formatDateTime
} from './utils';
import { MedicalUtils } from './utils/medicalUtils';
import { PermissionUtils } from './utils/permissionUtils';
import { PatientService, MedicationService, InvestigationService, TherapyService } from './services';
import CaseSheetBook from './CaseSheetBook';


interface PatientDetailProps {
  patient: patient;
  currentUser: user;
  onClose: () => void;
  onVitalClick: (patient: patient, vitalType: string) => void;
  onECGView?: (patient: patient) => void;
  onToggleECGMode?: (patient: patient) => void;
  onPatientDischarge?: (patientId: string) => void;
}

export const PatientDetail: React.FC<PatientDetailProps> = ({
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
  
  // Function to determine staff role type based on user role
  const getRoleBasedNoteType = (userRole: string): 'doctorNotes' | 'nursingNotes' | 'therapistNotes' | 'technicianNotes' | 'pharmacyNotes' | 'otherNotes' => {
    switch (userRole) {
      case 'Doctor':
      // 'Senior Consultant' role not available in current interface
        return 'doctorNotes';
      case 'Nurse':
      // 'Senior Nurse' role not available in current interface
        return 'nursingNotes';
      case 'Technician':
        return 'technicianNotes';
      case 'Admin':
      case 'Administrator':
      case 'Master Admin':
      case 'Provisioner':
        return 'otherNotes';
      default:
        return 'otherNotes';
    }
  };
  
  const [activeTab, setActiveTab] = useState<'overview' | 'medications' | 'investigations' | 'therapy' | 'notes' | 'casesheet'>('overview');
  const [medications, setMedications] = useState<medication[]>(patient.medications || []);
  const [investigations, setInvestigations] = useState<investigation[]>(patient.investigations || []);
  const [therapies, setTherapies] = useState<therapy[]>(patient.therapies || []);
  const [notes, setNotes] = useState<noteComment[]>(patient.notes || []);
  const [alerts, setAlerts] = useState<alertType[]>(patient.alerts || []);
  const [caseSheet, setCaseSheet] = useState<caseSheetEntry[]>(patient.caseSheet || []);
  const [isEcgMode, setIsECGMode] = useState<boolean>(patient.vitals?.isEcgMode ?? true); // Local state for simulation
  
  // Notes state
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [newNoteContent, setNewNoteContent] = useState('');
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editingNoteContent, setEditingNoteContent] = useState('');
  
  // New medication form
  const [isAddingMedication, setIsAddingMedication] = useState(false);
  const [newMedication, setNewMedication] = useState({
    name: '', dosage: '', frequency: '', route: 'PO', duration: ''
  });
  
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
  const [clinicalAlerts, setClinicalAlerts] = useState<clinicalAlert[]>([]);
  const [showClinicalAlerts, setShowClinicalAlerts] = useState(false);
  
  // Lab Integration
  const [labResults, setLabResults] = useState<labResult[]>([]);
  const [loadingLabResults, setLoadingLabResults] = useState(false);
  
  // Imaging/PACS Integration
  const [imagingStudies, setImagingStudies] = useState<imagingStudy[]>([]);
  const [loadingImaging, setLoadingImaging] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  

  // Loading states
  const [addingNote, setAddingNote] = useState(false);
  const [editingNote, setEditingNote] = useState(false);
  const [acknowledgingAlert, setAcknowledgingAlert] = useState<string | null>(null);
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

  useEffect(() => {
    setIsECGMode(patient.vitals?.isEcgMode || false);
  }, [patient.vitals?.isEcgMode]);

  // Sync alerts and auto-hide acknowledged ones after 3 seconds
  useEffect(() => {
    setAlerts(patient.alerts || []);
    
    // Auto-hide acknowledged alerts after 3 seconds
    const acknowledgedAlerts = (patient.alerts || []).filter(alert => alert.isAcknowledged);
    if (acknowledgedAlerts.length > 0) {
      const timer = setTimeout(() => {
        setAlerts(prev => prev.filter(alert => !alert.isAcknowledged));
      }, 3000);
      return () => clearTimeout(timer);
    }
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

  // Handle ECG/EEG toggle
  const handleToggleECGMode = (newMode: boolean) => {
    setIsECGMode(newMode); // Update local state for simulation
    if (onToggleECGMode) {
      const updatedPatient = {
        ...patient,
        vitals: {
          ...patient.vitals,
          isEcgMode: newMode
        }
      };
      onToggleECGMode(updatedPatient); // Call parent callback if provided
    }
  };

  // Handle Alert Acknowledgment - FIXED to auto-hide after acknowledgment
  const handleAcknowledgeAlert = async (alertId: string) => {
    setAcknowledgingAlert(alertId);
    try {
      await PatientService.acknowledgeAlert(patient.id, alertId, currentUser.id);
      
      setAlerts(prev => prev.map(alert =>
        alert.id === alertId ? {
          ...alert,
          isAcknowledged: true,
          performedBy: currentUser.id,           // Keep ID for system reference
          performedByName: currentUser.name,     // Store actual name
          performedByRole: currentUser.role,     // Store role (RN, MD, etc.)
          completedAt: new Date().toISOString()
        } : alert
      ));

      // Auto-hide acknowledged alert after 2 seconds
      setTimeout(() => {
        setAlerts(prev => prev.filter(alert => alert.id !== alertId));
      }, 2000);

      const alertMessage = alerts.find(a => a.id === alertId)?.message || 'Unknown Alert';
      const newCaseEntry: caseSheetEntry = {
        id: 'cs_' + Date.now(),
        timestamp: new Date().toISOString(),
        type: 'alertAcknowledged',
        description: `Alert acknowledged: "${alertMessage}" by ${currentUser.name} (${currentUser.role})`,
        performedBy: currentUser.name,
        canEdit: PatientService.canEditItem(new Date().toISOString())
      };
      addCaseSheetEntry(newCaseEntry);
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
      alert('Failed to acknowledge alert. Please try again.');
    } finally {
      setAcknowledgingAlert(null);
    }
  };

  // Handle Add Note
  const handleAddNote = async () => {
    if (addingNote) return; // Prevent multiple simultaneous calls
    if (!newNoteContent.trim()) return;

    setAddingNote(true);
    try {
      await PatientService.addNoteComment(patient.id, newNoteContent.trim(), currentUser.id, currentUser.name, currentUser.role);
      
      const newNote: noteComment = {
        id: 'note_' + Date.now(),
        content: newNoteContent.trim(),
        authorId: currentUser.id,
        authorName: currentUser.name,
        authorRole: currentUser.role,
        timestamp: new Date().toISOString(),
        canEdit: true,
        isEdited: false
      };
      
      setNotes(prev => [...prev, newNote]);
      setNewNoteContent('');
      setIsAddingNote(false);

      // Add case sheet entry to backend
      try {
        const response = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            entrytype: 'note',
            description: `Note: "${newNoteContent.trim()}"`,
            performedBy: currentUser.name
          })
        });

        if (response.ok) {
          const result = await response.json();
          console.log('Case sheet entry added:', result);
          
          // Add to local state
          const newCaseEntry: caseSheetEntry = {
            id: result.id || 'cs_' + Date.now(),
            timestamp: new Date().toISOString(),
            type: getRoleBasedNoteType(currentUser.role),
            description: `Note: "${newNoteContent.trim()}"`,
            performedBy: currentUser.name,
            canEdit: true
          };
          addCaseSheetEntry(newCaseEntry);
        } else {
          console.warn('Failed to add case sheet entry, continuing without it');
        }
      } catch (error) {
        console.warn('Failed to add case sheet entry:', error);
      }
    } catch (error) {
      console.error('Failed to add note:', error);
      alert('Failed to add note. Please try again.');
    } finally {
      setAddingNote(false);
    }
  };

  // Handle Edit Note
  const handleEditNote = async (noteId: string) => {
    if (!editingNoteContent.trim()) return;

    setEditingNote(true);
    try {
      await PatientService.editNoteComment(patient.id, noteId, editingNoteContent.trim(), currentUser.id);
      
      setNotes(prev => prev.map(note => 
        note.id === noteId ? {
          ...note,
          content: editingNoteContent.trim(),
          editedAt: new Date().toISOString(),
          isEdited: true,
          canEdit: PatientService.canEditNote(note, currentUser.id)
        } : note
      ));
      
      setEditingNoteId(null);
      setEditingNoteContent('');

      const newCaseEntry: caseSheetEntry = {
        id: 'cs_' + Date.now(),
        timestamp: new Date().toISOString(),
        type: 'doctorNotes',
        description: `Note edited by ${currentUser.name}`,
        performedBy: currentUser.name,
        canEdit: PatientService.canEditItem(new Date().toISOString())
      };
      addCaseSheetEntry(newCaseEntry);
    } catch (error) {
      console.error('Failed to edit note:', error);
      alert('Failed to edit note. Please try again.');
    } finally {
      setEditingNote(false);
    }
  };

  const startEditingNote = (note: noteComment) => {
    setEditingNoteId(note.id);
    setEditingNoteContent(note.content);
  };

  const cancelEditingNote = () => {
    setEditingNoteId(null);
    setEditingNoteContent('');
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

  const handleMedicationStatusChange = async (medicationId: string, status: 'active' | 'stopped' | 'held') => {
    try {
      await MedicationService.updateMedication(patient.id, medicationId, status, currentUser.id);
      
      setMedications(prev => prev.map(med => 
        med.id === medicationId ? { 
          ...med, 
          status, 
          modifiedBy: currentUser.name, 
          updatedat: new Date().toISOString(),
          canEdit: PatientService.canEditItem(new Date().toISOString()),
          history: [...(med.history || []), {
            id: 'hist_' + Date.now(),
            action: status === 'active' ? 'resumed' : status,
            timestamp: new Date().toISOString(),
            performedBy: currentUser.name
          }]
        } : med
      ));
      
      const medication = medications.find(m => m.id === medicationId);
      if (medication) {
        const newCaseEntry: caseSheetEntry = {
          id: 'cs_' + Date.now(),
          timestamp: new Date().toISOString(),
          type: 'pharmacyNotes',
          description: `${medication.name} ${status} by ${currentUser.name}`,
          performedBy: currentUser.name,
          canEdit: PatientService.canEditItem(new Date().toISOString())
        };
        addCaseSheetEntry(newCaseEntry);
      }
    } catch (error) {
      console.error('Failed to update medication:', error);
      alert('Failed to update medication. Please try again.');
    }
  };

  // Get unacknowledged and acknowledged alerts - ONLY SHOW UNACKNOWLEDGED
  const unacknowledgedAlerts = alerts.filter(alert => !alert.isAcknowledged);
  const acknowledgedAlerts = alerts.filter(alert => alert.isAcknowledged);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: UserIcon },
    { id: 'medications', label: 'Medications', icon: Plus },
    { id: 'investigations', label: 'Investigations', icon: TestTube },
    { id: 'therapy', label: 'Therapy', icon: Stethoscope },
    { id: 'notes', label: 'Notes', icon: MessageCircle },
    { id: 'casesheet', label: 'Case Sheet', icon: FileText }
  ]; // All tabs visible to all roles - permissions handled within each tab
  
  console.log('📋 Available tabs:', tabs.map(t => t.label).join(', '));
  console.log('💊 Medications count in component:', medications.length);
  console.log('🧪 Investigations count in component:', investigations.length);

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
  
  console.log('🏃 Therapies count in component:', therapies.length);
  console.log('🧪 Lab results count:', labResults.length);
  console.log('🖼️ Imaging studies count:', imagingStudies.length);
  console.log('System ready');

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

        {/* Compact Alert Banner - ONLY UNACKNOWLEDGED ALERTS */}
        {unacknowledgedAlerts.length > 0 && (
          <div className="bg-red-100 border-b border-red-200 p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 text-red-600 animate-pulse" />
                <h3 className="text-sm font-bold text-red-800">⚠️ UNACKNOWLEDGED ALERTS ({unacknowledgedAlerts.length})</h3>
              </div>
              <button
                onClick={() => {
                  unacknowledgedAlerts.forEach(alert => {
                    handleAcknowledgeAlert(alert.id);
                  });
                }}
                disabled={acknowledgingAlert !== null}
                className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-green-400"
              >
                {acknowledgingAlert !== null ? (
                  <>
                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Acknowledging...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4" />
                    <span>Acknowledge All</span>
                  </>
                )}
              </button>
            </div>
            
            {/* Max 4 Alerts in 2x2 Grid */}
            <div className="grid grid-cols-2 gap-2">
              {unacknowledgedAlerts.slice(0, 4).map((alert) => (
                <div key={alert.id} className="flex items-center justify-between p-2 bg-white rounded border-l-4 border-red-500">
                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      alert.severity === 'critical' ? 'bg-red-600 animate-pulse' :
                      alert.severity === 'high' ? 'bg-orange-500' :
                      alert.severity === 'medium' ? 'bg-yellow-500' :
                      'bg-blue-500'
                    }`}></div>
                    <span className="text-xs text-red-700 font-medium truncate flex-1">{alert.message}</span>
                    <span className="text-xs text-gray-500 flex-shrink-0">
                      {formatTimeOnly(alert.timestamp)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Show remaining alerts count if more than 4 */}
            {unacknowledgedAlerts.length > 4 && (
              <div className="mt-2 text-center">
                <span className="text-xs text-red-700 bg-red-200 px-2 py-1 rounded">
                  +{unacknowledgedAlerts.length - 4} more alerts (showing first 4)
                </span>
              </div>
            )}
          </div>
        )}

        {/* Show acknowledged alerts briefly with auto-fade */}
        {acknowledgedAlerts.length > 0 && (
          <div className="bg-green-50 border-b border-green-200 p-3 animate-pulse">
            <h3 className="text-sm font-bold text-green-800 mb-2">
              ✅ ACKNOWLEDGED ALERTS ({acknowledgedAlerts.length}) - Will disappear shortly...
            </h3>
            <div className="space-y-1">
              {acknowledgedAlerts.slice(0, 2).map((alert) => (
                <div key={alert.id} className="flex items-center justify-between p-2 bg-white rounded border-l-4 border-green-500 opacity-75">
                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                    <div className="w-2 h-2 rounded-full bg-green-600"></div>
                    <span className="text-xs text-green-700 font-medium truncate flex-1">{alert.message}</span>
                  </div>
                  <div className="text-xs text-gray-600 flex-shrink-0">
                    by {alert.performedByName || `User ${alert.performedBy}`} 
                    {alert.performedByRole && ` (${alert.performedByRole})`}
                    {alert.completedAt && ` • ${formatTimeOnly(alert.completedAt)}`}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Clinical Decision Support Alerts */}
        {clinicalAlerts.length > 0 && showClinicalAlerts && (
          <div className="bg-amber-50 border-b border-amber-200 p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <Stethoscope className="w-4 h-4 text-amber-600" />
                <h3 className="text-sm font-bold text-amber-800">🔬 CLINICAL DECISION SUPPORT ({clinicalAlerts.length})</h3>
              </div>
              <button
                onClick={() => setShowClinicalAlerts(false)}
                className="text-amber-600 hover:text-amber-800 text-xs font-medium"
              >
                Dismiss All
              </button>
            </div>
            
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {clinicalAlerts.map((alert) => (
                <div key={alert.id} className="flex items-center justify-between p-2 bg-white rounded border-l-4 border-amber-400">
                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      alert.severity === 'critical' ? 'bg-red-600 animate-pulse' :
                      alert.severity === 'high' ? 'bg-orange-500' :
                      alert.severity === 'medium' ? 'bg-yellow-500' :
                      'bg-blue-500'
                    }`}></div>
                    <div className="flex-1 min-w-0">
                      <span className="text-xs text-amber-700 font-medium truncate block">{alert.message}</span>
                      <p className="text-xs text-gray-600 truncate">{alert.details}</p>
                      {alert.suggestedActions && alert.suggestedActions.length > 0 && (
                        <p className="text-xs text-amber-600 mt-1">
                          💡 {alert.suggestedActions[0]}
                        </p>
                      )}
                    </div>
                    <span className="text-xs text-gray-500 flex-shrink-0">
                      {formatTimeOnly(alert.timestamp)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}


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

              {/* ECG/EEG Waveform Display - Full Space Available */}
              <div className="flex-1 bg-gray-50 rounded-lg p-2 min-h-0">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-base font-semibold flex items-center space-x-2">
                    <Zap className="w-4 h-4 text-green-600" />
                    <span>{isEcgMode ? 'ECG' : 'EEG'} Monitor</span>
                  </h3>
                  <div className="flex items-center space-x-3">
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-700">
                        {isEcgMode ? 'Cardiac Rhythm' : 'Brain Activity'}
                      </p>
                      <p className="text-lg font-bold text-green-600">
                        {isEcgMode ? (patient.vitals?.ecgReading || '--') : (patient.vitals?.eegReading || '--')}
                        {isEcgMode ? ' mV' : ' μV'}
                      </p>
                    </div>
                    
                    {/* ECG/EEG Mode Toggle */}
                    <div className="flex items-center space-x-1 bg-gray-800 rounded-lg p-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleECGMode(true);
                        }}
                        className={`flex items-center space-x-1 px-2 py-1 rounded text-xs transition-colors ${
                          isEcgMode ? 'bg-green-600 text-white' : 'text-gray-400 hover:text-white'
                        }`}
                      >
                        <Heart className="w-3 h-3" />
                        <span>ECG</span>
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleToggleECGMode(false);
                        }}
                        className={`flex items-center space-x-1 px-2 py-1 rounded text-xs transition-colors ${
                          !isEcgMode ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                        }`}
                      >
                        <Zap className="w-3 h-3" />
                        <span>EEG</span>
                      </button>
                    </div>
                    
                    <select 
                      className="text-sm border rounded px-2 py-1"
                      defaultValue={isEcgMode ? 'II' : 'C3-C4'}
                    >
                      {isEcgMode ? (
                        <>
                          <option value="I">Lead I</option>
                          <option value="II">Lead II</option>
                          <option value="III">Lead III</option>
                          <option value="aVR">aVR</option>
                          <option value="aVL">aVL</option>
                          <option value="aVF">aVF</option>
                          <option value="V1">V1</option>
                          <option value="V2">V2</option>
                          <option value="V3">V3</option>
                          <option value="V4">V4</option>
                          <option value="V5">V5</option>
                          <option value="V6">V6</option>
                        </>
                      ) : (
                        <>
                          <option value="F3-F4">F3-F4</option>
                          <option value="C3-C4">C3-C4</option>
                          <option value="P3-P4">P3-P4</option>
                          <option value="O1-O2">O1-O2</option>
                          <option value="T3-T4">T3-T4</option>
                          <option value="T5-T6">T5-T6</option>
                        </>
                      )}
                    </select>
                    <button
                      onClick={() => onECGView ? onECGView(patient) : onVitalClick(patient, isEcgMode ? 'ecgReading' : 'eegReading')}
                      className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 transition-colors"
                    >
                      Full View
                    </button>
                  </div>
                </div>
                
                {/* ECG/EEG Waveform - Takes Remaining Space */}
                <div 
                  className="bg-gray-900 rounded-lg cursor-pointer flex flex-col hover:bg-gray-800 transition-colors p-2"
                  style={{ height: 'calc(100% - 60px)' }}
                  onClick={() => onECGView ? onECGView(patient) : onVitalClick(patient, isEcgMode ? 'ecgReading' : 'eegReading')}
                >
                  <div className="flex items-center justify-between mb-2 flex-shrink-0">
                    <div className="flex items-center space-x-3">
                      <div className={`w-2 h-2 rounded-full animate-pulse ${
                        isEcgMode ? 'bg-green-400' : 'bg-blue-400'
                      }`}></div>
                      <span className={`text-sm font-medium ${
                        isEcgMode ? 'text-green-400' : 'text-blue-400'
                      }`}>
                        {isEcgMode ? 'Cardiac Signal' : 'Brain Signal'} • 
                        {isEcgMode ? (patient.vitals?.ecgReading || '--') : (patient.vitals?.eegReading || '--')}
                        {isEcgMode ? 'mV' : 'μV'}
                      </span>
                      <span className="text-green-300 text-sm">25mm/s • 10mm/mV</span>
                    </div>
                    <span className="text-gray-400 text-sm">Click for full view</span>
                  </div>
                  
                  <div className="flex-1 min-h-0 relative">
                    <svg 
                      width="100%" 
                      height="100%" 
                      viewBox="0 0 400 120"
                      className="bg-gray-900 w-full h-full"
                      preserveAspectRatio="none"
                    >
                      <defs>
                        <pattern id={`grid-${patient.id}-detail`} width="10" height="10" patternUnits="userSpaceOnUse">
                          <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#374151" strokeWidth="0.5" opacity="0.4"/>
                        </pattern>
                        <pattern id={`grid-major-${patient.id}-detail`} width="50" height="50" patternUnits="userSpaceOnUse">
                          <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#4B5563" strokeWidth="1" opacity="0.6"/>
                        </pattern>
                      </defs>
                      <rect width="100%" height="100%" fill={`url(#grid-${patient.id}-detail)`} />
                      <rect width="100%" height="100%" fill={`url(#grid-major-${patient.id}-detail)`} />
                      
                      <path
                        d="M 0 50 L 400 50"
                        fill="none"
                        stroke={isEcgMode ? "#10B981" : "#3B82F6"}
                        strokeWidth="2"
                        className="drop-shadow-lg"
                      />
                      
                      {/* Sweep line */}
                      <line
                        x1="380"
                        y1="0"
                        x2="380"
                        y2="120"
                        stroke="#EF4444"
                        strokeWidth="1"
                        opacity="0.7"
                      />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Notes Tab - Compact layout */}
          {activeTab === 'notes' && (
            <div className="p-3 h-full flex flex-col">
              {PermissionUtils.canEditNotes(currentUser.role) && (
                <div className="flex justify-end mb-2">
                  <button
                    onClick={() => setIsAddingNote(true)}
                    className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                  >
                    <MessageCircle className="w-4 h-4" />
                    <span>Add Note</span>
                  </button>
                </div>
              )}

              {/* Add New Note - Compact */}
              {isAddingNote && PermissionUtils.canEditNotes(currentUser.role) && (
                <div className="mb-2 p-2 bg-blue-50 rounded-lg border">
                  <div className="flex items-start space-x-2">
                    <div className="bg-blue-600 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium">
                      {currentUser.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div className="flex-1">
                      <div className="text-xs font-medium text-gray-900 mb-1">
                        {currentUser.name} ({currentUser.role})
                      </div>
                      <textarea
                        value={newNoteContent}
                        onChange={(e) => setNewNoteContent(e.target.value)}
                        placeholder="Add a clinical note..."
                        className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
                        rows={2}
                      />
                      <div className="flex space-x-2 mt-2">
                        <button
                          onClick={handleAddNote}
                          disabled={addingNote || !newNoteContent.trim()}
                          className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
                        >
                          {addingNote ? (
                            <>
                              <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                              <span>Adding...</span>
                            </>
                          ) : (
                            <>
                              <Send className="w-3 h-3" />
                              <span>Add</span>
                            </>
                          )}
                        </button>
                        <button
                          onClick={() => {
                            setIsAddingNote(false);
                            setNewNoteContent('');
                          }}
                          className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-sm"
                        >
                          <X className="w-3 h-3" />
                          <span>Cancel</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Notes List - Compact scrollable area */}
              <div className="flex-1 overflow-y-auto space-y-2">
                {notes.slice().reverse().map((note) => (
                  <div key={note.id} className="bg-white border rounded-lg p-2">
                    <div className="flex items-start space-x-2">
                      <div className={`text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                        note.authorRole === 'Doctor' ? 'bg-blue-600' :
                        note.authorRole === 'Nurse' ? 'bg-green-600' :
                        note.authorRole === 'Admin' ? 'bg-purple-600' :
                        'bg-gray-600'
                      }`}>
                        {(note.authorName || 'U').split(' ').map(n => n[0]).join('')}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center space-x-2">
                            <span className="font-medium text-gray-900 text-sm">{note.authorName}</span>
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                              note.authorRole === 'Doctor' ? 'bg-blue-100 text-blue-800' :
                              note.authorRole === 'Nurse' ? 'bg-green-100 text-green-800' :
                              note.authorRole === 'Admin' ? 'bg-purple-100 text-purple-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {note.authorRole}
                            </span>
                            <span className="text-xs text-gray-500">
                              {formatDateTime(note.timestamp)}
                            </span>
                            {note.isEdited && (
                              <span className="text-xs text-gray-400">
                                (edited {note.editedAt ? formatDateTime(note.editedAt) : ''})
                              </span>
                            )}
                          </div>
                          {note.canEdit && note.authorId === currentUser.id && PermissionUtils.canEditNotes(currentUser.role) && (
                            <button
                              onClick={() => startEditingNote(note)}
                              className="text-gray-500 hover:text-gray-700 p-1"
                              title="Edit note"
                            >
                              <Edit className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                        
                        {editingNoteId === note.id ? (
                          <div>
                            <textarea
                              value={editingNoteContent}
                              onChange={(e) => setEditingNoteContent(e.target.value)}
                              className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-sm"
                              rows={2}
                            />
                            <div className="flex space-x-2 mt-2">
                              <button
                                onClick={() => debounce(() => handleEditNote(note.id), 300)()}
                                disabled={editingNote || !editingNoteContent.trim()}
                                className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-400"
                              >
                                {editingNote ? (
                                  <>
                                    <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                    <span>Saving...</span>
                                  </>
                                ) : (
                                  <>
                                    <Save className="w-3 h-3" />
                                    <span>Save</span>
                                  </>
                                )}
                              </button>
                              <button
                                onClick={cancelEditingNote}
                                className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
                              >
                                <X className="w-3 h-3" />
                                <span>Cancel</span>
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="text-gray-700 whitespace-pre-wrap text-sm">
                            {note.content}
                          </div>
                        )}
                        
                        {!note.canEdit && note.authorId === currentUser.id && (
                          <div className="mt-1 text-xs text-gray-500 flex items-center space-x-1">
                            <Clock className="w-3 h-3" />
                            <span>Edit time expired (24h limit)</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {(notes || []).length === 0 && (
                  <div className="text-center py-6 text-gray-500">
                    <MessageCircle className="w-10 h-10 mx-auto mb-3 opacity-50" />
                    <p>No clinical notes yet</p>
                    {PermissionUtils.canEditNotes(currentUser.role) && (
                      <button
                        onClick={() => setIsAddingNote(true)}
                        className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        Add First Note
                      </button>
                    )}
                  </div>
                )}
              </div>
              
              {/* Shift Handoff Notes Section */}
              <div className="mt-6 border-t pt-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-purple-800 flex items-center space-x-2">
                    <div className="w-6 h-6 bg-purple-100 rounded-lg flex items-center justify-center">
                      🔄
                    </div>
                    <span>Shift Handoff Notes</span>
                  </h3>
                  {PermissionUtils.canEditNotes(currentUser.role) && (
                    <button
                      onClick={() => {
                        const shift = new Date().getHours() < 16 ? 'day' : new Date().getHours() < 23 ? 'evening' : 'night';
                        const handoffNote = prompt(`Add handoff note for ${shift} shift:\n\nNote categories:\n• Medication changes\n• Assessment findings\n• Safety concerns\n• Family updates\n• Other\n\nEnter your handoff note:`);
                        
                        if (handoffNote && handoffNote.trim()) {
                          const priority = prompt('Set priority level:\n\n1 = Low\n2 = Medium\n3 = High\n4 = Critical\n\nEnter number (1-4):') || '2';
                          const priorityMap = { '1': 'low', '2': 'medium', '3': 'high', '4': 'critical' };
                          const priorityLevel = priorityMap[priority as keyof typeof priorityMap] || 'medium';
                          
                          // Add to case sheet as handoff note
                          const handoffEntry: caseSheetEntry = {
                            id: 'handoff_' + Date.now(),
                            timestamp: new Date().toISOString(),
                            type: 'handoffNote',
                            description: `${shift.toUpperCase()} SHIFT HANDOFF - ${priorityLevel.toUpperCase()} PRIORITY: ${handoffNote}`,
                            performedBy: currentUser.name,
                            canEdit: PatientService.canEditItem(new Date().toISOString()),
                            details: {
                              shift,
                              priority: priorityLevel,
                              fromNurse: currentUser.name,
                              category: 'general',
                              note: handoffNote
                            }
                          };
                          addCaseSheetEntry(handoffEntry);
                          
                          alert(`✅ Handoff note added for ${shift} shift!\n\nPriority: ${priorityLevel}\nFrom: ${currentUser.name}\n\nNote logged in case sheet for continuity of care.`);
                        }
                      }}
                      className="flex items-center space-x-2 px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm"
                    >
                      <Plus className="w-4 h-4" />
                      <span>Add Handoff</span>
                    </button>
                  )}
                </div>
                
                {/* Display recent handoff notes from case sheet */}
                <div className="space-y-2">
                  {caseSheet
                    .filter(entry => entry.type === 'handoffNote')
                    .slice(0, 3) // Show last 3 handoff notes
                    .map((handoff) => (
                      <div key={handoff.id} className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-medium text-purple-700">
                              {handoff.details?.shift?.toUpperCase() || 'GENERAL'} SHIFT
                            </span>
                            <div className={`px-2 py-0.5 rounded text-xs font-medium ${
                              handoff.details?.priority === 'critical' ? 'bg-red-100 text-red-800' :
                              handoff.details?.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                              handoff.details?.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-green-100 text-green-800'
                            }`}>
                              {handoff.details?.priority?.toUpperCase() || 'MEDIUM'}
                            </div>
                            <span className="text-xs text-gray-500">
                              {formatDateTime(handoff.timestamp)}
                            </span>
                          </div>
                          <span className="text-xs text-purple-600 font-medium">
                            From: {handoff.performedBy}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700">
                          {handoff.description.replace(/^.*PRIORITY:\s*/, '')}
                        </p>
                      </div>
                    ))}
                  
                  {caseSheet.filter(entry => entry.type === 'handoffNote').length === 0 && (
                    <div className="text-center py-4">
                      <div className="text-gray-400 mb-2">
                        <Clock className="w-8 h-8 mx-auto" />
                      </div>
                      <p className="text-sm text-gray-500">No handoff notes yet</p>
                      <p className="text-xs text-gray-400 mt-1">Add shift handoff notes to ensure continuity of care</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Medications Tab - Compact layout */}
          {activeTab === 'medications' && (
            <div className="p-3 h-full flex flex-col">
              <div className="flex justify-end mb-2">
                {!PermissionUtils.canEditMedications(currentUser.role) && (
                  <span className="text-xs bg-yellow-100 text-yellow-600 px-2 py-1 rounded-lg flex items-center space-x-1">
                    <Shield className="w-3 h-3" />
                    <span>View Only</span>
                  </span>
                )}
                {PermissionUtils.canEditMedications(currentUser.role) && (
                  <button
                    onClick={() => setIsAddingMedication(true)}
                    className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Prescribe</span>
                  </button>
                )}
              </div>

              {/* Add Medication Form */}
              {isAddingMedication && PermissionUtils.canEditMedications(currentUser.role) && (
                <div className="mb-2 p-2 bg-blue-50 rounded-lg border">
                  <h4 className="font-medium mb-2 text-sm">Prescribe New Medication</h4>
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      placeholder="Medication name"
                      value={newMedication.name}
                      onChange={(e) => setNewMedication(prev => ({ ...prev, name: e.target.value }))}
                      className="px-2 py-1 border rounded text-sm col-span-2"
                    />
                    <input
                      type="text"
                      placeholder="Dosage (e.g., 10mg)"
                      value={newMedication.dosage}
                      onChange={(e) => setNewMedication(prev => ({ ...prev, dosage: e.target.value }))}
                      className="px-2 py-1 border rounded text-sm"
                    />
                    <input
                      type="text"
                      placeholder="Frequency (e.g., Twice daily)"
                      value={newMedication.frequency}
                      onChange={(e) => setNewMedication(prev => ({ ...prev, frequency: e.target.value }))}
                      className="px-2 py-1 border rounded text-sm"
                    />
                    <input
                      type="text"
                      placeholder="Duration (e.g., 7 days)"
                      value={newMedication.duration}
                      onChange={(e) => setNewMedication(prev => ({ ...prev, duration: e.target.value }))}
                      className="px-2 py-1 border rounded text-sm"
                    />
                    <select
                      value={newMedication.route}
                      onChange={(e) => setNewMedication(prev => ({ ...prev, route: e.target.value }))}
                      className="px-2 py-1 border rounded text-sm"
                    >
                      <option value="PO">PO (Oral)</option>
                      <option value="IV">IV (Intravenous)</option>
                      <option value="IM">IM (Intramuscular)</option>
                      <option value="SC">SC (Subcutaneous)</option>
                      <option value="Inhaled">Inhaled</option>
                      <option value="Topical">Topical</option>
                    </select>
                  </div>
                  <div className="flex space-x-2 mt-2">
                    <button
                      onClick={async () => {
                        if (isAddingMedication) return; // Prevent multiple simultaneous calls
                        if (!newMedication.name || !newMedication.dosage || !newMedication.frequency || !newMedication.duration) return;
                        setIsAddingMedication(true);
                        try {
                          const timestamp = new Date().toISOString();
                          const medicationData = {
                            ...newMedication,
                            status: 'active' as const,
                            startDate: timestamp.split('T')[0],
                            prescribedBy: currentUser.name,
                            createdAt: timestamp,
                            canEdit: true
                          };
                          const newMed = await MedicationService.addMedication(patient.id, medicationData, currentUser.id);
                          if (newMed) {
                            // Add history if not present from backend
                            const medicationWithHistory: medication = {
                              ...newMed,
                              history: newMed.history || [{
                                id: 'hist_' + Date.now(),
                                action: 'prescribed' as const,
                                timestamp,
                                performedBy: currentUser.name
                              }]
                            };
                            setMedications(prev => [...prev, medicationWithHistory]);
                          } else {
                            console.error('Failed to add medication - no response from backend');
                            alert('Failed to add medication. Please try again.');
                            setIsAddingMedication(false);
                            return;
                          }
                          setNewMedication({ name: '', dosage: '', frequency: '', route: 'PO', duration: '' });
                          setIsAddingMedication(false);

                          // Add case sheet entry to backend
                          try {
                            const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json'
                              },
                              body: JSON.stringify({
                                entrytype: 'medication',
                                description: `${newMedication.name} (${newMedication.dosage}, ${newMedication.frequency}, ${newMedication.duration}) prescribed by ${currentUser.name}`,
                                performedBy: currentUser.name
                              })
                            });

                            if (caseResponse.ok) {
                              const caseResult = await caseResponse.json();
                              const newCaseEntry: caseSheetEntry = {
                                id: caseResult.id || 'cs_' + Date.now(),
                                timestamp,
                                type: 'pharmacyNotes',
                                description: `${newMedication.name} (${newMedication.dosage}, ${newMedication.frequency}, ${newMedication.duration}) prescribed by ${currentUser.name}`,
                                performedBy: currentUser.name,
                                canEdit: true
                              };
                              addCaseSheetEntry(newCaseEntry);
                            }
                          } catch (caseError) {
                            console.warn('Failed to add medication case sheet entry:', caseError);
                          }
                        } catch (error) {
                          console.error('Failed to add medication:', error);
                        } finally {
                          setIsAddingMedication(false);
                        }
                      }}
                      disabled={isAddingMedication || !newMedication.name || !newMedication.dosage || !newMedication.frequency || !newMedication.duration}
                      className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-400"
                    >
                      {isAddingMedication ? (
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
                        setIsAddingMedication(false);
                        setNewMedication({ name: '', dosage: '', frequency: '', route: 'PO', duration: '' });
                      }}
                      className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
                    >
                      <X className="w-3 h-3" />
                      <span>Cancel</span>
                    </button>
                  </div>
                </div>
              )}
              
              <div className="flex-1 overflow-y-auto space-y-2">
                {medications.map((med) => (
                  <div key={med.id} className="bg-white border rounded-lg p-2">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-1">
                          <h4 className="font-medium text-sm">{med.name} {med.dosage}</h4>
                          <div className={`px-2 py-1 rounded-full text-xs font-medium border ${getMedicationStatusColor(med.status)}`}>
                            {med.status.toUpperCase()}
                          </div>
                        </div>
                        <div className="text-sm text-gray-600">
                          <p><span className="font-medium">Frequency:</span> {med.frequency} • <span className="font-medium">Route:</span> {med.route}</p>
                          <p><span className="font-medium">Prescribed by:</span> {med.prescribedBy} on {formatDateTime(med.createdAt)?.split(',')[0] || 'Unknown date'}</p>
                          
                          
                          
                          {/* Medication Administration Schedule */}
                          {med.status === 'active' && (
                            <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-medium text-green-700">💊 Administration Schedule</span>
                                <div className="flex items-center space-x-1">
                                  <span className="text-xs text-green-600">
                                    Last: {patient.lastMedicationTime ? 
                                      new Date(patient.lastMedicationTime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 
                                      'Not recorded'
                                    }
                                  </span>
                                </div>
                              </div>
                              <div className="text-xs text-green-600">
                                {/* Generate administration times based on frequency */}
                                {(() => {
                                  // Default schedule based on frequency
                                  const freq = med.frequency.toLowerCase();
                                  let nextTimes: string[] = [];
                                  if (freq.includes('once daily')) nextTimes = ['08:00'];
                                  else if (freq.includes('twice daily')) nextTimes = ['08:00', '20:00'];
                                  else if (freq.includes('three times')) nextTimes = ['08:00', '14:00', '20:00'];
                                  else if (freq.includes('four times')) nextTimes = ['06:00', '12:00', '18:00', '22:00'];
                                  else if (freq.includes('every 8 hours')) nextTimes = ['06:00', '14:00', '22:00'];
                                  else if (freq.includes('every 6 hours')) nextTimes = ['06:00', '12:00', '18:00', '00:00'];
                                  
                                  const now = new Date();
                                  const currentTime = now.getHours() * 60 + now.getMinutes();
                                  const nextTime = nextTimes.find(time => {
                                    const [hours, minutes] = time.split(':').map(Number);
                                    return (hours * 60 + minutes) > currentTime;
                                  }) || nextTimes[0];
                                  
                                  return (
                                    <div className="flex items-center space-x-1">
                                      <span className="font-medium">Next due:</span>
                                      <span className="bg-green-100 px-2 py-0.5 rounded text-green-800">{nextTime}</span>
                                      <span className="text-green-600">({med.frequency})</span>
                                    </div>
                                  );
                                })()}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      {PermissionUtils.canEditMedications(currentUser.role) && med.canEdit && (
                        <div className="flex items-center space-x-1">
                          {med.status === 'active' && (
                            <>
                              <button
                                onClick={() => {
                                  const now = new Date().toISOString();
                                  // Add administration record to case sheet
                                  const adminEntry: caseSheetEntry = {
                                    id: 'admin_' + Date.now(),
                                    timestamp: now,
                                    type: 'medicationAdministration',
                                    description: `Administered ${med.name} ${med.dosage} via ${med.route} route`,
                                    performedBy: currentUser.name,
                                    canEdit: PatientService.canEditItem(now),
                                    details: {
                                      medicationId: med.id,
                                      medicationName: med.name,
                                      dosage: med.dosage,
                                      route: med.route,
                                      administeredby: currentUser.name,
                                      administeredat: now
                                    }
                                  };
                                  addCaseSheetEntry(adminEntry);
                                  
                                  // Update patient's last medication time
                                  alert(`✅ ${med.name} ${med.dosage} administered successfully!\n\nTime: ${new Date().toLocaleTimeString()}\nAdministered by: ${currentUser.name}\n\nAdministration logged in case sheet.`);
                                }}
                                className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                                title="Administer medication"
                              >
                                <CheckCircle className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => debounce(() => handleMedicationStatusChange(med.id, 'held'), 300)()}
                                className="p-1 text-yellow-600 hover:bg-yellow-50 rounded transition-colors"
                                title="Hold medication"
                              >
                                <Pause className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => debounce(() => handleMedicationStatusChange(med.id, 'stopped'), 300)()}
                                className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors"
                                title="Stop medication"
                              >
                                <StopCircle className="w-4 h-4" />
                              </button>
                            </>
                          )}
                          {med.status === 'held' && (
                            <button
                              onClick={() => debounce(() => handleMedicationStatusChange(med.id, 'active'), 300)()}
                              className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors"
                              title="Resume medication"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {medications.length === 0 && (
                  <div className="text-center py-6 text-gray-500">
                    <Plus className="w-10 h-10 mx-auto mb-3 opacity-50" />
                    <p>No medications prescribed yet</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Investigation Tab */}
          {activeTab === 'investigations' && (
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
                              <CheckCircle className="w-4 h-4" />
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
                    onClick={() => console.log('DICOM viewer disabled')}
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
            <div className="p-4 h-full flex flex-col">
              {PermissionUtils.canEditMedications(currentUser.role) && (
                <div className="flex justify-end mb-3">
                  <button
                    onClick={() => setIsAddingTherapy(true)}
                    className="flex items-center space-x-2 px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm"
                  >
                    <Stethoscope className="w-4 h-4" />
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
                                      
                                      // TODO: Implement therapy session recording in backend
                                      // await TherapyService.addTherapySession(patient.id, therapy.id, sessionData, currentUser.id);
                                      
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
                                <CheckCircle className="w-4 h-4" />
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
                    <Stethoscope className="w-10 h-10 mx-auto mb-3 opacity-50" />
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

export default PatientDetail;