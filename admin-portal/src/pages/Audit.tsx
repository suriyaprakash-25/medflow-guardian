import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { ShieldAlert, Database, Search, Filter, ShieldCheck, ShieldX, ChevronDown, User, Hash, Clock, FileJson } from 'lucide-react';

export default function Audit() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const orgId = user.role === 'platform_admin' ? '' : user.memberships?.[0]?.hospital_id;

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await api.get('/api/admin/audit', {
          params: { hospital_id: orgId, limit: 100 }
        });
        setLogs(res.data.items);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, [orgId]);

  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Security Audit Trail</h2>
          <p className="text-slate-500 mt-1 font-medium">Immutable ledger of all authorization decisions and system access.</p>
        </div>
        <div className="flex gap-3">
            <button className="px-4 py-2.5 bg-white text-slate-700 font-medium text-sm rounded-xl border border-slate-200 hover:bg-slate-50 transition-colors shadow-sm flex items-center gap-2">
            <Filter className="h-4 w-4" /> Filter Logs
            </button>
            <button className="px-4 py-2.5 bg-slate-900 text-white font-medium text-sm rounded-xl hover:bg-slate-800 transition-colors shadow-sm flex items-center gap-2">
            <Database className="h-4 w-4" /> Export CSV
            </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
        {/* Toolbar */}
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex flex-col sm:flex-row gap-4 items-center justify-between">
            <div className="relative w-full max-w-md">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Search className="h-4 w-4 text-slate-400" />
                </div>
                <input
                    type="text"
                    placeholder="Search operations or actors..."
                    className="w-full !pl-10 pr-4 py-2 border border-slate-200 rounded-xl bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all placeholder:text-slate-400"
                />
            </div>
            <div className="text-sm font-medium text-slate-500 flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                Live Recording Active
            </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-xs uppercase tracking-wider text-slate-500 font-bold">
                <th className="p-4 pl-6 font-semibold">Event</th>
                <th className="p-4 font-semibold">Actor</th>
                <th className="p-4 font-semibold">Resource</th>
                <th className="p-4 font-semibold">Decision</th>
                <th className="p-4 font-semibold text-right">Timestamp</th>
                <th className="p-4 pr-6 w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                    <td colSpan={6} className="p-12 text-center">
                        <div className="flex flex-col items-center justify-center gap-3">
                            <div className="w-6 h-6 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                            <span className="text-sm font-medium text-slate-500">Loading audit trail...</span>
                        </div>
                    </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                    <td colSpan={6} className="p-12 text-center text-slate-500 font-medium">
                        No audit logs available for this organization.
                    </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <React.Fragment key={log.id}>
                    <tr 
                        onClick={() => toggleExpand(log.id)}
                        className={`hover:bg-slate-50/80 transition-colors cursor-pointer group ${expandedId === log.id ? 'bg-blue-50/30' : ''}`}
                    >
                      <td className="p-4 pl-6">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg border shadow-sm ${log.decision === 'ALLOW' ? 'bg-emerald-50 border-emerald-100 text-emerald-600' : 'bg-red-50 border-red-100 text-red-600'}`}>
                             {log.decision === 'ALLOW' ? <ShieldCheck className="h-5 w-5" /> : <ShieldX className="h-5 w-5" />}
                          </div>
                          <span className="font-bold text-slate-900 group-hover:text-blue-600 transition-colors">{log.operation}</span>
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-slate-400" />
                          <span className="text-sm font-medium text-slate-700">{log.actor_role}</span>
                          <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded font-mono border border-slate-200">ID:{log.actor_id}</span>
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <Database className="h-4 w-4 text-slate-400" />
                          <span className="text-sm font-medium text-slate-700">{log.resource_type}</span>
                          {log.resource_id && (
                            <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded font-mono border border-slate-200">ID:{log.resource_id}</span>
                          )}
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex flex-col items-start gap-1">
                            <span className={`inline-flex items-center text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded ${log.decision === 'ALLOW' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                            {log.decision}
                            </span>
                            {log.denial_reason && (
                                <span className="text-xs text-red-500 font-medium truncate max-w-[150px]" title={log.denial_reason}>
                                    {log.denial_reason}
                                </span>
                            )}
                        </div>
                      </td>
                      <td className="p-4 text-right text-sm font-medium text-slate-500">
                        {new Date(log.timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>
                      <td className="p-4 pr-6">
                        <ChevronDown className={`h-5 w-5 text-slate-400 transition-transform ${expandedId === log.id ? 'rotate-180 text-blue-500' : 'group-hover:text-slate-600'}`} />
                      </td>
                    </tr>
                    
                    {/* Expanded Detail Panel */}
                    {expandedId === log.id && (
                        <tr>
                            <td colSpan={6} className="p-0 border-b border-slate-200 bg-slate-50/50">
                                <div className="px-8 py-6 grid grid-cols-1 md:grid-cols-3 gap-8 animate-in slide-in-from-top-2 fade-in duration-200">
                                    <div className="space-y-4">
                                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2"><Hash className="h-4 w-4" /> Context Data</h4>
                                        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
                                            <div className="flex justify-between text-sm">
                                                <span className="text-slate-500 font-medium">Event ID</span>
                                                <span className="text-slate-900 font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded">{log.id}</span>
                                            </div>
                                            <div className="flex justify-between text-sm">
                                                <span className="text-slate-500 font-medium">Organization</span>
                                                <span className="text-slate-900 font-medium">{log.organization_id || 'Global'}</span>
                                            </div>
                                            <div className="flex justify-between text-sm">
                                                <span className="text-slate-500 font-medium">Patient Scope</span>
                                                <span className="text-slate-900 font-medium">{log.patient_id || 'N/A'}</span>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div className="space-y-4">
                                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2"><ShieldAlert className="h-4 w-4" /> CAE State (Phase 5)</h4>
                                        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3 opacity-70">
                                            <div className="flex justify-between text-sm">
                                                <span className="text-slate-500 font-medium">Purpose</span>
                                                <span className="text-slate-900">{log.purpose || 'Not specified'}</span>
                                            </div>
                                            <div className="flex justify-between text-sm">
                                                <span className="text-slate-500 font-medium">Consent State ID</span>
                                                <span className="text-slate-900 font-mono text-xs">{log.consent_state_id || 'None'}</span>
                                            </div>
                                            <div className="flex justify-between text-sm">
                                                <span className="text-slate-500 font-medium">Enforcement State</span>
                                                <span className="text-slate-900 font-mono text-xs">{log.enforcement_state || 'None'}</span>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div className="space-y-4">
                                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2"><FileJson className="h-4 w-4" /> Raw Metadata</h4>
                                        <div className="bg-slate-900 rounded-xl p-4 shadow-inner overflow-x-auto h-[120px]">
                                            <pre className="text-xs font-mono text-green-400">
                                                {log.metadata_json ? JSON.stringify(JSON.parse(log.metadata_json), null, 2) : '// No metadata provided for this evaluation'}
                                            </pre>
                                        </div>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
