import React from 'react';
import { Search, Filter, RefreshCw } from 'lucide-react';

interface StaffFiltersProps {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  selectedRole: string;
  setSelectedRole: (role: string) => void;
  selectedDepartment: string;
  setSelectedDepartment: (department: string) => void;
  statusFilter: string;
  setStatusFilter: (status: string) => void;
  roles: string[];
  departments: string[];
  onRefresh: () => void;
  loading: boolean;
}

export const StaffFilters: React.FC<StaffFiltersProps> = ({
  searchTerm,
  setSearchTerm,
  selectedRole,
  setSelectedRole,
  selectedDepartment,
  setSelectedDepartment,
  statusFilter,
  setStatusFilter,
  roles,
  departments,
  onRefresh,
  loading
}) => {
  const clearFilters = () => {
    setSearchTerm('');
    setSelectedRole('');
    setSelectedDepartment('');
    setStatusFilter('all');
  };

  const hasActiveFilters = searchTerm || selectedRole || selectedDepartment || statusFilter !== 'all';

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Filter className="w-5 h-5 text-gray-500" />
          <h3 className="text-lg font-medium text-gray-900">Filter Staff</h3>
          {hasActiveFilters && (
            <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
              Filters Active
            </span>
          )}
        </div>
        <div className="flex space-x-2">
          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-sm text-gray-600 hover:text-gray-800 underline"
            >
              Clear Filters
            </button>
          )}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="flex items-center space-x-1 px-3 py-1 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md disabled:opacity-50"
            title="Refresh staff list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Search Box */}
        <div className="lg:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Search Staff</label>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by name, ID, phone, or email..."
              className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        {/* Role Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Role</label>
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Roles</option>
            {roles.map(role => (
              <option key={role} value={role}>{role}</option>
            ))}
          </select>
        </div>

        {/* Department Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Department</label>
          <select
            value={selectedDepartment}
            onChange={(e) => setSelectedDepartment(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Departments</option>
            {departments.map(dept => (
              <option key={dept} value={dept}>{dept}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Additional Filters Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
        {/* Status Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">All Status</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive Only</option>
          </select>
        </div>

        {/* Quick Role Buttons */}
        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Quick Filters</label>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedRole('Nurse')}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                selectedRole === 'Nurse'
                  ? 'bg-green-100 text-green-800 border-green-300'
                  : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
              }`}
            >
              Nurses
            </button>
            <button
              onClick={() => setSelectedRole('Consultant')}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                selectedRole === 'Consultant'
                  ? 'bg-blue-100 text-blue-800 border-blue-300'
                  : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
              }`}
            >
              Doctors
            </button>
            <button
              onClick={() => setSelectedRole('Technician')}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                selectedRole === 'Technician'
                  ? 'bg-yellow-100 text-yellow-800 border-yellow-300'
                  : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
              }`}
            >
              Technicians
            </button>
            <button
              onClick={() => setSelectedRole('Admin')}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                selectedRole.includes('Admin')
                  ? 'bg-red-100 text-red-800 border-red-300'
                  : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
              }`}
            >
              Admins
            </button>
          </div>
        </div>
      </div>

      {/* Results Summary */}
      {hasActiveFilters && (
        <div className="mt-4 p-3 bg-blue-50 rounded-md">
          <p className="text-sm text-blue-800">
            <span className="font-medium">Active filters:</span>
            {searchTerm && <span className="ml-1">Search: "{searchTerm}"</span>}
            {selectedRole && <span className="ml-1">Role: {selectedRole}</span>}
            {selectedDepartment && <span className="ml-1">Department: {selectedDepartment}</span>}
            {statusFilter !== 'all' && <span className="ml-1">Status: {statusFilter}</span>}
          </p>
        </div>
      )}
    </div>
  );
};