import { useState } from 'react';
import { useDoctorContext } from '../lib/doctorContext';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Badge } from '@shared/ui/Badge';
import { EmptyState } from '@shared/ui/EmptyState';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { Activity, CheckCircle, Clock, AlertTriangle, ShieldAlert, User } from 'lucide-react';

const normalized = (value: string | null | undefined) => (value || '').trim().toLowerCase();

export default function DashboardView() {
  const { requests, updateStatus, isAdmin, adminData } = useDoctorContext();
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'pending'>('all');

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
            <div className="divide-y divide-slate-100">
              {filteredRequests.map((request) => (
                <article key={request.id} className="flex flex-col justify-between gap-4 p-5 hover:bg-slate-50 md:flex-row md:items-center">
                  <div className="flex-1 space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      {getPriorityBadge(request.priority)}
                      <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
                        <User className="h-4 w-4 text-slate-500" aria-hidden="true" />
                        Patient ID {request.patient_id}
                      </div>
                      {getStatusBadge(request.status)}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-900">“{request.symptoms}”</p>
                      {request.ai_reasoning ? (
                        <p className="mt-2 border-l-2 border-blue-200 pl-3 text-xs leading-5 text-slate-600">
                          <span className="font-semibold text-slate-800">Automated triage rationale:</span> {request.ai_reasoning}
                        </p>
                      ) : null}
                      {request.disclaimer ? <p className="mt-2 text-xs leading-5 text-slate-600">{request.disclaimer}</p> : null}
                    </div>
                    <div className="text-[11px] font-medium uppercase tracking-wider text-slate-500">Submitted {new Date(request.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</div>
                  </div>
                  {normalized(request.status) !== 'resolved' ? (
                    <div className="flex flex-wrap items-center gap-2 md:border-l md:border-slate-100 md:pl-4">
                      <Button variant="outline" size="sm" onClick={() => updateStatus(request.id, 'Under Review')} disabled={normalized(request.status) === 'under review'}>Mark under review</Button>
                      <Button size="sm" onClick={() => updateStatus(request.id, 'Resolved')} className="bg-emerald-700 text-white hover:bg-emerald-800">Mark resolved</Button>
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
