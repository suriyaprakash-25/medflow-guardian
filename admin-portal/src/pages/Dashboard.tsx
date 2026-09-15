import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ActivitySquare, Database, ShieldCheck, Users } from 'lucide-react';
import { Button } from '@shared/ui/Button';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { api } from '../lib/api';

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface DashboardMetricData {
  metrics: {
    total_staff: number;
    active_consents: number;
    total_patients: number;
  };
  recent_activity: Array<{
    id: number;
    decision: string;
    operation: string;
    resource_type: string;
    actor_role: string;
    actor_id: number;
    denial_reason?: string | null;
    timestamp: string;
  }>;
}

interface StoredAdminUser {
  role?: string;
  system_role?: string;
  memberships?: Array<{ hospital_id?: number; hospital_name?: string }>;
}

function readStoredUser(): StoredAdminUser {
  try { return JSON.parse(localStorage.getItem('user') || '{}') as StoredAdminUser; }
  catch { return {}; }
}

export default function Dashboard() {
  const user = useMemo(() => readStoredUser(), []);
  const isPlatformAdmin = user.system_role === 'platform_admin' || user.role === 'platform_admin';
  const orgId = isPlatformAdmin ? undefined : user.memberships?.[0]?.hospital_id;
  const scopeLabel = isPlatformAdmin ? 'Platform scope' : user.memberships?.[0]?.hospital_name || (orgId ? `Organization ${orgId}` : 'Organization scope');

  const [data, setData] = useState<DashboardMetricData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const [filter, setFilter] = useState<'ALL' | 'ALLOW' | 'DENY'>('ALL');

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/api/admin/dashboard', { params: orgId ? { hospital_id: orgId } : undefined });
      setData(response.data as DashboardMetricData);
      setLoadedAt(new Date());
    } catch (requestError: unknown) {
      const detail = typeof requestError === 'object' && requestError !== null && 'response' in requestError
        ? (requestError as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      setData(null);
      setError(detail || 'The dashboard metrics request failed.');
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    queueMicrotask(() => { void fetchDashboard(); });
  }, [fetchDashboard]);

  if (loading) {
    return <FeedbackState tone="loading" title="Loading governance metrics" message={`Retrieving server-authorized metrics for ${scopeLabel}.`} />;
  }

  if (!data) {
    return <FeedbackState tone="error" title="Governance metrics unavailable" message={error || 'No dashboard data was returned.'} action={<Button type="button" onClick={() => void fetchDashboard()}>Retry</Button>} />;
  }

  const metrics = [
    { label: 'Active staff memberships', value: data.metrics.total_staff, icon: Users, description: 'Current active organization memberships in scope.' },
    { label: 'Active consents', value: data.metrics.active_consents, icon: ShieldCheck, description: 'Server records currently marked active in scope.' },
    { label: isPlatformAdmin ? 'Patient accounts' : 'Patients with visits', value: data.metrics.total_patients, icon: ActivitySquare, description: isPlatformAdmin ? 'Patient accounts across the platform.' : 'Distinct patients with a visit in this organization.' },
  ];

  const filteredActivity = useMemo(() => data.recent_activity.filter(log => filter === 'ALL' || log.decision === filter), [data.recent_activity, filter]);
  
  const allowCount = useMemo(() => data.recent_activity.filter(a => a.decision === 'ALLOW').length, [data.recent_activity]);
  const denyCount = useMemo(() => data.recent_activity.filter(a => a.decision === 'DENY').length, [data.recent_activity]);
  
  const healthData = useMemo(() => {
    return [
      { name: 'Allowed', value: allowCount, color: '#10b981' },
      { name: 'Denied', value: denyCount, color: '#f43f5e' }
    ];
  }, [allowCount, denyCount]);

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">{scopeLabel}</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Platform governance</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Counts and recent authorization events come from the administrative API. No trend or health status is inferred from these values.</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm" role="status">
          <span className="font-semibold text-slate-900">Metrics loaded</span>
          <span className="ml-2">{loadedAt ? loadedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '—'}</span>
        </div>
      </header>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3" aria-label="Governance metrics">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <article key={metric.label} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 inline-flex rounded-xl bg-blue-50 p-3 text-blue-700"><Icon className="h-6 w-6" aria-hidden="true" /></div>
              <p className="text-sm font-semibold text-slate-600">{metric.label}</p>
              <p className="mt-2 text-4xl font-bold tracking-tight text-slate-950">{metric.value}</p>
              <p className="mt-3 text-xs leading-5 text-slate-500">{metric.description}</p>
            </article>
          );
        })}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-labelledby="recent-security-heading">
          <div className="flex flex-col gap-3 border-b border-slate-200 bg-slate-50/80 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-slate-200/70 p-2"><Database className="h-5 w-5 text-slate-700" aria-hidden="true" /></div>
              <div>
                <h3 id="recent-security-heading" className="font-bold text-slate-950">Recent authorization events</h3>
                <p className="mt-1 text-xs text-slate-500">Live feed of the latest decisions.</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex bg-slate-200/50 rounded-lg p-1">
                 {(['ALL', 'ALLOW', 'DENY'] as const).map(f => (
                   <button key={f} onClick={() => setFilter(f)} className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${filter === f ? 'bg-white shadow-sm text-slate-900' : 'text-slate-500 hover:text-slate-800'}`}>{f}</button>
                 ))}
              </div>
              <Link to="/audit" className="inline-flex min-h-9 items-center justify-center rounded-md border border-slate-300 bg-white px-3 py-1 text-xs font-semibold text-slate-800 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-700">View all</Link>
            </div>
          </div>

          {filteredActivity.length === 0 ? (
            <div className="p-6"><FeedbackState tone="empty" title="No matching events" message="No audit records match the current filter." compact /></div>
          ) : (
            <div className="divide-y divide-slate-100">
              {filteredActivity.map((log) => {
                const allowed = log.decision === 'ALLOW';
                return (
                  <article key={log.id} className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6 hover:bg-slate-50 transition-colors">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${allowed ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-rose-200 bg-rose-50 text-rose-800'}`}>{log.decision}</span>
                        <span className="font-semibold text-slate-950">{log.operation}</span>
                        <span className="text-sm text-slate-500">on {log.resource_type}</span>
                      </div>
                      <p className="mt-2 text-xs text-slate-500">Actor {log.actor_role} · ID {log.actor_id}{log.denial_reason ? ` · ${log.denial_reason}` : ''}</p>
                    </div>
                    <time className="shrink-0 text-xs font-medium text-slate-500" dateTime={log.timestamp}>{new Date(log.timestamp).toLocaleString()}</time>
                  </article>
                );
              })}
            </div>
          )}
        </section>

        <section className="glass-panel overflow-hidden rounded-2xl p-6 flex flex-col items-center justify-center min-h-[300px]">
           <h3 className="font-bold text-slate-950 self-start w-full border-b border-slate-200/50 pb-3 mb-4">Governance Health</h3>
           {data.recent_activity.length > 0 ? (
             <>
               <div className="w-full h-48 relative">
                 <Suspense fallback={<div className="text-slate-400 text-xs flex items-center justify-center h-full">Loading chart...</div>}>
                   <ResponsiveContainer width="100%" height="100%">
                     <PieChart>
                       <Pie data={healthData} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                         {healthData.map((entry, index) => (
                           <Cell key={`cell-${index}`} fill={entry.color} />
                         ))}
                       </Pie>
                       <Tooltip />
                     </PieChart>
                   </ResponsiveContainer>
                 </Suspense>
                 <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-3xl font-bold text-slate-900">{Math.round((allowCount/(allowCount+denyCount))*100)}%</span>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Pass Rate</span>
                 </div>
               </div>
               <p className="text-xs text-center text-slate-500 mt-4 leading-relaxed">System health is calculated based on the authorization pass-rate of the most recent events.</p>
             </>
           ) : (
             <FeedbackState tone="empty" title="No data" message="Not enough data to calculate health score." compact />
           )}
        </section>
      </div>
    </div>
  );
}
