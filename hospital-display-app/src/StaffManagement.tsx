import React from 'react';
import { Users, Plus } from 'lucide-react';
import { useStaffManagement } from './hooks/useStaffManagement';
import {
  StaffForm,
  StaffList,
  StaffFilters,
  StaffDetails
} from './components/StaffManagement';

const StaffManagement: React.FC = () => {
  const {
    // Data
    staff,
    loading,
    error,
    roles,
    departments,

    // Form state
    showAddForm,
    setShowAddForm,
    editingStaff,
    setEditingStaff,
    newStaff,
    setNewStaff,
    previewStaffId,
    setPreviewStaffId,
    createdStaff,

    // Filter state
    searchTerm,
    setSearchTerm,
    selectedRole,
    setSelectedRole,
    selectedDepartment,
    setSelectedDepartment,
    statusFilter,
    setStatusFilter,

    // Actions
    fetchStaff,
    addStaff,
    editStaff,
    deleteStaff,
    clearError,
    clearCreatedStaff,

    // Stats
    totalStaff,
    filteredCount,
    activeStaff,
    inactiveStaff,
  } = useStaffManagement({
    autoRefresh: true,
    refreshInterval: 30000
  });

  const handleAddSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    await addStaff(newStaff);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStaff) return;
    clearError();
    await editStaff(editingStaff);
  };

  const handleDelete = async (staffId: string, name: string) => {
    if (window.confirm(`Are you sure you want to delete ${name}? This action cannot be undone.`)) {
      clearError();
      await deleteStaff(staffId);
    }
  };

  const handleCloseAdd = () => {
    setShowAddForm(false);
    setPreviewStaffId('');
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
    clearError();
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <Users className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Staff Management</h1>
            <p className="text-gray-600">Manage hospital staff members and their access</p>
          </div>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
          <span>Add Staff Member</span>
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <span className="text-red-400">❌</span>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
            <button
              onClick={clearError}
              className="text-red-600 hover:text-red-800"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <Users className="w-8 h-8 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Total Staff</p>
              <p className="text-2xl font-semibold text-gray-900">{totalStaff}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                <span className="text-green-600 font-bold">✓</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Active</p>
              <p className="text-2xl font-semibold text-green-600">{activeStaff}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                <span className="text-red-600 font-bold">✕</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Inactive</p>
              <p className="text-2xl font-semibold text-red-600">{inactiveStaff}</p>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span className="text-blue-600 font-bold">#</span>
              </div>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-500">Filtered</p>
              <p className="text-2xl font-semibold text-blue-600">{filteredCount}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <StaffFilters
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        selectedRole={selectedRole}
        setSelectedRole={setSelectedRole}
        selectedDepartment={selectedDepartment}
        setSelectedDepartment={setSelectedDepartment}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        roles={roles}
        departments={departments}
        onRefresh={fetchStaff}
        loading={loading}
      />

      {/* Staff List */}
      <StaffList
        staff={staff}
        loading={loading}
        onEdit={setEditingStaff}
        onDelete={handleDelete}
      />

      {/* Staff Form */}
      <StaffForm
        showAddForm={showAddForm}
        editingStaff={editingStaff}
        newStaff={newStaff}
        setNewStaff={setNewStaff}
        setEditingStaff={setEditingStaff}
        roles={roles}
        departments={departments}
        loading={loading}
        previewStaffId={previewStaffId}
        setPreviewStaffId={setPreviewStaffId}
        onCloseAdd={handleCloseAdd}
        onSubmitAdd={handleAddSubmit}
        onSubmitEdit={handleEditSubmit}
      />

      {/* Staff Details */}
      <StaffDetails
        staff={null}
        createdStaff={createdStaff}
        onClose={clearCreatedStaff}
        onEdit={setEditingStaff}
      />
    </div>
  );
};

export default StaffManagement;