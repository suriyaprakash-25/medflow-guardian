import { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown, Download, Search, ShieldCheck, ShieldX } from 'lucide-react';
import { Button } from '@shared/ui/Button';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { Input } from '@shared/ui/Input';
import { ResponsiveTable } from '@shared/ui/ResponsiveTable';
import { api } from '../lib/api';

interface AuditRecord {
  id: number;
  actor_id: number;
  actor_role: string;
  organization_id?: number | null;
  patient_id?: number | null;
  operation: string;
  resource_type: string;
  resource_id?: string | null;
  purpose?: string | null;
  request_id?: string | null;
  correlation_id?: string | null;
  authorization_id?: string | null;
  consent_id?: number | null;
  consent_state_id?: number | null;
  policy_version?: number | null;
  enforcement_point?: string | null;
  decision: 'ALLOW' | 'DENY';
  denial_reason?: string | null;
  metadata_json?: string | null;
  timestamp: string;
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

function metadataText(raw?: string | null) {
  if (!raw) return '// No additional metadata';
  try { return JSON.stringify(JSON.parse(raw), null, 2); }
  catch { return raw; }
}

function csvCell(value: unknown) {
  const text = value === null || value === undefined ? '' : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

export default function Audit() {
  const user = useMemo(() => readStoredUser(), []);
  const isPlatformAdmin = user.system_role === 'platform_admin' || user.role === 'platform_admin';
  const orgId = isPlatformAdmin ? undefined : user.memberships?.[0]?.hospital_id;
  const scopeLabel = isPlatformAdmin ? 'Platform scope' : user.memberships?.[0]?.hospital_name || (orgId ? `Organization ${orgId}` : 'Organization scope');

  const [logs, setLogs] = useState<AuditRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [decisionFilter, setDecisionFilter] = useState<'all' | 'ALLOW' | 'DENY'>('all');

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/api/admin/audit', {
        params: { ...(orgId ? { hospital_id: orgId } : {}), limit: 100 },
      });
      setLogs((response.data.items || []) as AuditRecord[]);
      setTotal(Number(response.data.total || 0));
    } catch (requestError: unknown) {
      const detail = typeof requestError === 'object' && requestError !== null && 'response' in requestError
        ? (requestError as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      setError(detail || 'Unable to load the authorization audit trail.');
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    queueMicrotask(() => { void fetchLogs(); });
  }, [fetchLogs]);

  const filteredLogs = useMemo(() => logs.filter((log) => {
    if (decisionFilter !== 'all' && log.decision !== decisionFilter) return false;
    const query = searchTerm.trim().toLowerCase();
    if (!query) return true;
    return [log.operation, log.resource_type, log.actor_role, log.actor_id, log.resource_id, log.denial_reason, log.purpose, log.request_id, log.correlation_id]
      .some((value) => value !== null && value !== undefined && String(value).toLowerCase().includes(query));
  }), [logs, decisionFilter, searchTerm]);

  const exportLoadedCsv = () => {
    const headers = ['id', 'timestamp', 'decision', 'operation', 'resource_type', 'resource_id', 'actor_role', 'actor_id', 'organization_id', 'patient_id', 'purpose', 'denial_reason', 'authorization_id', 'consent_id', 'consent_state_id', 'policy_version', 'enforcement_point'];
    const rows = filteredLogs.map((log) => headers.map((key) => csvCell(log[key as keyof AuditRecord])).join(','));
    const blob = new Blob([[headers.join(','), ...rows].join('\n')], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `medflow-audit-${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">{scopeLabel}</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Security audit trail</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Authorization decisions recorded by the server. This view does not claim realtime health or completeness beyond the API response.</p>
        </div>
        <Button type="button" variant="outline" className="gap-2 self-start lg:self-auto" onClick={exportLoadedCsv} disabled={filteredLogs.length === 0}>
          <Download className="h-4 w-4" aria-hidden="true" />Export visible records
        </Button>
      </header>

      {error ? <FeedbackState tone="error" title="Audit trail unavailable" message={error} action={<Button type="button" onClick={() => void fetchLogs()}>Retry</Button>} /> : null}

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm" aria-label="Audit filters">
        <div className="grid gap-4 md:grid-cols-[1fr_auto_auto] md:items-end">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" aria-hidden="true" />
            <label htmlFor="audit-search" className="sr-only">Search audit records</label>
            <Input id="audit-search" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Search operation, actor, resource or request" className="pl-10" />
          </div>
          <div>
            <label htmlFor="audit-decision" className="mb-1 block text-xs font-semibold text-slate-600">Decision</label>
            <select id="audit-decision" value={decisionFilter} onChange={(event) => setDecisionFilter(event.target.value as 'all' | 'ALLOW' | 'DENY')} className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2">
              <option value="all">All decisions</option><option value="ALLOW">Allow</option><option value="DENY">Deny</option>
            </select>
          </div>
          <p className="min-h-11 rounded-xl bg-slate-50 px-3 py-3 text-sm text-slate-600" role="status">Showing {filteredLogs.length} of {Math.min(logs.length, total)} loaded records · {total} total</p>
        </div>
      </section>

      {loading ? (
        <FeedbackState tone="loading" title="Loading audit records" message="Retrieving up to 100 recent server audit entries." />
      ) : filteredLogs.length === 0 ? (
        <FeedbackState tone="empty" title="No matching audit records" message={logs.length === 0 ? 'No audit records were returned for this scope.' : 'Adjust the search or decision filter.'} />
      ) : (
        <ResponsiveTable label="Authorization audit records">
          <table className="w-full border-collapse text-left">
            <thead><tr className="border-b border-slate-200 bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-600"><th scope="col" className="p-4 pl-6">Event</th><th scope="col" className="p-4">Actor</th><th scope="col" className="p-4">Resource</th><th scope="col" className="p-4">Decision</th><th scope="col" className="p-4 text-right">Timestamp</th><th scope="col" className="p-4 pr-6"><span className="sr-only">Details</span></th></tr></thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLogs.map((log) => {
                const expanded = expandedId === log.id;
                return [
                  <tr key={`row-${log.id}`} className={expanded ? 'bg-blue-50/30' : 'hover:bg-slate-50/70'}>
                    <td className="p-4 pl-6"><div className="flex items-center gap-3">{log.decision === 'ALLOW' ? <ShieldCheck className="h-5 w-5 text-emerald-700" aria-hidden="true" /> : <ShieldX className="h-5 w-5 text-rose-700" aria-hidden="true" />}<span className="font-semibold text-slate-950">{log.operation}</span></div></td>
                    <td className="p-4 text-sm text-slate-700"><span className="font-medium">{log.actor_role}</span><span className="ml-2 text-xs text-slate-500">ID {log.actor_id}</span></td>
                    <td className="p-4 text-sm text-slate-700">{log.resource_type}{log.resource_id ? <span className="ml-2 text-xs text-slate-500">ID {log.resource_id}</span> : null}</td>
                    <td className="p-4"><span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-bold ${log.decision === 'ALLOW' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-rose-200 bg-rose-50 text-rose-800'}`}>{log.decision}</span>{log.denial_reason ? <p className="mt-1 max-w-52 truncate text-xs text-rose-700" title={log.denial_reason}>{log.denial_reason}</p> : null}</td>
                    <td className="p-4 text-right text-sm text-slate-600"><time dateTime={log.timestamp}>{new Date(log.timestamp).toLocaleString()}</time></td>
                    <td className="p-4 pr-6 text-right"><Button type="button" variant="ghost" size="icon" aria-label={`${expanded ? 'Collapse' : 'Expand'} audit event ${log.id}`} aria-expanded={expanded} aria-controls={`audit-detail-${log.id}`} onClick={() => setExpandedId(expanded ? null : log.id)}><ChevronDown className={`h-5 w-5 transition-transform ${expanded ? 'rotate-180' : ''}`} aria-hidden="true" /></Button></td>
                  </tr>,
                  expanded ? <tr key={`detail-${log.id}`} id={`audit-detail-${log.id}`}><td colSpan={6} className="border-b border-slate-200 bg-slate-50/60 p-5 sm:p-6"><div className="grid gap-5 lg:grid-cols-3"><dl className="rounded-xl border border-slate-200 bg-white p-4 text-sm"><dt className="font-semibold text-slate-950">Context</dt><dd className="mt-3 text-slate-600">Organization: {log.organization_id ?? 'Global'}</dd><dd className="mt-2 text-slate-600">Patient: {log.patient_id ?? 'Not applicable'}</dd><dd className="mt-2 text-slate-600">Purpose: {log.purpose || 'Not specified'}</dd><dd className="mt-2 text-slate-600">Request: {log.request_id || 'Not recorded'}</dd></dl><dl className="rounded-xl border border-slate-200 bg-white p-4 text-sm"><dt className="font-semibold text-slate-950">Authorization trace</dt><dd className="mt-3 text-slate-600">Authorization ID: {log.authorization_id || 'Not recorded'}</dd><dd className="mt-2 text-slate-600">Consent ID: {log.consent_id ?? 'Not applicable'}</dd><dd className="mt-2 text-slate-600">Consent state ID: {log.consent_state_id ?? 'Not applicable'}</dd><dd className="mt-2 text-slate-600">Policy version: {log.policy_version ?? 'Not recorded'}</dd><dd className="mt-2 text-slate-600">Enforcement point: {log.enforcement_point || 'Not recorded'}</dd></dl><div className="min-w-0"><p className="font-semibold text-slate-950">Additional metadata</p><pre className="mt-3 max-h-48 overflow-auto rounded-xl bg-slate-950 p-4 text-xs leading-5 text-emerald-300">{metadataText(log.metadata_json)}</pre></div></div></td></tr> : null,
                ];
              })}
            </tbody>
          </table>
        </ResponsiveTable>
      )}
    </div>
  );
}
