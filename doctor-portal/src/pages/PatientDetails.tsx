import { useState, useRef, useEffect } from 'react';
import { useDoctorContext } from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Badge } from '@shared/ui/Badge';
import { EmptyState } from '@shared/ui/EmptyState';
import { HeartPulse, MessageSquare, Send, Activity, User, MapPin, Clock, Stethoscope, FileText, Beaker, Download } from 'lucide-react';
import { api as axios } from '../lib/api';
import { toast } from 'react-hot-toast';

export default function PatientDetails() {
  const { activePatientId, messages, chatInput, setChatInput, sendMessage, historicalReadings, liveVitals, doctorVisits } = useDoctorContext();
  const [activeTab, setActiveTab] = useState<'vitals' | 'messages' | 'clinical'>('vitals');
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [prescriptions, setPrescriptions] = useState<any[]>([]);
  const [labs, setLabs] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [clinicalLoading, setClinicalLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (activeTab === 'clinical' && activePatientId) {
      const scopedVisit = doctorVisits.find(v => v.patient_id === activePatientId);
      if (!scopedVisit?.hospital_id) {
        toast.error('Clinical access requires an active hospital context for this patient.');
        return;
      }

      const fetchClinicalData = async () => {
        setClinicalLoading(true);
        const token = localStorage.getItem('token');
        const headers = { Authorization: `Bearer ${token}` };
        const params = {
          purpose: 'TREATMENT',
          hospital_id: scopedVisit.hospital_id,
        };
        try {
          const [prescRes, labsRes, notesRes] = await Promise.all([
            axios.get(`/api/clinical/prescriptions/patient/${activePatientId}`, { headers, params }),
            axios.get(`/api/clinical/labs/patient/${activePatientId}`, { headers, params }),
            axios.get(`/api/clinical/notes/patient/${activePatientId}`, { headers, params })
          ]);
          setPrescriptions(prescRes.data);
          setLabs(labsRes.data);
          setNotes(notesRes.data);
        } catch (error) {
          console.error(error);
          toast.error('Failed to load clinical history or access denied.');
        } finally {
          setClinicalLoading(false);
        }
      };
      fetchClinicalData();
    }
  }, [activeTab, activePatientId, doctorVisits]);

  const handleExportFHIR = async () => {
    if (!activePatientId) return;
    setExporting(true);
    const token = localStorage.getItem('token');
    const headers = { Authorization: `Bearer ${token}` };
    try {
      // Provider interoperability is deliberately consent-bound. The doctor must
      // select/enter the consent granted to this doctor before an export can run.
      const rawConsentId = window.prompt('Enter the patient consent ID authorizing this FHIR export:');
      if (!rawConsentId) return;
      const consentId = Number(rawConsentId);
      if (!Number.isInteger(consentId) || consentId <= 0) {
        toast.error('Enter a valid consent ID.');
        return;
      }

      const params = new URLSearchParams({
        purpose: 'TREATMENT',
        consent_id: String(consentId),
      });
      const res = await axios.get(`/api/interoperability/patients/${activePatientId}/export?${params.toString()}`, { headers });
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `patient_${activePatientId}_fhir_bundle.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('FHIR Bundle exported successfully');
    } catch (error) {
      console.error(error);
      toast.error('FHIR export denied or failed. Verify the consent ID and purpose.');
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'messages') chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeTab]);

  if (!activePatientId) {
    return <div className="flex h-[80vh] items-center justify-center animate-in fade-in"><EmptyState icon={<User className="h-12 w-12 text-slate-300" />} title="No Patient Selected" description="Select a patient from the My Patients list or Triage Queue to view details." /></div>;
  }

  const activeVisit = doctorVisits.find(v => v.patient_id === activePatientId);
  const liveData = liveVitals[activePatientId];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-in slide-in-from-bottom-4 duration-500">
      <div className="lg:col-span-4 space-y-6">
        <Card className="border-t-4 border-t-blue-600 shadow-md"><CardContent className="p-6"><div className="flex items-start gap-4"><div className="h-16 w-16 rounded-full bg-blue-100 flex items-center justify-center shrink-0 border-4 border-white shadow-sm"><User className="h-8 w-8 text-blue-600" /></div><div><h2 className="text-xl font-bold text-slate-900">Patient #{activePatientId * 13}</h2><div className="text-sm font-mono text-slate-500 mt-0.5">ID: {activePatientId}</div>{activeVisit && <Badge variant={activeVisit.status === 'Active' ? 'default' : 'secondary'} className={`mt-2 ${activeVisit.status === 'Active' ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100' : ''} border-none`}>{activeVisit.status}</Badge>}</div></div><div className="mt-8 space-y-4"><div className="flex items-start gap-3"><MapPin className="h-5 w-5 text-slate-400 mt-0.5" /><div><p className="text-xs font-semibold text-slate-500 uppercase">Hospital</p><p className="text-sm text-slate-900">{activeVisit?.hospital?.name || 'Unknown Location'}</p></div></div><div className="flex items-start gap-3"><Stethoscope className="h-5 w-5 text-slate-400 mt-0.5" /><div><p className="text-xs font-semibold text-slate-500 uppercase">Primary Reason</p><p className="text-sm text-slate-900">{activeVisit?.reason || 'Not specified'}</p></div></div></div></CardContent></Card>
        <Card><CardHeader className="pb-2 border-b border-slate-100"><CardTitle className="text-sm flex items-center justify-between">Current Vitals{liveData && <span className="flex h-2 w-2 rounded-full bg-rose-500 animate-pulse" />}</CardTitle></CardHeader><CardContent className="p-4 bg-slate-50">{liveData ? <div className="grid grid-cols-2 gap-4"><div className="bg-white p-3 rounded-lg border border-slate-200 text-center"><p className="text-xs text-slate-500 uppercase font-semibold">HR</p><p className="text-2xl font-bold text-slate-900">{liveData.heart_rate} <span className="text-xs text-slate-400 font-normal">bpm</span></p></div><div className="bg-white p-3 rounded-lg border border-slate-200 text-center"><p className="text-xs text-slate-500 uppercase font-semibold">O2</p><p className="text-2xl font-bold text-slate-900">{liveData.oxygen_level} <span className="text-xs text-slate-400 font-normal">%</span></p></div><div className="bg-white p-3 rounded-lg border border-slate-200 text-center col-span-2"><p className="text-xs text-slate-500 uppercase font-semibold">Blood Pressure</p><p className="text-2xl font-bold text-slate-900">{liveData.blood_pressure_sys}/{liveData.blood_pressure_dia} <span className="text-xs text-slate-400 font-normal">mmHg</span></p></div></div> : <p className="text-sm text-slate-500 text-center py-4">No live vitals transmitting.</p>}</CardContent></Card>
      </div>

      <div className="lg:col-span-8 flex flex-col min-h-[600px]">
        <div className="flex items-center gap-2 mb-4 border-b border-slate-200 pb-px"><button onClick={() => setActiveTab('vitals')} className={`px-4 py-2 text-sm font-medium border-b-2 ${activeTab === 'vitals' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500'}`}><div className="flex items-center gap-2"><Activity className="h-4 w-4" /> Vitals History</div></button><button onClick={() => setActiveTab('messages')} className={`px-4 py-2 text-sm font-medium border-b-2 ${activeTab === 'messages' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500'}`}><div className="flex items-center gap-2"><MessageSquare className="h-4 w-4" /> Direct Messages</div></button><button onClick={() => setActiveTab('clinical')} className={`px-4 py-2 text-sm font-medium border-b-2 ${activeTab === 'clinical' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500'}`}><div className="flex items-center gap-2"><FileText className="h-4 w-4" /> Clinical Records</div></button></div>
        {activeTab === 'vitals' && <Card className="flex-1 overflow-hidden flex flex-col"><CardHeader className="bg-slate-50 border-b border-slate-100"><CardTitle className="text-base flex items-center justify-between">Reading History<Badge variant="outline" className="bg-white">{historicalReadings.length} records</Badge></CardTitle></CardHeader><CardContent className="p-0 flex-1 overflow-y-auto bg-white">{historicalReadings.length === 0 ? <div className="p-12"><EmptyState icon={<HeartPulse className="h-10 w-10 text-slate-300" />} title="No vitals recorded" description="There is no historical vital data available for this patient." /></div> : <div className="divide-y divide-slate-100">{historicalReadings.map(r => <div key={r.id} className="p-4 hover:bg-slate-50 flex items-center justify-between"><div className="flex items-center gap-3"><Clock className="h-4 w-4 text-slate-400" /><span className="text-sm font-medium text-slate-700">{new Date(r.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>{r.is_simulated && <Badge variant="outline" className="text-[10px] bg-slate-100 h-5 px-1.5 border-none text-slate-500">SIM</Badge>}</div><div className="flex gap-4 md:gap-8 text-sm"><div className="text-center"><span className="text-slate-400 text-xs uppercase block">HR</span><span className="font-semibold text-slate-900">{r.heart_rate}</span></div><div className="text-center"><span className="text-slate-400 text-xs uppercase block">O2</span><span className="font-semibold text-slate-900">{r.oxygen_level}%</span></div><div className="text-center"><span className="text-slate-400 text-xs uppercase block">BP</span><span className="font-semibold text-slate-900">{r.blood_pressure_sys}/{r.blood_pressure_dia}</span></div></div></div>)}</div>}</CardContent></Card>}
        {activeTab === 'messages' && <Card className="flex-1 flex flex-col overflow-hidden"><div className="flex-1 overflow-y-auto p-4 bg-slate-50/50 space-y-4">{messages.length === 0 ? <div className="h-full flex items-center justify-center"><EmptyState icon={<MessageSquare className="h-10 w-10 text-slate-300" />} title="No messages yet" description="Send a message to the patient to start a secure conversation." /></div> : messages.map(m => { const isPatient = m.sender_id === activePatientId; return <div key={m.id} className={`flex flex-col ${isPatient ? 'items-start' : 'items-end'}`}><div className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm shadow-sm ${isPatient ? 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm' : 'bg-blue-600 text-white rounded-tr-sm'}`}>{m.content}</div><span className="text-[10px] text-slate-400 mt-1 font-medium mx-1">{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span></div> })}<div ref={chatEndRef} /></div><div className="p-4 bg-white border-t border-slate-200"><form onSubmit={sendMessage} className="flex gap-2 relative"><input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Type a secure message to the patient..." className="flex-1 border border-slate-300 rounded-full pl-4 pr-12 py-2.5 text-sm" disabled={!activePatientId} /><Button type="submit" size="icon" className="absolute right-1 top-1 bottom-1 h-auto rounded-full bg-blue-600 hover:bg-blue-700" disabled={!chatInput.trim()}><Send className="h-4 w-4" /></Button></form></div></Card>}
        {activeTab === 'clinical' && <Card className="flex-1 flex flex-col overflow-hidden bg-slate-50"><CardHeader className="bg-white border-b border-slate-100 py-3 px-4 flex-row items-center justify-between"><CardTitle className="text-sm">Patient Clinical History</CardTitle><Button variant="outline" size="sm" className="gap-2" onClick={handleExportFHIR} disabled={exporting || clinicalLoading}><Download className="h-4 w-4" />{exporting ? 'Exporting...' : 'Export FHIR'}</Button></CardHeader><CardContent className="p-4 overflow-y-auto">{clinicalLoading ? <div className="text-center py-12 text-slate-500 animate-pulse">Loading clinical history...</div> : <div className="space-y-6"><section><h3 className="font-semibold flex items-center gap-2 mb-3"><Beaker className="h-4 w-4" /> Lab Results</h3>{labs.length ? labs.map(lab => <div key={lab.id} className="p-3 mb-2 bg-white rounded-lg border"><div className="flex justify-between"><span className="font-medium">{lab.test_name}</span><span className="text-xs text-slate-500">{new Date(lab.test_date).toLocaleDateString()}</span></div><div className="text-sm mt-1">{lab.result_value} {lab.unit}</div></div>) : <p className="text-sm text-slate-500">No lab results found.</p>}</section><section><h3 className="font-semibold flex items-center gap-2 mb-3"><Activity className="h-4 w-4" /> Prescriptions</h3>{prescriptions.length ? prescriptions.map(rx => <div key={rx.id} className="p-3 mb-2 bg-white rounded-lg border"><div className="flex justify-between"><span className="font-medium">Rx ID: {rx.id}</span><Badge variant="outline">{rx.is_active ? 'Active' : 'Completed'}</Badge></div><div className="text-sm mt-1">{rx.dosage} {rx.frequency}</div></div>) : <p className="text-sm text-slate-500">No prescriptions found.</p>}</section><section><h3 className="font-semibold flex items-center gap-2 mb-3"><FileText className="h-4 w-4" /> Clinical Notes</h3>{notes.length ? notes.map(note => <div key={note.id} className="p-3 mb-2 bg-white rounded-lg border"><div className="font-medium">{note.title}</div><p className="text-xs text-slate-600 mt-1 line-clamp-2">{note.content}</p></div>) : <p className="text-sm text-slate-500">No notes found.</p>}</section></div>}</CardContent></Card>}
      </div>
    </div>
  );
}
