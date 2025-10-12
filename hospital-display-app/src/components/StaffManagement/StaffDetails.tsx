import React from 'react';
import { User, Mail, Phone, CreditCard, Building, Shield, Calendar, X } from 'lucide-react';
import { staff, createdStaff } from '../../types';

interface StaffDetailsProps {
  staff: staff | null;
  createdStaff: createdStaff | null;
  onClose: () => void;
  onEdit?: (staff: staff) => void;
}

export const StaffDetails: React.FC<StaffDetailsProps> = ({
  staff,
  createdStaff,
  onClose,
  onEdit
}) => {
  const displayStaff = createdStaff || staff;

  if (!displayStaff) {
    return null;
  }

  const getRoleColor = (role: string) => {
    if (role.includes('Admin') || role === 'Master Admin') return 'bg-red-100 text-red-800 border-red-200';
    if (role === 'Provisioner') return 'bg-purple-100 text-purple-800 border-purple-200';
    if (role.includes('Consultant') || role.includes('Director') || role.includes('Chief')) return 'bg-blue-100 text-blue-800 border-blue-200';
    if (role.includes('Nurse')) return 'bg-green-100 text-green-800 border-green-200';
    if (role.includes('Technician')) return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    return 'bg-gray-100 text-gray-800 border-gray-200';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl m-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">
            {createdStaff ? 'Staff Member Created Successfully' : 'Staff Member Details'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            title="Close"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Success Message for Created Staff */}
        {createdStaff && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                  <span className="text-green-600 font-bold">✓</span>
                </div>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-green-800">Staff Member Added Successfully</h3>
                <p className="text-sm text-green-700 mt-1">
                  New staff member has been created and is ready for use.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Staff Information Card */}
        <div className="bg-gray-50 rounded-lg p-6 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-16 h-16 bg-gray-300 rounded-full flex items-center justify-center">
                <User className="w-8 h-8 text-gray-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{displayStaff.name}</h3>
                <p className="text-sm text-gray-600">{displayStaff.staffId}</p>
                <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRoleColor(displayStaff.role)}`}>
                  <Shield className="w-3 h-3 mr-1" />
                  {displayStaff.role}
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                displayStaff.isActive
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              }`}>
                {displayStaff.isActive ? 'Active' : 'Inactive'}
              </span>
              {onEdit && staff && (
                <button
                  onClick={() => onEdit(staff)}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  Edit
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Details Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Contact Information */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-gray-900 uppercase tracking-wide">Contact Information</h4>

            <div className="flex items-center space-x-3">
              <Mail className="w-4 h-4 text-gray-400" />
              <div>
                <p className="text-sm text-gray-600">Email</p>
                <p className="text-sm font-medium text-gray-900">
                  {displayStaff.email || 'Not provided'}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Phone className="w-4 h-4 text-gray-400" />
              <div>
                <p className="text-sm text-gray-600">Phone</p>
                <p className="text-sm font-medium text-gray-900">
                  {displayStaff.phone || 'Not provided'}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <CreditCard className="w-4 h-4 text-gray-400" />
              <div>
                <p className="text-sm text-gray-600">NFC Card ID</p>
                <p className="text-sm font-medium text-gray-900">
                  {displayStaff.nfcId || 'Not assigned'}
                </p>
              </div>
            </div>
          </div>

          {/* Work Information */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium text-gray-900 uppercase tracking-wide">Work Information</h4>

            <div className="flex items-center space-x-3">
              <Building className="w-4 h-4 text-gray-400" />
              <div>
                <p className="text-sm text-gray-600">Department</p>
                <p className="text-sm font-medium text-gray-900">{displayStaff.department}</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Calendar className="w-4 h-4 text-gray-400" />
              <div>
                <p className="text-sm text-gray-600">Created</p>
                <p className="text-sm font-medium text-gray-900">
                  {formatDate(displayStaff.createdAt)}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Temporary Credentials (for newly created staff) */}
        {createdStaff && (createdStaff.temppin || createdStaff.temppassword) && (
          <div className="border border-yellow-200 bg-yellow-50 rounded-lg p-4 mb-6">
            <h4 className="text-sm font-medium text-yellow-800 mb-3">
              🔐 Temporary Login Credentials
            </h4>
            <div className="space-y-2">
              {createdStaff.temppassword && (
                <div>
                  <p className="text-xs text-yellow-700">Temporary Password:</p>
                  <p className="text-sm font-mono bg-yellow-100 px-2 py-1 rounded text-yellow-800">
                    {createdStaff.temppassword}
                  </p>
                </div>
              )}
              {createdStaff.temppin && (
                <div>
                  <p className="text-xs text-yellow-700">Temporary PIN:</p>
                  <p className="text-sm font-mono bg-yellow-100 px-2 py-1 rounded text-yellow-800">
                    {createdStaff.temppin}
                  </p>
                </div>
              )}
            </div>
            <p className="text-xs text-yellow-700 mt-2">
              ⚠️ Please provide these credentials to the staff member securely.
              They should change these on first login.
            </p>
          </div>
        )}

        {/* Security Information */}
        <div className="bg-blue-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-800 mb-2">Security Information</h4>
          <div className="text-xs text-blue-700 space-y-1">
            <p>• This staff member can access systems based on their role permissions</p>
            <p>• All login attempts are logged and monitored</p>
            <p>• Contact IT support for password resets or access issues</p>
            {displayStaff.nfcId && <p>• NFC card access is enabled for physical entry</p>}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};