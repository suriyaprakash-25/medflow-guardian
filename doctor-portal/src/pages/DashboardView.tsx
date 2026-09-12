import { useState } from 'react';
import { useDoctorContext } from '../lib/doctorContext';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Badge } from '@shared/ui/Badge';
import { EmptyState } from '@shared/ui/EmptyState';
import { 
  Activity, CheckCircle, Clock, AlertTriangle, 
  ShieldAlert, User
} from 'lucide-react';

export default function DashboardView() {
  const { requests, updateStatus, isAdmin, adminData } = useDoctorContext();
  const [filter, setFilter] = useState<'all' | 'critical' | 'high' | 'pending'>('all');

  if (isAdmin) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold tracking-tight">System Overview</h2>
        {adminData ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Total Users</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{adminData.total_users}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Hospitals</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{adminData.total_hospitals}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Triage Requests</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{adminData.total_triage_requests}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-slate-500">Access Grants</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold">{adminData.active_grants}</div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <p className="text-slate-500">Loading admin data...</p>
        )}
      </div>
    );
  }

  const criticalCount = requests.filter(r => r.priority === 'Critical' && r.status !== 'Resolved').length;
  const highCount = requests.filter(r => r.priority === 'High' && r.status !== 'Resolved').length;
  const pendingCount = requests.filter(r => r.status === 'pending').length;

  const filteredRequests = requests.filter(r => {
    if (filter === 'critical') return r.priority === 'Critical';
    if (filter === 'high') return r.priority === 'High';
    if (filter === 'pending') return r.status === 'pending';
    return true;
  });

  const getPriorityBadge = (priority: string | null) => {
    switch (priority) {
      case 'Critical': return <Badge variant="destructive" className="bg-rose-100 text-rose-700 hover:bg-rose-100 border-none">Critical</Badge>;
      case 'High': return <Badge variant="destructive" className="bg-amber-100 text-amber-700 hover:bg-amber-100 border-none">High</Badge>;
      case 'Moderate': return <Badge variant="secondary" className="bg-blue-100 text-blue-700 hover:bg-blue-100 border-none">Moderate</Badge>;
      default: return <Badge variant="outline" className="bg-slate-100 text-slate-600 hover:bg-slate-100 border-none">Low</Badge>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Resolved': return <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1"><CheckCircle className="h-3 w-3"/> Resolved</span>;
      case 'Under Review': return <span className="text-xs font-semibold text-blue-600 flex items-center gap-1"><Activity className="h-3 w-3"/> Reviewing</span>;
      case 'pending': return <span className="text-xs font-semibold text-amber-600 flex items-center gap-1"><Clock className="h-3 w-3"/> Pending</span>;
      default: return <span className="text-xs font-semibold text-slate-500">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-l-4 border-l-rose-500">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium text-slate-600">Critical Alerts</CardTitle>
            <ShieldAlert className="h-4 w-4 text-rose-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-900">{criticalCount}</div>
            <p className="text-xs text-slate-500 mt-1">Requires immediate attention</p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium text-slate-600">High Priority</CardTitle>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-900">{highCount}</div>
            <p className="text-xs text-slate-500 mt-1">Review within 4 hours</p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium text-slate-600">Pending Queue</CardTitle>
            <Clock className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-slate-900">{pendingCount}</div>
            <p className="text-xs text-slate-500 mt-1">Awaiting initial assessment</p>
          </CardContent>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <CardHeader className="bg-slate-50/50 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <CardTitle className="text-lg">Triage Queue</CardTitle>
            <p className="text-sm text-slate-500 mt-1">AI-prioritized patient symptom reports.</p>
          </div>
          <div className="flex bg-slate-100 p-1 rounded-lg">
            <button onClick={() => setFilter('all')} className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${filter === 'all' ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-700'}`}>All</button>
            <button onClick={() => setFilter('critical')} className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${filter === 'critical' ? 'bg-white shadow-sm text-rose-600' : 'text-slate-500 hover:text-slate-700'}`}>Critical</button>
            <button onClick={() => setFilter('pending')} className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${filter === 'pending' ? 'bg-white shadow-sm text-blue-600' : 'text-slate-500 hover:text-slate-700'}`}>Pending</button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filteredRequests.length === 0 ? (
            <div className="p-12">
              <EmptyState icon={<Activity className="h-10 w-10 text-emerald-400" />} title="Queue is clear" description="There are no triage requests matching your current filter." />
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {filteredRequests.map(r => (
                <div key={r.id} className="p-5 hover:bg-slate-50 transition-colors group flex flex-col md:flex-row gap-4 md:items-center justify-between">
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center gap-3">
                      {getPriorityBadge(r.priority)}
                      <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-900">
                        <User className="h-4 w-4 text-slate-400" />
                        Patient #{r.id * 13}
                      </div>
                      <span className="text-slate-300">•</span>
                      {getStatusBadge(r.status)}
                    </div>
                    <div>
                      <p className="text-sm text-slate-900 font-medium">"{r.symptoms}"</p>
                      {r.ai_reasoning && (
                        <p className="text-xs text-slate-500 mt-1 border-l-2 border-slate-200 pl-2">
                          <span className="font-semibold text-slate-700">AI Note:</span> {r.ai_reasoning}
                        </p>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 font-medium uppercase tracking-wider">
                      Submitted: {new Date(r.created_at).toLocaleString([], {dateStyle: 'medium', timeStyle: 'short'})}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 shrink-0 md:pl-4 md:border-l md:border-slate-100">
                    {r.status !== 'Resolved' && (
                      <>
                        <Button variant="outline" size="sm" onClick={() => updateStatus(r.id, 'Under Review')} className="h-8 text-xs font-medium" disabled={r.status === 'Under Review'}>Reviewing</Button>
                        <Button variant="default" size="sm" onClick={() => updateStatus(r.id, 'Resolved')} className="h-8 text-xs font-medium bg-emerald-600 hover:bg-emerald-700 text-white">Mark Resolved</Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
