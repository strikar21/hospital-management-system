import React from 'react';
import { X } from 'lucide-react';

interface Staff {
  id: string;
  staffId: string;
  name: string;
  role: string;
  department: string;
  nfcId?: string;
  phone?: string;
  email?: string;
  isActive: boolean;
  createdAt: string;
}

interface NewStaff {
  staffId: string;
  name: string;
  role: string;
  department: string;
  nfcId: string;
  phone: string;
  email: string;
  password: string;
}

interface CreatedStaff extends Staff {
  temppin?: string;
  temppassword?: string;
}

interface StaffFormProps {
  showAddForm: boolean;
  editingStaff: Staff | null;
  newStaff: NewStaff;
  setNewStaff: (staff: NewStaff) => void;
  setEditingStaff: (staff: Staff | null) => void;
  roles: string[];
  departments: string[];
  loading: boolean;
  previewStaffId: string;
  setPreviewStaffId: (id: string) => void;
  onCloseAdd: () => void;
  onSubmitAdd: (e: React.FormEvent) => void;
  onSubmitEdit: (e: React.FormEvent) => void;
}

export const StaffForm: React.FC<StaffFormProps> = ({
  showAddForm,
  editingStaff,
  newStaff,
  setNewStaff,
  setEditingStaff,
  roles,
  departments,
  loading,
  previewStaffId,
  setPreviewStaffId,
  onCloseAdd,
  onSubmitAdd,
  onSubmitEdit
}) => {
  const requiresPassword = (role: string) => {
    return ['Master Admin', 'Admin', 'Dept Admin', 'Provisioner'].includes(role);
  };

  const requiresPin = (role: string) => {
    return ['Nurse', 'Technician', 'Pharmacist', 'Dietitian'].includes(role);
  };

  const generateStaffId = (name: string, role: string) => {
    if (!name || !role) return '';

    const cleanName = name.replace(/\s+/g, '').toLowerCase();
    const rolePrefix = role.slice(0, 3).toUpperCase();
    // Staff ID generation moved to backend for consistency and compliance
    // Frontend should not generate medical staff IDs
    return `TEMP_${rolePrefix}${cleanName.slice(0, 4)}`; // Backend will generate proper UUID
  };

  React.useEffect(() => {
    if (newStaff.name && newStaff.role && !previewStaffId) {
      const generatedId = generateStaffId(newStaff.name, newStaff.role);
      setPreviewStaffId(generatedId);
      setNewStaff({...newStaff, staffId: generatedId});
    }
  }, [newStaff.name, newStaff.role, previewStaffId, setPreviewStaffId, setNewStaff]);

  if (!showAddForm && !editingStaff) {
    return null;
  }

  return (
    <>
      {/* Add Staff Form */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-4xl m-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold">Add New Staff Member</h2>
              <button
                onClick={onCloseAdd}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={onSubmitAdd} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={newStaff.name}
                    onChange={(e) => setNewStaff({...newStaff, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter full name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Role *</label>
                  <select
                    required
                    value={newStaff.role}
                    onChange={(e) => setNewStaff({...newStaff, role: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">Select Role</option>
                    {roles.map(role => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Department *</label>
                  <select
                    required
                    value={newStaff.department}
                    onChange={(e) => setNewStaff({...newStaff, department: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">Select Department</option>
                    {departments.map(dept => (
                      <option key={dept} value={dept}>{dept}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Staff ID
                    <span className="text-xs text-gray-500 ml-1">(Auto-generated)</span>
                  </label>
                  <input
                    type="text"
                    value={newStaff.staffId}
                    onChange={(e) => setNewStaff({...newStaff, staffId: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Will be auto-generated"
                  />
                  {previewStaffId && (
                    <p className="text-xs text-green-600 mt-1">Preview: {previewStaffId}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">NFC Card ID</label>
                  <input
                    type="text"
                    value={newStaff.nfcId}
                    onChange={(e) => setNewStaff({...newStaff, nfcId: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Scan or enter NFC ID"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
                  <input
                    type="tel"
                    value={newStaff.phone}
                    onChange={(e) => setNewStaff({...newStaff, phone: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Contact number"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                  <input
                    type="email"
                    value={newStaff.email}
                    onChange={(e) => setNewStaff({...newStaff, email: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="email@hospital.com"
                  />
                </div>

                {requiresPassword(newStaff.role) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                    <input
                      type="text"
                      value={newStaff.password}
                      onChange={(e) => setNewStaff({...newStaff, password: e.target.value})}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Default: hospital123"
                    />
                    <p className="text-xs text-gray-500 mt-1">Admin roles use passwords for login</p>
                  </div>
                )}

                {requiresPin(newStaff.role) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">PIN Authentication</label>
                    <div className="w-full p-2 border border-gray-200 rounded-md bg-gray-50 text-gray-600">
                      PIN will be auto-generated
                    </div>
                    <p className="text-xs text-gray-500 mt-1">A 6-digit PIN will be automatically generated for this role</p>
                  </div>
                )}

                {!requiresPassword(newStaff.role) && !requiresPin(newStaff.role) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                    <input
                      type="text"
                      value={newStaff.password}
                      onChange={(e) => setNewStaff({...newStaff, password: e.target.value})}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Default: hospital123"
                    />
                    <p className="text-xs text-gray-500 mt-1">Default authentication method</p>
                  </div>
                )}
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={onCloseAdd}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50"
                >
                  {loading ? 'Adding...' : 'Add Staff Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Staff Form */}
      {editingStaff && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl m-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Edit Staff Member</h2>
              <button
                onClick={() => setEditingStaff(null)}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={onSubmitEdit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Staff ID</label>
                  <input
                    type="text"
                    value={editingStaff.staffId}
                    disabled
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100"
                  />
                  <p className="text-xs text-gray-500 mt-1">Staff ID cannot be changed</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                  <input
                    type="text"
                    required
                    value={editingStaff.name}
                    onChange={(e) => setEditingStaff({...editingStaff, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Role</label>
                  <select
                    required
                    value={editingStaff.role}
                    onChange={(e) => setEditingStaff({...editingStaff, role: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  >
                    {roles.map(role => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Department</label>
                  <select
                    required
                    value={editingStaff.department}
                    onChange={(e) => setEditingStaff({...editingStaff, department: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  >
                    {departments.map(dept => (
                      <option key={dept} value={dept}>{dept}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">NFC Card ID</label>
                  <input
                    type="text"
                    value={editingStaff.nfcId || ''}
                    onChange={(e) => setEditingStaff({...editingStaff, nfcId: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
                  <input
                    type="tel"
                    value={editingStaff.phone || ''}
                    onChange={(e) => setEditingStaff({...editingStaff, phone: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                  <input
                    type="email"
                    value={editingStaff.email || ''}
                    onChange={(e) => setEditingStaff({...editingStaff, email: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={() => setEditingStaff(null)}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50"
                >
                  {loading ? 'Updating...' : 'Update Staff Member'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};