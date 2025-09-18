import React, { useState, useEffect } from 'react';
import { 
  Users, Bed, Clock, AlertCircle, CheckCircle, User, 
  Heart, MapPin, Calendar, Phone, Activity 
} from 'lucide-react';
import { User as UserType } from './types';

interface AdmissionRecommendation {
  id: string;
  firstName: string;
  lastName: string;
  age: number;
  dateofbirth?: string;
  gender: string;
  diagnosis: string;
  priority: string;
  recommendedward?: string;
  department: string;
  estimatedLengthOfStay?: number;
  specialRequirements?: string;
  insurancetype?: string;
  emergencycontact?: string;
  allergies?: string;
  weight?: number;
  assigneddoctor: string;
  assigneddoctorname?: string;
  recommendedby: string;
  createdat: string;
  status: string;
}

interface AvailableBed {
  wardId: string;
  wardName: string;
  wardType: string;
  roomId: string;
  roomNumber: string;
  roomType: string;
  bedId: string;
  bedNumber: string;
  bedType: string;
  equipment: any;
}

interface AvailableDevice {
  id: string;
  deviceId: string;
  deviceName: string;
  deviceType: string;
  model: string;
  batteryLevel: number;
  location: string;
}

interface NurseAdmissionProps {
  currentUser: UserType;
  onBack: () => void;
}

