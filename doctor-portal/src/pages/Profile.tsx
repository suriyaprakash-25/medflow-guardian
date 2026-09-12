import React, { useState } from 'react';
import { useDoctorContext } from '../lib/doctorContext';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Badge } from '@shared/ui/Badge';
import { EmptyState } from '@shared/ui/EmptyState';
import { ShieldCheck, History, Activity, AlertCircle, Clock, User, Mail, Save, Phone, Building } from 'lucide-react';
import toast from 'react-hot-toast';

import { api as axios } from '../lib/api';

interface ProfileUpdatePayload {
  full_name?: string;
  email?: string;
}

interface ProfileRequestError {
  response?: {
    data?: {
      detail?: string;
    };
  };
}

export default function Profile() {
  const { auditLogs, currentUser, setCurrentUser } = useDoctorContext();
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    fullName: currentUser?.full_name || '',
    email: currentUser?.email || '',
    phone: '+1 (555) 123-4567',
    hospital: 'General Hospital'
  });

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) {
      toast.error('Your user profile is not available yet.');
      return;
    }

    setLoading(true);
    try {
      const payload: ProfileUpdatePayload = {};
      if (formData.fullName.trim()) payload.full_name = formData.fullName.trim();
      if (formData.email.trim()) payload.email = formData.email.trim();

      await axios.patch('/api/auth/me', payload);
      
      setCurrentUser({
        ...currentUser,
        full_name: payload.full_name || currentUser.full_name,
        email: payload.email || currentUser.email
      });
      
      toast.success('Profile settings updated successfully');
    } catch (error) {
      const requestError = error as ProfileRequestError;
      toast.error(requestError.response?.data?.detail || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500 pb-12">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Doctor Profile</h2>
        <p className="text-sm text-slate-500 mt-1">Manage your clinical account, contact details, and security audit logs.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <Card className="border-t-4 border-t-blue-600">
            <CardHeader className="bg-slate-50/50 border-b border-slate-100">
              <CardTitle className="text-lg flex items-center gap-2">
                <User className="h-5 w-5 text-blue-600" />
                Personal Information
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <form onSubmit={handleSave}>
                <div className="p-6 space-y-6">
                  <div className="flex items-center gap-6 pb-6 border-b border-slate-100">
                    <div className="h-20 w-20 rounded-full bg-blue-100 flex items-center justify-center border-4 border-white shadow-md">
                      <User className="h-10 w-10 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-slate-900">Dr. {formData.fullName || 'Doctor'}</h3>
                      <p className="text-sm font-medium text-blue-600 uppercase tracking-wider mt-1">{currentUser?.role || 'Practitioner'}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <label className="text-sm font-semibold text-slate-700">Full Name</label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><User className="h-4 w-4 text-slate-400" /></div>
                        <input type="text" value={formData.fullName} onChange={(e) => setFormData({...formData, fullName: e.target.value})} className="w-full !pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 outline-none transition-all" />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-semibold text-slate-700">Email Address</label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Mail className="h-4 w-4 text-slate-400" /></div>
                        <input type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} className="w-full !pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 outline-none transition-all" />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-semibold text-slate-700">Phone Number</label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Phone className="h-4 w-4 text-slate-400" /></div>
                        <input type="text" value={formData.phone} onChange={(e) => setFormData({...formData, phone: e.target.value})} className="w-full !pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 outline-none transition-all" />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-semibold text-slate-700">Primary Hospital</label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Building className="h-4 w-4 text-slate-400" /></div>
                        <input type="text" value={formData.hospital} disabled className="w-full !pl-10 pr-4 py-2 border border-slate-200 rounded-lg text-sm bg-slate-100 text-slate-500 cursor-not-allowed" />
                      </div>
                      <p className="text-[10px] text-slate-500 mt-1">Hospital affiliation is managed by Admin.</p>
                    </div>
                  </div>
                </div>

                <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end">
                  <button type="submit" disabled={loading} className="flex items-center gap-2 px-5 py-2 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors disabled:opacity-50">
                    {loading ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save className="h-4 w-4" />}
                    Save Changes
                  </button>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="bg-slate-50/50 border-b border-slate-100 pb-4">
              <CardTitle className="text-lg flex items-center gap-2"><History className="h-5 w-5 text-slate-500" />Security Audit Logs</CardTitle>
              <p className="text-xs text-slate-500 mt-1">Immutable ledger of your system interactions.</p>
            </CardHeader>
            <CardContent className="p-0">
              {auditLogs.length === 0 ? (
                <div className="p-12"><EmptyState icon={<ShieldCheck className="h-10 w-10 text-slate-300" />} title="No audit logs found" description="Your account activity will appear here." /></div>
              ) : (
                <div className="divide-y divide-slate-100 max-h-[500px] overflow-y-auto">
                  {auditLogs.map(log => {
                    const isWarning = log.operation.includes('unauthorized') || log.operation.includes('failed');
                    return (
                      <div key={log.id} className="p-5 hover:bg-slate-50 transition-colors flex gap-4">
                        <div className="mt-0.5 shrink-0">
                          {isWarning ? (
                            <div className="h-8 w-8 rounded-full bg-rose-100 flex items-center justify-center"><AlertCircle className="h-4 w-4 text-rose-600" /></div>
                          ) : (
                            <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center"><Activity className="h-4 w-4 text-slate-500" /></div>
                          )}
                        </div>
                        <div className="flex-1 space-y-1">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div className="font-semibold text-sm text-slate-900 uppercase tracking-wide">{log.operation.replace(/_/g, ' ')}</div>
                            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 shrink-0"><Clock className="h-3 w-3" />{new Date(log.timestamp).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</div>
                          </div>
                          <div className="flex flex-wrap gap-2 pt-1">
                            {log.target_user_id && <Badge variant="outline" className="bg-white text-xs font-medium text-slate-600 border-slate-200">Target User ID: {log.target_user_id}</Badge>}
                            {log.document_id && <Badge variant="outline" className="bg-white text-xs font-medium text-slate-600 border-slate-200">Document ID: {log.document_id}</Badge>}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-1 space-y-6">
          <Card className="bg-gradient-to-br from-slate-900 to-slate-800 text-white border-none shadow-xl">
            <CardContent className="p-6">
              <div className="flex items-center gap-4 mb-6">
                <div className="p-3 bg-blue-500/20 rounded-xl"><ShieldCheck className="h-8 w-8 text-blue-400" /></div>
                <div><h3 className="font-bold text-lg">Account Security</h3><p className="text-slate-400 text-xs">CAE Protected Session</p></div>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between py-2 border-b border-slate-700/50"><span className="text-sm text-slate-300">Authentication</span><Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">Verified</Badge></div>
                <div className="flex items-center justify-between py-2 border-b border-slate-700/50"><span className="text-sm text-slate-300">2FA Status</span><Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">Active</Badge></div>
                <div className="flex items-center justify-between py-2"><span className="text-sm text-slate-300">Last Login</span><span className="text-xs text-slate-400">Just now</span></div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
