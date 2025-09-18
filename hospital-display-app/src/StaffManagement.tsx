import React, { useState, useEffect } from 'react';
import { User, Plus, Edit, Trash2, Users, Shield, Building } from 'lucide-react';

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
  tempPin?: string;
  tempPassword?: string;
}

const StaffManagement: React.FC = () => {
  const [staff, setStaff] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingStaff, setEditingStaff] = useState<Staff | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  
  const [newStaff, setNewStaff] = useState<NewStaff>({
    staffId: '',
    name: '',
    role: '',
    department: '',
    nfcId: '',
    phone: '',
    email: '',
    password: 'hospital123'
  });
  const [previewStaffId, setPreviewStaffId] = useState<string>('');
  const [createdStaffInfo, setCreatedStaffInfo] = useState<CreatedStaff | null>(null);

  // Define which roles use PINs vs passwords
  const PIN_ROLES = [
    "Doctor", "Consultant", "Resident", "Intern",
    "Nurse", "Staff Nurse", "Nursing Assistant",
    "Technician", "Lab Technician", "Radiology Technician", "IT Technician",
    "Pharmacist", "Physiotherapist", "Security", "Maintenance", "Receptionist"
  ];
  
  const PASSWORD_ROLES = [
    "Administrator", "Provisioner"
  ];
  
  const requiresPin = (role: string) => PIN_ROLES.includes(role);
  const requiresPassword = (role: string) => PASSWORD_ROLES.includes(role);

  useEffect(() => {
    fetchStaff();
    fetchRoles();
    fetchDepartments();
  }, []);

  const fetchStaff = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/staff/');
      const data = await response.json();
      setStaff(data.staff || []);
    } catch (error) {
      console.error('Error fetching staff:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRoles = async () => {
    try {
      const response = await fetch('/api/v1/staff/roles/list');
      const data = await response.json();
      setRoles(data.roles || []);
    } catch (error) {
      console.error('Error fetching roles:', error);
    }
  };

  const fetchDepartments = async () => {
    try {
      const response = await fetch('/api/v1/staff/departments/list');
      const data = await response.json();
      setDepartments(data.departments || []);
    } catch (error) {
      console.error('Error fetching departments:', error);
    }
  };

  const fetchPreviewStaffId = async (role: string) => {
    if (!role) {
      setPreviewStaffId('');
      return;
    }
    try {
      const response = await fetch(`/api/v1/staff/generate-id/${encodeURIComponent(role)}`);
      const data = await response.json();
      setPreviewStaffId(data.nextStaffId || '');
    } catch (error) {
      console.error('Error fetching preview staff ID:', error);
      setPreviewStaffId('');
    }
  };

  const handleAddStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await fetch('/api/v1/staff/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newStaff),
      });

      if (response.ok) {
        const createdStaff = await response.json();
        setCreatedStaffInfo(createdStaff);
        
        // Auto-send WhatsApp message if phone number exists
        if (createdStaff.phone) {
          const message = `🏥 *Hospital Login Credentials*\n\nHi ${createdStaff.name}!\n\nYour login details:\n👤 *Staff ID:* ${createdStaff.staffId}\n${
            createdStaff.tempPin 
              ? `🔐 *PIN:* ${createdStaff.tempPin}` 
              : `🔐 *Password:* ${createdStaff.tempPassword}`
          }\n\nPlease keep these credentials secure.\n\nWelcome to the team! 👨‍⚕️👩‍⚕️`;
          
          const phoneNumber = (createdStaff.phone || '').replace(/[^\d]/g, '');
          const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(message)}`;
          window.open(whatsappUrl, '_blank');
        }
        
        setShowAddForm(false);
        setNewStaff({
          staffId: '',
          name: '',
          role: '',
          department: '',
          nfcId: '',
          phone: '',
          email: '',
          password: 'hospital123'
        });
        setPreviewStaffId('');
        fetchStaff();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error adding staff:', error);
      alert('Error adding staff member');
    } finally {
      setLoading(false);
    }
  };

  const handleDeactivateStaff = async (staffId: string) => {
    if (!window.confirm('Are you sure you want to deactivate this staff member?')) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/staff/${staffId}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        fetchStaff();
      } else {
        alert('Error deactivating staff member');
      }
    } catch (error) {
      console.error('Error deactivating staff:', error);
      alert('Error deactivating staff member');
    } finally {
      setLoading(false);
    }
  };

  const handleEditStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStaff) return;

    setLoading(true);
    try {
      const response = await fetch(`/api/v1/staff/${editingStaff.staffId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: editingStaff.name,
          role: editingStaff.role,
          department: editingStaff.department,
          nfcId: editingStaff.nfcId,
          phone: editingStaff.phone,
          email: editingStaff.email,
        }),
      });

      if (response.ok) {
        setEditingStaff(null);
        fetchStaff();
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error updating staff:', error);
      alert('Error updating staff member');
    } finally {
      setLoading(false);
    }
  };

  const getRoleColor = (role: string) => {
    if (role.includes('Admin') || role === 'Master Admin') return 'bg-red-100 text-red-800';
    if (role === 'Provisioner') return 'bg-purple-100 text-purple-800';
    if (role.includes('Consultant') || role.includes('Director') || role.includes('Chief')) return 'bg-blue-100 text-blue-800';
    if (role.includes('Nurse')) return 'bg-green-100 text-green-800';
    if (role.includes('Technician')) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Users className="h-8 w-8 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">Staff Management</h1>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
          disabled={loading}
        >
          <Plus className="h-5 w-5" />
          <span>Add Staff Member</span>
        </button>
      </div>

      {/* Staff Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center">
            <Users className="h-12 w-12 text-blue-600" />
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500">Total Staff</h3>
              <p className="text-2xl font-bold text-gray-900">{staff.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center">
            <Shield className="h-12 w-12 text-green-600" />
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500">Active Staff</h3>
              <p className="text-2xl font-bold text-gray-900">{staff.filter(s => s.isActive).length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center">
            <Building className="h-12 w-12 text-orange-600" />
            <div className="ml-4">
              <h3 className="text-sm font-medium text-gray-500">Departments</h3>
              <p className="text-2xl font-bold text-gray-900">{new Set(staff.map(s => s.department)).size}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Add Staff Form */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl m-4 max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Add New Staff Member</h2>
            
            <form onSubmit={handleAddStaff} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Staff ID</label>
                  <input
                    type="text"
                    value={newStaff.staffId}
                    onChange={(e) => setNewStaff({...newStaff, staffId: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder={previewStaffId || "Auto-generated based on role"}
                  />
                  {previewStaffId && !newStaff.staffId && (
                    <p className="text-xs text-green-600 mt-1">
                      Next available: <strong>{previewStaffId}</strong>
                    </p>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
                  <input
                    type="text"
                    value={newStaff.name}
                    onChange={(e) => setNewStaff({...newStaff, name: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    required
                    placeholder="Dr. John Smith"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Role *</label>
                  <select
                    value={newStaff.role}
                    onChange={(e) => {
                      const newRole = e.target.value;
                      setNewStaff({...newStaff, role: newRole});
                      fetchPreviewStaffId(newRole);
                    }}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    required
                  >
                    <option value="">Select Role</option>
                    {roles.map(role => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Department *</label>
                  <select
                    value={newStaff.department}
                    onChange={(e) => setNewStaff({...newStaff, department: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    required
                  >
                    <option value="">Select Department</option>
                    {departments.map(dept => (
                      <option key={dept} value={dept}>{dept}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">NFC ID</label>
                  <input
                    type="text"
                    value={newStaff.nfcId}
                    onChange={(e) => setNewStaff({...newStaff, nfcId: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="NFC001"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={newStaff.phone}
                    onChange={(e) => setNewStaff({...newStaff, phone: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="555-1234"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={newStaff.email}
                    onChange={(e) => setNewStaff({...newStaff, email: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="john.smith@hospital.com"
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
                  onClick={() => {
                    setShowAddForm(false);
                    setPreviewStaffId('');
                  }}
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
            <h2 className="text-xl font-bold mb-4">Edit Staff Member</h2>
            
            <form onSubmit={handleEditStaff} className="space-y-4">
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
                  <label className="block text-sm font-medium text-gray-700 mb-2">Full Name *</label>
                  <input
                    type="text"
                    value={editingStaff.name}
                    onChange={(e) => setEditingStaff({...editingStaff, name: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Role *</label>
                  <select
                    value={editingStaff.role}
                    onChange={(e) => setEditingStaff({...editingStaff, role: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    required
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
                    value={editingStaff.department}
                    onChange={(e) => setEditingStaff({...editingStaff, department: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    required
                  >
                    <option value="">Select Department</option>
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
                    placeholder="Enter NFC card ID"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
                  <input
                    type="text"
                    value={editingStaff.phone || ''}
                    onChange={(e) => setEditingStaff({...editingStaff, phone: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter phone number"
                  />
                </div>
                
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                  <input
                    type="email"
                    value={editingStaff.email || ''}
                    onChange={(e) => setEditingStaff({...editingStaff, email: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter email address"
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

      {/* Staff Credentials Modal */}
      {createdStaffInfo && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md m-4">
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                <svg className="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                </svg>
              </div>
              
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Staff Member Created Successfully!
              </h3>
              
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-gray-600">Name:</span>
                    <span className="ml-2">{createdStaffInfo.name}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">Staff ID:</span>
                    <span className="ml-2 font-mono">{createdStaffInfo.staffId}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-600">Role:</span>
                    <span className="ml-2">{createdStaffInfo.role}</span>
                  </div>
                  
                  {createdStaffInfo.tempPin && (
                    <div className="border-t pt-2 mt-3">
                      <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
                        <div className="flex items-center mb-1">
                          <svg className="h-4 w-4 text-yellow-600 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.502 0L4.33 15.5c-.77.833.192 2.5 1.732 2.5z"></path>
                          </svg>
                          <span className="font-medium text-yellow-800">Login PIN</span>
                        </div>
                        <div className="text-2xl font-mono font-bold text-center text-yellow-800">
                          {createdStaffInfo.tempPin}
                        </div>
                        <p className="text-xs text-yellow-600 mt-1 text-center">
                          Please share this PIN securely with the staff member
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {createdStaffInfo.tempPassword && (
                    <div className="border-t pt-2 mt-3">
                      <div className="bg-blue-50 border border-blue-200 rounded p-3">
                        <div className="flex items-center mb-1">
                          <svg className="h-4 w-4 text-blue-600 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m0 0a2 2 0 012 2v6a2 2 0 01-2 2h-10a2 2 0 01-2-2V9a2 2 0 012-2m0 0V7a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
                          </svg>
                          <span className="font-medium text-blue-800">Login Password</span>
                        </div>
                        <div className="text-lg font-mono font-bold text-center text-blue-800">
                          {createdStaffInfo.tempPassword}
                        </div>
                        <p className="text-xs text-blue-600 mt-1 text-center">
                          Staff can change this password after first login
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {createdStaffInfo.phone && (
                    <div className="border-t pt-2 mt-3">
                      <p className="text-xs text-gray-500 text-center mb-2">
                        📱 Phone: {createdStaffInfo.phone}
                      </p>
                      <p className="text-xs text-green-600 text-center mb-2 font-medium">
                        ✅ WhatsApp message sent automatically!
                      </p>
                      <button
                        onClick={() => {
                          const message = `🏥 *Hospital Login Credentials*\n\nHi ${createdStaffInfo.name}!\n\nYour login details:\n👤 *Staff ID:* ${createdStaffInfo.staffId}\n${
                            createdStaffInfo.tempPin 
                              ? `🔐 *PIN:* ${createdStaffInfo.tempPin}` 
                              : `🔐 *Password:* ${createdStaffInfo.tempPassword}`
                          }\n\nPlease keep these credentials secure.\n\nWelcome to the team! 👨‍⚕️👩‍⚕️`;
                          
                          const phoneNumber = (createdStaffInfo.phone || '').replace(/[^\d]/g, '');
                          const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(message)}`;
                          window.open(whatsappUrl, '_blank');
                        }}
                        className="w-full px-3 py-2 bg-green-500 hover:bg-green-600 text-white rounded-md text-sm flex items-center justify-center"
                      >
                        <svg className="h-4 w-4 mr-2" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893A11.821 11.821 0 0020.885 3.488z"/>
                        </svg>
                        Resend via WhatsApp
                      </button>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex justify-center space-x-3">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `Hospital Login Credentials\nStaff ID: ${createdStaffInfo.staffId}\n${
                        createdStaffInfo.tempPin ? `PIN: ${createdStaffInfo.tempPin}` : `Password: ${createdStaffInfo.tempPassword}`
                      }`
                    );
                    alert('Credentials copied to clipboard!');
                  }}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                >
                  📋 Copy Credentials
                </button>
                <button
                  onClick={() => setCreatedStaffInfo(null)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md"
                >
                  Done
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Staff List */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Staff Directory</h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Staff Member
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Department
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Contact
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {staff.map((member) => (
                <tr key={member.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                          <User className="h-6 w-6 text-gray-600" />
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">{member.name}</div>
                        <div className="text-sm text-gray-500">{member.staffId}</div>
                        {member.nfcId && <div className="text-xs text-blue-600">NFC: {member.nfcId}</div>}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleColor(member.role)}`}>
                      {member.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {member.department}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div>
                      {member.phone && <div>{member.phone}</div>}
                      {member.email && <div className="text-blue-600">{member.email}</div>}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      member.isActive ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {member.isActive ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                    <button
                      onClick={() => setEditingStaff(member)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDeactivateStaff(member.staffId)}
                      className="text-red-600 hover:text-red-900"
                      disabled={loading}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {staff.length === 0 && (
            <div className="text-center py-12">
              <Users className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No staff members</h3>
              <p className="mt-1 text-sm text-gray-500">Get started by adding your first staff member.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StaffManagement;