export const NurseAdmissionProcessing: React.FC<NurseAdmissionProps> = ({ 
  currentUser, 
  onBack 
}) => {
  const [recommendations, setRecommendations] = useState<AdmissionRecommendation[]>([]);
  const [availableBeds, setAvailableBeds] = useState<AvailableBed[]>([]);
  const [availableDevices, setAvailableDevices] = useState<AvailableDevice[]>([]);
  const [selectedRecommendation, setSelectedRecommendation] = useState<AdmissionRecommendation | null>(null);
  const [bedNumber, setBedNumber] = useState<string>('');
  const [roomNumber, setRoomNumber] = useState<string>('');
  const [wardType, setWardType] = useState<string>('General Ward');
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [processingNotes, setProcessingNotes] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Load pending recommendations
      const recResponse = await fetch('http://localhost:8001/api/v1/admission/recommendations?status=pending');
      const recData = await recResponse.json();
      // Transform name fields from lowercase to camelCase for admission recommendations
      const transformedRecommendations = (recData.recommendations || []).map((rec: any) => ({
        ...rec,
        firstName: rec.firstname || rec.firstName,
        lastName: rec.lastname || rec.lastName
      }));
      setRecommendations(transformedRecommendations);

      // Skip loading beds - manual entry only
      setAvailableBeds([]);

      // Load available devices
      const devicesResponse = await fetch('http://localhost:8001/api/v1/admission/available-devices?deviceType=watch');
      const devicesData = await devicesResponse.json();
      setAvailableDevices(devicesData.availableDevices || []);

    } catch (err) {
      setError('Failed to load admission data');
      console.error('Error loading data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleProcessAdmission = async () => {
    if (!selectedRecommendation || !bedNumber || !roomNumber) {
      setError('Please select a recommendation and enter bed/room numbers');
      return;
    }

    try {
      setProcessing(true);
      
      const response = await fetch('http://localhost:8001/api/v1/admission/process-admission', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          recommendationId: selectedRecommendation.id,
          bedNumber: bedNumber,
          roomNumber: roomNumber,
          wardType: wardType,
          selectedDevice: selectedDevice || null,
          processingNotes: processingNotes,
          processedBy: currentUser.name || 'Nursing Staff'
        })
      });

      const data = await response.json();

      if (data.success) {
        setSuccess(`Patient ${(() => {
          const placeholders = ['Patient', 'patient', 'Client', 'client', 'User', 'user', 'Test', 'test'];
          // Filter out placeholder words from individual name parts
          const validNames = [selectedRecommendation.firstName, selectedRecommendation.lastName]
            .filter(Boolean)
            .filter(name => !placeholders.includes(name.trim()));

          const cleanName = validNames.join(' ').trim();
          return cleanName || 'Unknown Patient';
        })()} successfully admitted to Bed ${bedNumber}, Room ${roomNumber}`);
        setSelectedRecommendation(null);
        setBedNumber('');
        setRoomNumber('');
        setWardType('General Ward');
        setSelectedDevice('');
        setProcessingNotes('');
        await loadData(); // Refresh data
      } else {
        setError(data.message || 'Failed to process admission');
      }

    } catch (err) {
      setError('Error processing admission');
      console.error('Error:', err);
    } finally {
      setProcessing(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-red-600 bg-red-50';
      case 'routine': return 'text-blue-600 bg-blue-50';
      case 'elective': return 'text-green-600 bg-green-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getBedTypeIcon = (bedType: string) => {
    switch (bedType) {
      case 'ICU': return '🏥';
      case 'cardiac': return '❤️';
      case 'emergency': return '🚨';
      default: return '🛏️';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading admission data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center">
                <Users className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Nurse Admission Processing</h1>
                <p className="text-gray-600">Process doctor recommendations and admit patients</p>
              </div>
            </div>
            <button
              onClick={onBack}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              ← Back
            </button>
          </div>
        </div>

        {/* Success/Error Messages */}
        {success && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
              <span className="text-green-800">{success}</span>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
              <span className="text-red-800">{error}</span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Pending Recommendations */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <Clock className="w-5 h-5 mr-2" />
              Pending Admissions ({recommendations.length})
            </h2>

            <div className="space-y-4 max-h-96 overflow-y-auto">
              {recommendations.map((rec) => (
                <div
                  key={rec.id}
                  className={`border rounded-lg p-4 cursor-pointer transition-all ${
                    selectedRecommendation?.id === rec.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setSelectedRecommendation(rec)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-semibold text-gray-900">
                        {(() => {
                          const placeholders = ['Patient', 'patient', 'Client', 'client', 'User', 'user', 'Test', 'test'];
                          // Filter out placeholder words from individual name parts
                          const validNames = [rec.firstName, rec.lastName]
                            .filter(Boolean)
                            .filter(name => !placeholders.includes(name.trim()));

                          const cleanName = validNames.join(' ').trim();
                          return cleanName || 'Unknown Patient';
                        })()}
                      </h3>
                      <p className="text-sm text-gray-600">{rec.age} years old, {rec.gender}</p>
                    </div>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getPriorityColor(rec.priority)}`}>
                      {rec.priority.toUpperCase()}
                    </span>
                  </div>
                  
                  <div className="space-y-1 text-sm text-gray-600">
                    <div className="flex items-center">
                      <Heart className="w-4 h-4 mr-1" />
                      {rec.diagnosis}
                    </div>
                    <div className="flex items-center">
                      <MapPin className="w-4 h-4 mr-1" />
                      {rec.department}
                    </div>
                    <div className="flex items-center">
                      <User className="w-4 h-4 mr-1" />
                      {rec.assigneddoctorname || rec.assigneddoctor}
                    </div>
                    <div className="flex items-center">
                      <Calendar className="w-4 h-4 mr-1" />
                      {rec.createdat ? (() => {
                      try {
                        return new Date(rec.createdat).toLocaleString();
                      } catch {
                        return 'Date not available';
                      }
                    })() : 'Date not available'}
                    </div>
                    {rec.specialRequirements && (
                      <div className="flex items-center">
                        <AlertCircle className="w-4 h-4 mr-1" />
                        {rec.specialRequirements}
                      </div>
                    )}
                    {rec.emergencycontact && (
                      <div className="flex items-center">
                        <Phone className="w-4 h-4 mr-1" />
                        {rec.emergencycontact}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {recommendations.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <Users className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                  <p>No pending admission recommendations</p>
                </div>
              )}
            </div>
          </div>

          {/* Admission Processing */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <Bed className="w-5 h-5 mr-2" />
              Process Admission
            </h2>

            {selectedRecommendation ? (
              <div className="space-y-4">
                {/* Patient Info */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">
                    Patient: {(() => {
                      const placeholders = ['Patient', 'patient', 'Client', 'client', 'User', 'user', 'Test', 'test'];
                      // Filter out placeholder words from individual name parts
                      const validNames = [selectedRecommendation.firstName, selectedRecommendation.lastName]
                        .filter(Boolean)
                        .filter(name => !placeholders.includes(name.trim()));

                      const cleanName = validNames.join(' ').trim();
                      return cleanName || 'Unknown Patient';
                    })()}
                  </h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>Age: {selectedRecommendation.age}</div>
                    <div>Gender: {selectedRecommendation.gender}</div>
                    <div>Department: {selectedRecommendation.department}</div>
                    <div>Priority: <span className={`px-1 rounded ${getPriorityColor(selectedRecommendation.priority)}`}>
                      {selectedRecommendation.priority}
                    </span></div>
                  </div>
                </div>

                {/* Manual Bed/Room Entry */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Bed Number <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={bedNumber}
                      onChange={(e) => setBedNumber(e.target.value)}
                      placeholder="e.g., 101A"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Room Number <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={roomNumber}
                      onChange={(e) => setRoomNumber(e.target.value)}
                      placeholder="e.g., 201"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
                
                {/* Ward Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Ward Type
                  </label>
                  <select
                    value={wardType}
                    onChange={(e) => setWardType(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="General Ward">General Ward</option>
                    <option value="ICU">ICU</option>
                    <option value="Emergency">Emergency</option>
                    <option value="Cardiac">Cardiac</option>
                    <option value="Pediatric">Pediatric</option>
                    <option value="Maternity">Maternity</option>
                  </select>
                </div>

                {/* Device Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Assign Watch Device (Optional)
                  </label>
                  <select
                    value={selectedDevice}
                    onChange={(e) => setSelectedDevice(e.target.value)}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">No device assigned</option>
                    {availableDevices.map((device) => (
                      <option key={device.id} value={device.id}>
                        {device.deviceName} - Battery: {device.batteryLevel}%
                      </option>
                    ))}
                  </select>
                </div>

                {/* Processing Notes */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Processing Notes
                  </label>
                  <textarea
                    value={processingNotes}
                    onChange={(e) => setProcessingNotes(e.target.value)}
                    rows={3}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Add any notes about this admission..."
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex space-x-3">
                  <button
                    onClick={handleProcessAdmission}
                    disabled={processing || !bedNumber || !roomNumber}
                    className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center"
                  >
                    {processing ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Processing...
                      </>
                    ) : (
                      <>
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Admit Patient
                      </>
                    )}
                  </button>
                  
                  <button
                    onClick={() => setSelectedRecommendation(null)}
                    className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                <Bed className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                <p>Select a recommendation to process admission</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};