import { useState } from 'react';
import { useDoctorContext } from '../lib/doctorContext';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Badge } from '@shared/ui/Badge';
import { EmptyState } from '@shared/ui/EmptyState';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { Activity, CheckCircle, Clock, AlertTriangle, ShieldAlert } from 'lucide-react';

const normalized = (value: string | null | undefined) => (value || '').trim().toLowerCase();

export default function DashboardView() {
  const { requests, updateStatus, isAdmin, adminData } = useDoctorContext();
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'pending'>('all');
  const [selectedRequestId, setSelectedRequestId] = useState<number | null>(null);
  const selectedRequest = requests.find((r) => r.id === selectedRequestId) || null;

  if (isAdmin) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">System overview</h2>
          <p className="mt-1 text-sm text-slate-600">Operational counts reported by the administrative API.</p>
        </div>
        {adminData ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ['Total users', adminData.total_users],
              ['Hospitals', adminData.total_hospitals],
              ['Triage requests', adminData.total_triage_requests],
              ['Active grants', adminData.active_grants],
            ].map(([label, value]) => (
              <Card key={label}>
                <CardHeader className="pb-2"><CardTitle className="text-sm font-medium text-slate-600">{label}</CardTitle></CardHeader>
                <CardContent><div className="text-3xl font-bold">{value}</div></CardContent>
              </Card>
            ))}
          </div>
        ) : <FeedbackState tone="loading" title="Loading operational counts" />}
      </div>
    );
  }

  const criticalCount = requests.filter((request) => normalized(request.priority) === 'critical' && normalized(request.status) !== 'resolved').length;
  const highCount = requests.filter((request) => normalized(request.priority) === 'high' && normalized(request.status) !== 'resolved').length;
  const pendingCount = requests.filter((request) => normalized(request.status) === 'pending').length;

  const filteredRequests = requests.filter((request) => {
    if (filter === 'critical') return normalized(request.priority) === 'critical';
    if (filter === 'high') return normalized(request.priority) === 'high';
    if (filter === 'pending') return normalized(request.status) === 'pending';
    return true;
  });

  const getPriorityBadge = (priority: string | null) => {
    switch (normalized(priority)) {
      case 'critical': return <Badge variant="destructive" className="border-none bg-rose-100 text-rose-800 hover:bg-rose-100">Critical screening flag</Badge>;
      case 'high': return <Badge variant="destructive" className="border-none bg-amber-100 text-amber-900 hover:bg-amber-100">High screening flag</Badge>;
      case 'medium': return <Badge variant="secondary" className="border-none bg-blue-100 text-blue-800 hover:bg-blue-100">Medium screening flag</Badge>;
      default: return <Badge variant="outline" className="border-none bg-slate-100 text-slate-700 hover:bg-slate-100">Low screening flag</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (normalized(status)) {
      case 'resolved': return <span className="flex items-center gap-1 text-xs font-semibold text-emerald-700"><CheckCircle className="h-3 w-3" aria-hidden="true" /> Resolved</span>;
      case 'under review': return <span className="flex items-center gap-1 text-xs font-semibold text-blue-700"><Activity className="h-3 w-3" aria-hidden="true" /> Under review</span>;
      case 'pending': return <span className="flex items-center gap-1 text-xs font-semibold text-amber-800"><Clock className="h-3 w-3" aria-hidden="true" /> Pending review</span>;
      default: return <span className="text-xs font-semibold text-slate-600">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      <FeedbackState
        tone="info"
        title="Triage priority is decision support, not a diagnosis"
        message="Priority and rationale come from deterministic symptom-keyword rules. Review the patient's report and clinical context before making care decisions."
        compact
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card className="border-l-4 border-l-rose-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">Critical screening flags</CardTitle>
            <ShieldAlert className="h-4 w-4 text-rose-600" aria-hidden="true" />
          </CardHeader>
          <CardContent><div className="text-3xl font-bold text-slate-900">{criticalCount}</div><p className="mt-1 text-xs text-slate-600">Clinician review required; follow local emergency protocol.</p></CardContent>
        </Card>
        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">High screening flags</CardTitle>
            <AlertTriangle className="h-4 w-4 text-amber-600" aria-hidden="true" />
          </CardHeader>
          <CardContent><div className="text-3xl font-bold text-slate-900">{highCount}</div><p className="mt-1 text-xs text-slate-600">Review according to your organization’s clinical protocol.</p></CardContent>
        </Card>
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-600">Pending review</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" aria-hidden="true" />
          </CardHeader>
          <CardContent><div className="text-3xl font-bold text-slate-900">{pendingCount}</div><p className="mt-1 text-xs text-slate-600">Reports not yet marked under review or resolved.</p></CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <CardHeader className="flex flex-col gap-4 border-b border-slate-100 bg-slate-50/50 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-lg">Triage queue</CardTitle>
            <p className="mt-1 text-sm text-slate-600">Automated screening flags help order the queue; they do not replace clinical judgment.</p>
          </div>
          <div className="flex min-h-11 overflow-x-auto rounded-xl bg-slate-100 p-1" role="group" aria-label="Filter triage queue">
            {(['all', 'critical', 'high', 'pending'] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setFilter(value)}
                aria-pressed={filter === value}
                className={`min-h-9 whitespace-nowrap rounded-lg px-3 text-xs font-semibold capitalize transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 ${filter === value ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-600 hover:text-slate-950'}`}
              >
                {value}
              </button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filteredRequests.length === 0 ? (
            <div className="p-8 sm:p-12"><EmptyState icon={<Activity className="h-10 w-10 text-emerald-500" />} title="No matching reports" description="There are no triage reports matching the current filter." /></div>
          ) : (
            <div className="flex flex-col xl:flex-row divide-y xl:divide-y-0 xl:divide-x divide-slate-100 min-h-[500px]">
              <div className={`flex-1 overflow-y-auto max-h-[600px] ${selectedRequestId ? 'xl:w-1/3 xl:flex-none' : 'w-full'}`}>
                <div className="divide-y divide-slate-100">
                  {filteredRequests.map((request) => (
                    <button 
                      key={request.id} 
                      onClick={() => setSelectedRequestId(request.id)}
                      className={`w-full text-left flex flex-col justify-between gap-2 p-4 hover:bg-slate-50 transition-colors ${selectedRequestId === request.id ? 'bg-blue-50/50 border-l-4 border-l-blue-600' : 'border-l-4 border-l-transparent'}`}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        {getPriorityBadge(request.priority)}
                        {getStatusBadge(request.status)}
                      </div>
                      <p className="text-sm font-medium text-slate-900 line-clamp-2">“{request.symptoms}”</p>
                      <div className="text-[11px] font-medium text-slate-500">Patient {request.patient_id} • {new Date(request.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</div>
                    </button>
                  ))}
                </div>
              </div>
              
              {selectedRequest && (
                <div className="flex-1 p-6 bg-slate-50/30 overflow-y-auto">
                  <div className="glass-panel p-6 rounded-2xl mb-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-bold text-slate-900">Triage Detail</h3>
                      <Button variant="ghost" size="sm" onClick={() => setSelectedRequestId(null)}>Close</Button>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold mb-1">Symptoms Reported</p>
                        <p className="text-base text-slate-900 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">“{selectedRequest.symptoms}”</p>
                      </div>
                      
                      {selectedRequest.ai_reasoning && (
                        <div className="bg-blue-50/80 p-4 rounded-xl border border-blue-100">
                           <p className="text-xs text-blue-700 uppercase tracking-wider font-semibold flex items-center gap-1.5 mb-2">
                             <span className="text-base">✨</span> Automated Rationale
                           </p>
                           <p className="text-sm text-blue-900 leading-relaxed">{selectedRequest.ai_reasoning}</p>
                        </div>
                      )}
                      
                      {selectedRequest.disclaimer && (
                        <p className="text-xs leading-5 text-slate-500 italic">{selectedRequest.disclaimer}</p>
                      )}
                    </div>
                  </div>
                  
                  {normalized(selectedRequest.status) !== 'resolved' && (
                    <div className="flex items-center gap-3">
                      <Button variant="outline" onClick={() => updateStatus(selectedRequest.id, 'Under Review')} disabled={normalized(selectedRequest.status) === 'under review'}>Mark under review</Button>
                      <Button onClick={() => updateStatus(selectedRequest.id, 'Resolved')} className="bg-emerald-700 text-white hover:bg-emerald-800">Mark resolved</Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
