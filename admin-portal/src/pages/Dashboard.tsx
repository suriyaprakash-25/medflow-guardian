import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ActivitySquare, Database, ShieldCheck, Users } from 'lucide-react';
import { Button } from '@shared/ui/Button';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { api } from '../lib/api';

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

      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm" aria-labelledby="recent-security-heading">
        <div className="flex flex-col gap-3 border-b border-slate-200 bg-slate-50/80 px-5 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-200/70 p-2"><Database className="h-5 w-5 text-slate-700" aria-hidden="true" /></div>
            <div>
              <h3 id="recent-security-heading" className="font-bold text-slate-950">Recent authorization events</h3>
              <p className="mt-1 text-xs text-slate-500">Five most recent audit records in the current scope.</p>
            </div>
          </div>
          <Link to="/audit" className="inline-flex min-h-11 items-center justify-center rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2">View full audit log</Link>
        </div>

        {data.recent_activity.length === 0 ? (
          <div className="p-6"><FeedbackState tone="empty" title="No recent authorization events" message="No audit records were returned for the current scope." compact /></div>
        ) : (
          <div className="divide-y divide-slate-100">
            {data.recent_activity.map((log) => {
              const allowed = log.decision === 'ALLOW';
              return (
                <article key={log.id} className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
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
    </div>
  );
}
