import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { Search, Building, CheckCircle2, XCircle, Plus } from 'lucide-react';

export default function Staff() {
  const [staff, setStaff] = useState<any[]>([]);
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [orgLoading, setOrgLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedOrgId, setSelectedOrgId] = useState<string>('');
  const [showModal, setShowModal] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('doctor');
  const [error, setError] = useState('');

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const isPlatformAdmin = user.role === 'platform_admin';
  const membershipOrgId = user.memberships?.[0]?.hospital_id;
  const orgId = isPlatformAdmin ? selectedOrgId : membershipOrgId;

  useEffect(() => {
    if (!isPlatformAdmin) { setOrgLoading(false); return; }
    const fetchOrganizations = async () => {
      try {
        const res = await api.get('/api/hospitals');
        setOrganizations(res.data || []);
        if (!selectedOrgId && res.data?.length) setSelectedOrgId(String(res.data[0].id));
      } catch (err) { console.error(err); }
      finally { setOrgLoading(false); }
    };
    fetchOrganizations();
  }, [isPlatformAdmin]);

  useEffect(() => { fetchStaff(); }, [orgId]);

  const fetchStaff = async () => {
    if (!orgId) { setStaff([]); setLoading(false); return; }
    setLoading(true);
    try {
      const res = await api.get('/api/admin/staff', { params: { hospital_id: orgId } });
      setStaff(res.data || []);
    } catch (err) { console.error(err); setStaff([]); }
    finally { setLoading(false); }
  };

  const resetModal = () => {
    setShowModal(false); setNewEmail(''); setNewFullName(''); setNewPassword(''); setNewRole('doctor'); setError('');
  };

  const handleProvision = async () => {
    if (!newEmail || !orgId) return;
    if (newPassword.length < 12) { setError('Initial password must be at least 12 characters'); return; }
    setError('');
    try {
      await api.post('/api/admin/staff', { email: newEmail, full_name: newFullName || undefined, password: newPassword, role: newRole }, { params: { hospital_id: orgId } });
      resetModal();
      fetchStaff();
    } catch (err: any) { setError(err.response?.data?.detail || 'Provision failed'); }
  };

  const handleChangeRole = async (membershipId: number, role: string) => {
    try { await api.put(`/api/admin/staff/${membershipId}`, { role }, { params: { hospital_id: orgId } }); fetchStaff(); }
    catch (err: any) { setError(err.response?.data?.detail || 'Role update failed'); }
  };

  const handleRemove = async (membershipId: number) => {
    if (!window.confirm('Deactivate this staff membership?')) return;
    try { await api.delete(`/api/admin/staff/${membershipId}`, { params: { hospital_id: orgId } }); fetchStaff(); }
    catch (err: any) { setError(err.response?.data?.detail || 'Deactivation failed'); }
  };

  const filteredStaff = staff.filter(s => s.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) || s.email?.toLowerCase().includes(searchTerm.toLowerCase()));

  if (isPlatformAdmin && orgLoading) return <div className="p-12 text-center text-slate-500">Loading organizations...</div>;
  if (!orgId) return <div className="p-12 text-center flex flex-col items-center bg-white rounded-2xl border border-slate-200 shadow-sm mt-8"><Building className="h-12 w-12 text-slate-300 mb-4" /><h3 className="text-lg font-bold text-slate-900">Organization Required</h3><p className="text-slate-500 mt-2 max-w-md">Select an organization before managing its staff.</p></div>;

  const selectedOrg = organizations.find(o => String(o.id) === String(orgId));
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4"><div><h2 className="text-2xl font-bold text-slate-900 tracking-tight">Staff Directory</h2><p className="text-slate-500 mt-1 font-medium">Manage practitioner access and organization roles.</p></div><div className="flex items-center gap-3">{isPlatformAdmin && <select value={selectedOrgId} onChange={e => setSelectedOrgId(e.target.value)} className="px-3 py-2.5 border border-slate-200 rounded-xl bg-white text-sm font-medium">{organizations.map(org => <option key={org.id} value={org.id}>{org.name}</option>)}</select>}<button onClick={() => { setError(''); setShowModal(true); }} className="px-4 py-2.5 bg-blue-600 text-white font-medium text-sm rounded-xl hover:bg-blue-700"><span className="flex items-center gap-2"><Plus className="h-4 w-4" />Provision Account</span></button></div></div>
      {selectedOrg && <div className="text-sm text-slate-500">Managing staff for <span className="font-semibold text-slate-700">{selectedOrg.name}</span></div>}
      {error && !showModal && <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"><div className="p-4 border-b border-slate-200 bg-slate-50/50"><div className="relative w-full max-w-md"><div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Search className="h-4 w-4 text-slate-400" /></div><input type="text" placeholder="Search by name or email..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="w-full !pl-10 pr-4 py-2 border border-slate-200 rounded-xl bg-white text-sm" /></div></div><div className="overflow-x-auto"><table className="w-full text-left border-collapse"><thead><tr className="bg-slate-50/80 border-b border-slate-200 text-xs uppercase tracking-wider text-slate-500 font-bold"><th className="p-4 pl-6">Practitioner</th><th className="p-4">Contact</th><th className="p-4">Role</th><th className="p-4">Status</th><th className="p-4 pr-6 text-right">Actions</th></tr></thead><tbody className="divide-y divide-slate-100">{loading ? <tr><td colSpan={5} className="p-12 text-center">Loading...</td></tr> : filteredStaff.length === 0 ? <tr><td colSpan={5} className="p-12 text-center text-slate-500">No staff found.</td></tr> : filteredStaff.map(s => <tr key={s.membership_id} className="hover:bg-slate-50/50"><td className="p-4 pl-6 font-medium text-slate-900">{s.full_name}</td><td className="p-4 text-slate-500">{s.email}</td><td className="p-4"><select value={s.role} onChange={e => handleChangeRole(s.membership_id, e.target.value)} className="border border-slate-200 rounded px-2 py-1 text-sm bg-white"><option value="admin">Admin</option><option value="doctor">Doctor</option><option value="staff">Staff</option></select></td><td className="p-4">{s.is_active ? <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-emerald-50 text-emerald-700 border border-emerald-200"><CheckCircle2 className="h-3.5 w-3.5" />Active</span> : <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs bg-red-50 text-red-700 border border-red-200"><XCircle className="h-3.5 w-3.5" />Inactive</span>}</td><td className="p-4 pr-6 text-right">{s.is_active && <button onClick={() => handleRemove(s.membership_id)} className="text-sm text-red-600 hover:text-red-800 font-medium">Deactivate</button>}</td></tr>)}</tbody></table></div></div>
      {showModal && <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"><div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl"><h3 className="text-xl font-bold text-slate-900 mb-4">Provision Staff Account</h3>{error && <div className="mb-4 text-red-600 text-sm font-medium">{error}</div>}<div className="space-y-4"><div><label className="block text-sm font-medium text-slate-700 mb-1">Email Address</label><input type="email" value={newEmail} onChange={e => setNewEmail(e.target.value)} className="w-full px-4 py-2 border border-slate-200 rounded-xl" placeholder="doctor@hospital.com" /></div><div><label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label><input type="text" value={newFullName} onChange={e => setNewFullName(e.target.value)} className="w-full px-4 py-2 border border-slate-200 rounded-xl" placeholder="Dr. Jane Doe" /></div><div><label className="block text-sm font-medium text-slate-700 mb-1">Initial Password</label><input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} className="w-full px-4 py-2 border border-slate-200 rounded-xl" placeholder="At least 12 characters" autoComplete="new-password" /></div><div><label className="block text-sm font-medium text-slate-700 mb-1">Role</label><select value={newRole} onChange={e => setNewRole(e.target.value)} className="w-full px-4 py-2 border border-slate-200 rounded-xl"><option value="doctor">Doctor</option><option value="admin">Administrator</option><option value="staff">Support Staff</option></select></div></div><div className="mt-6 flex justify-end gap-3"><button onClick={resetModal} className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-100 rounded-xl">Cancel</button><button onClick={handleProvision} className="px-4 py-2 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700">Provision Account</button></div></div></div>}
    </div>
  );
}
