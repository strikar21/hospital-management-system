import React from 'react';
import { User, Edit, Trash2 } from 'lucide-react';

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

interface StaffListProps {
  staff: Staff[];
  loading: boolean;
  onEdit: (staff: Staff) => void;
  onDelete: (staffId: string, name: string) => void;
}

export const StaffList: React.FC<StaffListProps> = ({
  staff,
  loading,
  onEdit,
  onDelete
}) => {
  const getRoleColor = (role: string) => {
    if (role.includes('Admin') || role === 'Master Admin') return 'bg-red-100 text-red-800';
    if (role === 'Provisioner') return 'bg-purple-100 text-purple-800';
    if (role.includes('Consultant') || role.includes('Director') || role.includes('Chief')) return 'bg-blue-100 text-blue-800';
    if (role.includes('Nurse')) return 'bg-green-100 text-green-800';
    if (role.includes('Technician')) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Staff Directory</h2>
        </div>
        <div className="p-8 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading staff...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Staff Directory</h2>
        <p className="text-sm text-gray-600">Total staff members: {staff.length}</p>
      </div>

      {staff.length === 0 ? (
        <div className="text-center py-12">
          <User className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <p className="text-gray-500 text-lg">No staff members found</p>
          <p className="text-gray-400 text-sm">Add staff members to get started</p>
        </div>
      ) : (
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
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getRoleColor(member.role)}`}>
                      {member.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{member.department}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">
                      {member.phone && (
                        <div className="flex items-center">
                          <span className="text-gray-500">📞</span>
                          <span className="ml-1">{member.phone}</span>
                        </div>
                      )}
                      {member.email && (
                        <div className="flex items-center mt-1">
                          <span className="text-gray-500">📧</span>
                          <span className="ml-1 text-xs">{member.email}</span>
                        </div>
                      )}
                      {!member.phone && !member.email && (
                        <span className="text-gray-400 text-sm">No contact info</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      member.isActive
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {member.isActive ? 'Active' : 'Inactive'}
                    </span>
                    <div className="text-xs text-gray-500 mt-1">
                      Added: {new Date(member.createdAt).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => onEdit(member)}
                        className="text-indigo-600 hover:text-indigo-900 p-1 rounded hover:bg-indigo-50"
                        title="Edit staff member"
                      >
                        <Edit className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => onDelete(member.staffId, member.name)}
                        className="text-red-600 hover:text-red-900 p-1 rounded hover:bg-red-50"
                        title="Delete staff member"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};