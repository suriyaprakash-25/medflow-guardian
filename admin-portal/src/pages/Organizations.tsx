import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { Building, Plus, Search, CheckCircle2, XCircle } from 'lucide-react';

export default function Organizations() {
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [error, setError] = useState('');

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const isPlatformAdmin = user.role === 'platform_admin';

  useEffect(() => {
    fetchOrgs();
  }, []);

  const fetchOrgs = async () => {
    try {
      const res = await api.get('/api/hospitals');
      setOrganizations(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateOrg = async () => {
    if (!newOrgName) return;
    try {
      await api.post('/api/admin/organization', { name: newOrgName, is_active: true });
      setShowModal(false);
      setNewOrgName('');
      fetchOrgs();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create organization');
    }
  };

  if (!isPlatformAdmin) {
    return (
      <div className="p-12 text-center flex flex-col items-center bg-white rounded-2xl border border-slate-200 shadow-sm mt-8">
        <Building className="h-12 w-12 text-slate-300 mb-4" />
        <h3 className="text-lg font-bold text-slate-900">Access Denied</h3>
        <p className="text-slate-500 mt-2 max-w-md">Only Platform Administrators can manage organizations.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Organizations</h2>
          <p className="text-slate-500 mt-1 font-medium">Manage hospitals and clinical networks.</p>
        </div>
        <button 
          onClick={() => setShowModal(true)}
          className="px-4 py-2.5 bg-blue-600 text-white font-medium text-sm rounded-xl hover:bg-blue-700 transition-colors shadow-sm shadow-blue-500/20"
        >
          <div className="flex items-center gap-2">
            <Plus className="h-4 w-4" />
            Provision Organization
          </div>
        </button>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row gap-4 items-center justify-between">
            <div className="relative w-full max-w-md">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-4 w-4 text-slate-400" />
                </div>
                <input
                    type="text"
                    placeholder="Search organizations..."
                    className="w-full !pl-10 pr-4 py-2 border border-slate-200 rounded-xl bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                />
            </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-xs uppercase tracking-wider text-slate-500 font-bold">
                <th className="p-4 pl-6 font-semibold">Name</th>
                <th className="p-4 font-semibold">Status</th>
                <th className="p-4 pr-6 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                    <td colSpan={3} className="p-12 text-center">Loading...</td>
                </tr>
              ) : organizations.map((org: any) => (
                <tr key={org.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="p-4 pl-6">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-700 font-bold flex items-center justify-center">
                        {org.name.charAt(0)}
                      </div>
                      <div>
                        <div className="font-medium text-slate-900">{org.name}</div>
                        <div className="text-xs text-slate-500">ID: {org.id}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    {org.is_active ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Active
                        </span>
                    ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
                            <XCircle className="h-3.5 w-3.5" />
                            Inactive
                        </span>
                    )}
                  </td>
                  <td className="p-4 pr-6 text-right">
                    <button className="text-sm text-blue-600 hover:text-blue-800 font-medium">Edit</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center">
            <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl animate-in zoom-in-95 duration-200">
                <h3 className="text-xl font-bold text-slate-900 mb-4">Provision Organization</h3>
                {error && <div className="mb-4 text-red-600 text-sm font-medium">{error}</div>}
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Organization Name</label>
                        <input
                            type="text"
                            value={newOrgName}
                            onChange={(e) => setNewOrgName(e.target.value)}
                            className="w-full px-4 py-2 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                            placeholder="e.g. MedFlow General Hospital"
                        />
                    </div>
                </div>
                <div className="mt-6 flex justify-end gap-3">
                    <button onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-xl">Cancel</button>
                    <button onClick={handleCreateOrg} className="px-4 py-2 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700">Provision</button>
                </div>
            </div>
        </div>
      )}
    </div>
  );
}
