import React, { useState } from 'react';
import {
  User, Save, X, Calendar, MapPin, Stethoscope,
  Heart, AlertCircle, CheckCircle, UserPlus
} from 'lucide-react';
import { user as UserType } from './types';
import { getApiUrl } from './config/apiConfig';
// Removed unused HospitalAPI import

interface PatientAdmissionProps {
  currentUser: UserType;
  onBack: () => void;
}

export const PatientAdmission: React.FC<PatientAdmissionProps> = ({ 
  currentUser, 
  onBack 
}) => {
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    age: '',
    gender: 'Male',
    admissionType: 'General Ward', // Recommended ward type
    priority: 'Routine',
    department: currentUser.department || 'Cardiology',
    assignedDoctor: currentUser.name,
    diagnosis: '',
    weight: '',
    admissionDate: new Date().toISOString().split('T')[0], // Today's date
    insuranceType: 'General',
    emergencyContact: '',
    allergies: ''
  });
  
  const [loading, setLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const showMessage = (message: string, isError = false) => {
    if (isError) {
      setError(message);
      setTimeout(() => setError(null), 5000);
    } else {
      setShowSuccess(message);
      setTimeout(() => setShowSuccess(null), 3000);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Patient ID generation removed - backend handles ID assignment

  const admitPatient = async () => {
    // Validation
    if (!formData.name || !formData.age || !formData.diagnosis) {
      showMessage('Please fill all required fields (Name, Age, Diagnosis)', true);
      return;
    }

    setLoading(true);
    try {
      // Backend will assign patient ID - no frontend generation needed
      
      const patientData = {
        // Backend will generate and assign ID
        name: formData.name,
        bedNumber: '', // Will be assigned by nursing staff
        ward: formData.admissionType, // Doctor's recommendation
        room: '', // Will be assigned by nursing staff
        department: formData.department,
        assignedDoctor: formData.assignedDoctor,
        age: parseInt(formData.age),
        gender: formData.gender,
        weight: formData.weight ? parseFloat(formData.weight) : undefined,
        diagnosis: formData.diagnosis,
        admissionDate: formData.admissionDate,
        status: formData.priority === 'Emergency' ? 'critical' : 'stable',
        admissionType: formData.admissionType,
        priority: formData.priority,
        insuranceType: formData.insuranceType,
        emergencyContact: formData.emergencyContact,
        allergies: formData.allergies,
        admissionStatus: 'pendingBedAssignment' // New status for workflow
      };

      // Create admission recommendation instead of direct admission
      const recommendationData = {
        patientName: formData.name,
        age: parseInt(formData.age),
        gender: formData.gender,
        diagnosis: formData.diagnosis,
        priority: formData.priority.toLowerCase(),
        recommendedWard: formData.admissionType,
        department: formData.department,
        estimatedLengthOfStay: formData.priority === 'Emergency' ? 1 : 3,
        specialRequirements: formData.allergies ? `Allergies: ${formData.allergies}` : null,
        insuranceType: formData.insuranceType,
        emergencyContact: formData.emergencyContact,
        weight: formData.weight ? parseFloat(formData.weight) : null
      };

      const response = await fetch(getApiUrl('/admission/recommendations'), {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          patientName: formData.name,
          age: parseInt(formData.age),
          gender: formData.gender,
          diagnosis: formData.diagnosis,
          priority: formData.priority.toLowerCase(), 
          recommendedWard: formData.admissionType,
          department: formData.department,
          estimatedLengthOfStay: formData.priority === 'Emergency' ? 1 : 3,
          specialRequirements: formData.allergies ? `Allergies: ${formData.allergies}` : null,
          insuranceType: formData.insuranceType,
          emergencyContact: formData.emergencyContact,
          weight: formData.weight ? parseFloat(formData.weight) : null,
          performedBy: currentUser.staffId // Pass the actual doctor's staff ID
        })
      });

      if (response.ok) {
        const result = await response.json();
        showMessage(`✅ Admission recommendation created for ${formData.name}! Recommendation ID: ${result.recommendationId}. Nursing staff will process bed assignment and complete admission.`);
        // Reset form
        setFormData({
          id: '',
          name: '',
          age: '',
          gender: 'Male',
          admissionType: 'General Ward',
          priority: 'Routine',
          department: currentUser.department || 'Cardiology',
          assignedDoctor: currentUser.name,
          diagnosis: '',
          weight: '',
          admissionDate: new Date().toISOString().split('T')[0],
          insuranceType: 'General',
          emergencyContact: '',
          allergies: ''
        });
      } else {
        const errorData = await response.json();
        showMessage(errorData.detail || 'Failed to admit patient', true);
      }
    } catch (error: any) {
      console.error('Error admitting patient:', error);
      showMessage('Failed to admit patient', true);
    }
    setLoading(false);
  };

  const departments = [
    'General Medicine', 'Cardiology', 'Neurology', 'Orthopedics', 'Gynecology', 
    'General Surgery', 'Pediatrics', 'Emergency Medicine',
    'Internal Medicine', 'Oncology', 'Radiology', 'Dermatology', 'ENT'
  ];

  const admissionTypes = [
    'General Ward', 'ICU', 'Emergency Ward', 'Pediatric Ward',
    'Maternity Ward', 'Surgical Ward', 'Cardiac Care Unit', 'Observation Ward'
  ];

  const priorities = [
    'Routine', 'Urgent', 'Emergency'
  ];

  const insuranceTypes = [
    'General', 'Insurance', 'Corporate', 'Government', 'Cash'
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={onBack}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
                  <UserPlus className="w-7 h-7 text-blue-600" />
                  <span>Patient Admission Recommendation</span>
                </h1>
                <p className="text-sm text-gray-600">Recommend patient for hospital admission (bed assignment by nursing staff)</p>
              </div>
            </div>
            <div className="text-sm text-gray-600">
              Doctor: <span className="font-medium">{currentUser.name}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Success/Error Messages */}
      {showSuccess && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
            <CheckCircle className="w-5 h-5 inline mr-2" />
            {showSuccess}
          </div>
        </div>
      )}
      {error && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            <AlertCircle className="w-5 h-5 inline mr-2" />
            {error}
          </div>
        </div>
      )}

      {/* Admission Form */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Patient Information</h2>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Patient ID */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Patient ID (auto-generated if empty)
                </label>
                <input
                  type="text"
                  value={formData.id}
                  onChange={(e) => handleInputChange('id', e.target.value)}
                  placeholder="Auto-generated"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Patient Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Patient Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="Enter patient's full name"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              {/* Age */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Age *
                </label>
                <input
                  type="number"
                  value={formData.age}
                  onChange={(e) => handleInputChange('age', e.target.value)}
                  placeholder="Patient age"
                  min="0"
                  max="150"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>

              {/* Gender */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Gender
                </label>
                <select
                  value={formData.gender}
                  onChange={(e) => handleInputChange('gender', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              {/* Weight */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Weight (kg)
                </label>
                <input
                  type="number"
                  value={formData.weight}
                  onChange={(e) => handleInputChange('weight', e.target.value)}
                  placeholder="Patient weight"
                  step="0.1"
                  min="0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Admission Date */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Admission Date
                </label>
                <input
                  type="date"
                  value={formData.admissionDate}
                  onChange={(e) => handleInputChange('admissionDate', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Department */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Department
                </label>
                <select
                  value={formData.department}
                  onChange={(e) => handleInputChange('department', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {departments.map(dept => (
                    <option key={dept} value={dept}>{dept}</option>
                  ))}
                </select>
              </div>

              {/* Recommended Admission Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Recommended Admission Type *
                </label>
                <select
                  value={formData.admissionType}
                  onChange={(e) => handleInputChange('admissionType', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                >
                  {admissionTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>

              {/* Priority */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Priority *
                </label>
                <select
                  value={formData.priority}
                  onChange={(e) => handleInputChange('priority', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                >
                  {priorities.map(priority => (
                    <option key={priority} value={priority}>{priority}</option>
                  ))}
                </select>
              </div>

              {/* Insurance Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Insurance/Payment Type
                </label>
                <select
                  value={formData.insuranceType}
                  onChange={(e) => handleInputChange('insuranceType', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {insuranceTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>

              {/* Emergency Contact */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Emergency Contact
                </label>
                <input
                  type="text"
                  value={formData.emergencyContact}
                  onChange={(e) => handleInputChange('emergencyContact', e.target.value)}
                  placeholder="Phone number or contact details"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Assigned Doctor */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Assigned Doctor
                </label>
                <input
                  type="text"
                  value={formData.assignedDoctor}
                  onChange={(e) => handleInputChange('assignedDoctor', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>

            {/* Allergies */}
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Known Allergies
              </label>
              <input
                type="text"
                value={formData.allergies}
                onChange={(e) => handleInputChange('allergies', e.target.value)}
                placeholder="Drug allergies, food allergies, etc. (if any)"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Diagnosis */}
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Primary Diagnosis & Reason for Admission *
              </label>
              <textarea
                value={formData.diagnosis}
                onChange={(e) => handleInputChange('diagnosis', e.target.value)}
                placeholder="Enter primary diagnosis, symptoms, and medical reason for recommending admission"
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end space-x-4 mt-8 pt-6 border-t border-gray-200">
              <button
                onClick={onBack}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                onClick={admitPatient}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                <Save className="w-4 h-4" />
                <span>{loading ? 'Creating Recommendation...' : 'Create Admission Recommendation'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};