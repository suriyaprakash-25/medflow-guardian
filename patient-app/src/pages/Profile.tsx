import React, { useState } from 'react';
import { usePatientContext } from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Badge } from '@shared/ui/Badge';
import { History, ShieldCheck, Stethoscope, Building, Activity, AlertCircle, Settings, Save, User as UserIcon, Phone, HeartPulse } from 'lucide-react';
import { EmptyState } from '@shared/ui/EmptyState';
import { Input } from '@shared/ui/Input';
import { Label } from '@shared/ui/Label';
import { Button } from '@shared/ui/Button';
import { toast } from 'react-hot-toast';
import { api as axios } from '../lib/api';

export default function Profile() {
  const { patientVisits, requests, auditLogs, patientProfile, setPatientProfile } = usePatientContext();
  const [activeTab, setActiveTab] = useState<'visits' | 'triage' | 'security' | 'settings'>('settings');

  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    full_name: '',
    phone_number: '',
    date_of_birth: '',
    address: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
    blood_type: '',
    allergies: '',
    medical_history: ''
  });

  // Load patientProfile into form state when available
  React.useEffect(() => {
    if (patientProfile) {
      setFormData({
        full_name: patientProfile.full_name || '',
        phone_number: patientProfile.phone_number || '',
        date_of_birth: patientProfile.patient_profile?.date_of_birth || '',
        address: patientProfile.patient_profile?.address || '',
        emergency_contact_name: patientProfile.patient_profile?.emergency_contact_name || '',
        emergency_contact_phone: patientProfile.patient_profile?.emergency_contact_phone || '',
        blood_type: patientProfile.patient_profile?.blood_type || '',
        allergies: patientProfile.patient_profile?.allergies || '',
        medical_history: patientProfile.patient_profile?.medical_history || ''
      });
    }
  }, [patientProfile]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const res = await axios.post('/api/users/patient-profile', formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPatientProfile(res.data);
      toast.success('Profile updated successfully!');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-500">
      
      {/* Top Banner / Identity */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-center gap-6">
        <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center text-primary border-4 border-white shadow-sm shrink-0">
          <UserIcon />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-slate-900 m-0">{patientProfile?.full_name || 'Patient Identity'}</h2>
          <p className="text-slate-500 mt-1">{patientProfile?.email || 'Manage your health history and security settings.'}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-6">
        <button 
          onClick={() => setActiveTab('settings')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'settings' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
        >
          <div className="flex items-center gap-2"><Settings className="h-4 w-4" /> Profile Settings</div>
        </button>
        <button 
          onClick={() => setActiveTab('visits')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'visits' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
        >
          <div className="flex items-center gap-2"><Stethoscope className="h-4 w-4" /> Hospital Visits</div>
        </button>
        <button 
          onClick={() => setActiveTab('triage')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'triage' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
        >
          <div className="flex items-center gap-2"><Activity className="h-4 w-4" /> Triage History</div>
        </button>
        <button 
          onClick={() => setActiveTab('security')}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${activeTab === 'security' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
        >
          <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> Security Audit Logs</div>
        </button>
      </div>

      {/* Content */}
      <div className="mt-2">
        {activeTab === 'settings' && (
          <div className="animate-in fade-in slide-in-from-bottom-2">
            <form onSubmit={handleSaveProfile} className="space-y-6">
              
              <Card>
                <CardHeader className="border-b border-slate-100 bg-slate-50/50 pb-4">
                  <CardTitle className="text-base flex items-center gap-2 text-slate-800">
                    <UserIcon className="h-5 w-5 text-primary" /> Personal Information
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="full_name">Full Name</Label>
                    <Input id="full_name" name="full_name" value={formData.full_name} onChange={handleInputChange} placeholder="John Doe" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="date_of_birth">Date of Birth</Label>
                    <Input id="date_of_birth" name="date_of_birth" type="date" value={formData.date_of_birth} onChange={handleInputChange} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone_number">Phone Number</Label>
                    <Input id="phone_number" name="phone_number" type="tel" value={formData.phone_number} onChange={handleInputChange} placeholder="+1 (555) 000-0000" />
                  </div>
                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="address">Address</Label>
                    <Input id="address" name="address" value={formData.address} onChange={handleInputChange} placeholder="123 Medical Way, Health City, HC 12345" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="border-b border-slate-100 bg-slate-50/50 pb-4">
                  <CardTitle className="text-base flex items-center gap-2 text-slate-800">
                    <Phone className="h-5 w-5 text-red-500" /> Emergency Contact
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="emergency_contact_name">Contact Name</Label>
                    <Input id="emergency_contact_name" name="emergency_contact_name" value={formData.emergency_contact_name} onChange={handleInputChange} placeholder="Jane Doe (Spouse)" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="emergency_contact_phone">Contact Phone</Label>
                    <Input id="emergency_contact_phone" name="emergency_contact_phone" type="tel" value={formData.emergency_contact_phone} onChange={handleInputChange} placeholder="+1 (555) 111-1111" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="border-b border-slate-100 bg-slate-50/50 pb-4">
                  <CardTitle className="text-base flex items-center gap-2 text-slate-800">
                    <HeartPulse className="h-5 w-5 text-primary" /> Medical Profile
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="blood_type">Blood Type</Label>
                    <Input id="blood_type" name="blood_type" value={formData.blood_type} onChange={handleInputChange} placeholder="e.g. O+, A-, AB+" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="allergies">Known Allergies</Label>
                    <Input id="allergies" name="allergies" value={formData.allergies} onChange={handleInputChange} placeholder="e.g. Penicillin, Peanuts" />
                  </div>
                  <div className="space-y-2 md:col-span-2">
                    <Label htmlFor="medical_history">General Medical History / Notes</Label>
                    <textarea 
                      id="medical_history" 
                      name="medical_history" 
                      value={formData.medical_history} 
                      onChange={handleInputChange}
                      rows={4}
                      className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                      placeholder="List any chronic conditions, past surgeries, or ongoing treatments here."
                    />
                  </div>
                </CardContent>
              </Card>

              <div className="flex justify-end pt-4">
                <Button type="submit" disabled={saving} className="min-w-[150px] gap-2 shadow-sm">
                  {saving ? <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save className="h-4 w-4" />}
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>

            </form>
          </div>
        )}

        {activeTab === 'visits' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-in fade-in slide-in-from-bottom-2">
            {patientVisits.length === 0 ? (
              <div className="col-span-full">
                <EmptyState icon={<Building className="h-10 w-10 text-slate-300" />} title="No visits recorded" description="You have not been registered for any hospital visits." />
              </div>
            ) : (
              patientVisits.map(v => (
                <Card key={v.id} className="overflow-hidden">
                  <div className={`h-1.5 w-full ${v.status === 'completed' ? 'bg-emerald-400' : 'bg-primary'}`}></div>
                  <CardContent className="p-5">
                    <div className="flex justify-between items-start mb-3">
                      <h4 className="font-semibold text-slate-900 m-0">{v.hospital?.name}</h4>
                      <Badge className={v.status === 'completed' ? 'bg-emerald-100 text-emerald-800' : 'bg-primary/10 text-primary'}>
                        {v.status.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="text-sm text-slate-600 flex items-center gap-2 mb-2">
                      <Stethoscope className="h-4 w-4 text-slate-400" /> Dr. {v.doctor?.full_name}
                    </div>
                    <div className="text-sm text-slate-600 bg-slate-50 p-3 rounded-md border border-slate-100 mt-3">
                      <span className="font-medium text-slate-700 block mb-1">Reason for Visit:</span>
                      {v.reason}
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}

        {activeTab === 'triage' && (
          <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-2">
            {requests.length === 0 ? (
              <EmptyState icon={<History className="h-10 w-10 text-slate-300" />} title="No triage requests" description="You have not submitted any symptoms for triage." />
            ) : (
              requests.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).map(req => (
                <Card key={req.id}>
                  <CardContent className="p-5 flex flex-col sm:flex-row gap-6">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-sm text-slate-500 font-medium">
                          {new Date(req.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                        </span>
                        <Badge className="bg-slate-100 text-slate-700">{req.status.toUpperCase()}</Badge>
                      </div>
                      <p className="text-slate-800 text-sm mt-2 italic">"{req.symptoms}"</p>
                    </div>
                    
                    {req.priority && (
                      <div className="sm:w-1/3 bg-slate-50 rounded-lg p-4 border border-slate-100">
                        <div className="flex items-center gap-2 mb-2">
                          <Activity className="h-4 w-4 text-primary" />
                          <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">AI Assessment</span>
                          <Badge className={`ml-auto ${
                            req.priority === 'high' ? 'bg-red-100 text-red-800' :
                            req.priority === 'medium' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                          }`}>
                            {req.priority.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="text-xs text-slate-600 leading-relaxed mb-3">{req.ai_reasoning}</p>
                        {req.disclaimer && (
                          <p className="text-[10px] text-slate-400 italic flex items-start gap-1">
                            <AlertCircle className="h-3 w-3 shrink-0 mt-0.5" />
                            {req.disclaimer}
                          </p>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        )}

        {activeTab === 'security' && (
          <div className="animate-in fade-in slide-in-from-bottom-2">
            <Card>
              <CardHeader className="border-b border-slate-100 pb-4">
                <CardTitle className="text-base flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-slate-400" /> Security Event Log
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {auditLogs.length === 0 ? (
                  <div className="p-8"><EmptyState icon={<ShieldCheck className="h-10 w-10 text-slate-300" />} title="No audit logs" description="No security events have been recorded." /></div>
                ) : (
                  <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
                    {auditLogs.map(a => (
                      <div key={a.id} className="p-4 flex flex-col sm:flex-row justify-between sm:items-center gap-2 hover:bg-slate-50 transition-colors">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">{(a.operation || '').replace('_', ' ')}</span>
                          </div>
                          <p className="text-xs text-slate-500">
                            Actor Role: <span className="font-medium text-slate-700">{a.actor_role}</span> (ID: {a.actor_id})
                            {a.resource_id && <span className="ml-2 pl-2 border-l border-slate-300">Resource ID: {a.resource_id}</span>}
                          </p>
                        </div>
                        <span className="text-xs text-slate-400 whitespace-nowrap">
                          {new Date(a.timestamp).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

