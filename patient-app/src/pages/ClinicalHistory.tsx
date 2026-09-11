import React, { useState, useEffect } from 'react';
import { api as axios } from '../lib/api';
import { Activity, Beaker, FileText, Download } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function ClinicalHistory() {
  const [prescriptions, setPrescriptions] = useState<any[]>([]);
  const [labs, setLabs] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const userRes = await axios.get('/api/auth/me', { headers });
        const patientId = userRes.data.id;
        
        const [prescRes, labsRes, notesRes] = await Promise.all([
          axios.get(`/api/clinical/prescriptions/patient/${patientId}`, { headers }),
          axios.get(`/api/clinical/labs/patient/${patientId}`, { headers }),
          axios.get(`/api/clinical/notes/patient/${patientId}`, { headers })
        ]);
        
        setPrescriptions(prescRes.data);
        setLabs(labsRes.data);
        setNotes(notesRes.data);
      } catch (error) {
        console.error(error);
        toast.error('Failed to load clinical history');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleExportFHIR = async () => {
    setExporting(true);
    try {
      const userRes = await axios.get('/api/auth/me', { headers });
      const patientId = userRes.data.id;
      
      const res = await axios.get(`/api/interoperability/patients/${patientId}/export`, { headers });
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `patient_${patientId}_fhir_bundle.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('FHIR Bundle exported successfully');
    } catch (error) {
      console.error(error);
      toast.error('Failed to export FHIR Bundle');
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-500 animate-pulse">Loading clinical history...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-6 rounded-xl border border-border shadow-sm">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Activity className="h-6 w-6 text-primary" />
            Clinical History
          </h2>
          <p className="text-sm text-slate-500 mt-1">View your prescriptions, lab results, and clinical notes.</p>
        </div>
        <button 
          onClick={handleExportFHIR}
          disabled={exporting}
          className="flex items-center gap-2 bg-slate-900 text-white px-4 py-2 rounded-lg hover:bg-slate-800 transition-colors disabled:opacity-50"
        >
          <Download className="h-4 w-4" />
          {exporting ? 'Exporting...' : 'Export FHIR Bundle'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl border border-border shadow-sm p-6">
          <h3 className="font-semibold text-slate-900 flex items-center gap-2 mb-4">
            <Beaker className="h-5 w-5 text-emerald-500" /> Lab Results
          </h3>
          <div className="space-y-4">
            {labs.length === 0 ? <p className="text-sm text-slate-500 italic">No lab results found.</p> : labs.map(lab => (
              <div key={lab.id} className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <div className="flex justify-between items-start">
                  <span className="font-medium text-sm text-slate-900">{lab.test_name}</span>
                  <span className="text-xs text-slate-500">{new Date(lab.test_date).toLocaleDateString()}</span>
                </div>
                <div className="mt-2 text-sm text-slate-700">
                  <span className="font-semibold">{lab.result_value}</span> {lab.unit}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-border shadow-sm p-6">
          <h3 className="font-semibold text-slate-900 flex items-center gap-2 mb-4">
            <Activity className="h-5 w-5 text-primary" /> Prescriptions
          </h3>
          <div className="space-y-4">
            {prescriptions.length === 0 ? <p className="text-sm text-slate-500 italic">No prescriptions found.</p> : prescriptions.map(rx => (
              <div key={rx.id} className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <div className="flex justify-between items-start">
                  <span className="font-medium text-sm text-slate-900">Rx ID: {rx.id}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${rx.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'}`}>
                    {rx.is_active ? 'Active' : 'Completed'}
                  </span>
                </div>
                <div className="mt-2 text-sm text-slate-700">
                  {rx.dosage} {rx.frequency}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-border shadow-sm p-6">
          <h3 className="font-semibold text-slate-900 flex items-center gap-2 mb-4">
            <FileText className="h-5 w-5 text-blue-500" /> Clinical Notes
          </h3>
          <div className="space-y-4">
            {notes.length === 0 ? <p className="text-sm text-slate-500 italic">No notes found.</p> : notes.map(note => (
              <div key={note.id} className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <div className="font-medium text-sm text-slate-900">{note.title}</div>
                <p className="text-xs text-slate-600 mt-1 line-clamp-2">{note.content}</p>
                <div className="mt-2 text-[10px] text-slate-400">
                  {new Date(note.created_at).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
