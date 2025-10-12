import { useState, useEffect, useCallback } from 'react';
import { StaffService } from '../services/StaffService';

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

interface UseStaffManagementOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export const useStaffManagement = (options: UseStaffManagementOptions = {}) => {
  const { autoRefresh = false, refreshInterval = 30000 } = options;

  // State
  const [staff, setStaff] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);

  // Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingStaff, setEditingStaff] = useState<Staff | null>(null);
  const [previewStaffId, setPreviewStaffId] = useState('');
  const [createdStaff, setCreatedStaff] = useState<CreatedStaff | null>(null);

  // Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRole, setSelectedRole] = useState('');
  const [selectedDepartment, setSelectedDepartment] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');

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

  // Fetch staff data
  const fetchStaff = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await StaffService.getAllStaff();
      setStaff(Array.isArray(data) ? data : []);
    } catch (error) {
      // Error fetching staff - handle silently
      setError('Failed to load staff members');
      setStaff([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch roles and departments
  const fetchRolesAndDepartments = useCallback(async () => {
    try {
      const [rolesData, deptsData] = await Promise.all([
        StaffService.getRoles(),
        StaffService.getDepartments()
      ]);

      setRoles(Array.isArray(rolesData) ? rolesData : []);
      setDepartments(Array.isArray(deptsData) ? deptsData : []);
    } catch (error) {
      // Error fetching roles/departments - handle silently
    }
  }, []);

  // Add staff member
  const addStaff = useCallback(async (staffData: NewStaff): Promise<boolean> => {
    setLoading(true);
    try {
      const result = await StaffService.addStaff(staffData);
      setCreatedStaff(result);
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
      await fetchStaff();
      return true;
    } catch (error: any) {
      // Error adding staff - handle silently
      setError(error?.message || 'Error adding staff member');
      return false;
    } finally {
      setLoading(false);
    }
  }, [fetchStaff]);

  // Edit staff member
  const editStaff = useCallback(async (staffData: Staff): Promise<boolean> => {
    setLoading(true);
    try {
      await StaffService.updateStaff(staffData.staffId, {
        name: staffData.name,
        role: staffData.role,
        department: staffData.department,
        nfcId: staffData.nfcId,
        phone: staffData.phone,
        email: staffData.email,
      });
      setEditingStaff(null);
      await fetchStaff();
      return true;
    } catch (error: any) {
      // Error updating staff - handle silently
      setError(error?.message || 'Error updating staff member');
      return false;
    } finally {
      setLoading(false);
    }
  }, [fetchStaff]);

  // Delete staff member
  const deleteStaff = useCallback(async (staffId: string): Promise<boolean> => {
    setLoading(true);
    try {
      await StaffService.deleteStaff(staffId);
      await fetchStaff();
      return true;
    } catch (error: any) {
      // Error deleting staff - handle silently
      setError(error?.message || 'Error deleting staff member');
      return false;
    } finally {
      setLoading(false);
    }
  }, [fetchStaff]);

  // Filter staff based on search and filters
  const filteredStaff = staff.filter(member => {
    const matchesSearch = !searchTerm ||
      member.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      member.staffId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      member.phone?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      member.email?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesRole = !selectedRole || member.role === selectedRole;
    const matchesDepartment = !selectedDepartment || member.department === selectedDepartment;
    const matchesStatus = statusFilter === 'all' ||
      (statusFilter === 'active' && member.isActive) ||
      (statusFilter === 'inactive' && !member.isActive);

    return matchesSearch && matchesRole && matchesDepartment && matchesStatus;
  });

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Clear created staff notification
  const clearCreatedStaff = useCallback(() => {
    setCreatedStaff(null);
  }, []);

  // Initial data load
  useEffect(() => {
    fetchStaff();
    fetchRolesAndDepartments();
  }, [fetchStaff, fetchRolesAndDepartments]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      if (!loading) {
        fetchStaff();
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, loading, fetchStaff]);

  return {
    // Data
    staff: filteredStaff,
    allStaff: staff,
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
    totalStaff: staff.length,
    filteredCount: filteredStaff.length,
    activeStaff: staff.filter(s => s.isActive).length,
    inactiveStaff: staff.filter(s => !s.isActive).length,
  };
};