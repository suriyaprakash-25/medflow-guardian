import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { Database, Search, Filter, ShieldAlert } from 'lucide-react';

export default function Audit() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const orgId = user.system_role === 'platform_admin' ? '' : user.memberships?.[0]?.hospital_id;

  useEffect(() => {
    const fetchAudit = async () => {
      try {
        const res = await api.get('/api/admin/audit', {
          params: { hospital_id: orgId, limit: 50, offset: 0 }
        });
        setLogs(res.data.items);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchAudit();
  }, [orgId]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Audit Explorer</h2>
          <p className="text-sm text-slate-500 mt-1">Tamper-evident trail of all Central Authorization Engine decisions.</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col h-[700px]">
        {/* Toolbar */}
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex gap-4 items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search audit logs..."
              className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button className="flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50 bg-white">
            <Filter className="h-4 w-4" />
            Filter
          </button>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="p-8 text-center text-slate-500">Loading audit trail...</div>
          ) : (
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50 sticky top-0">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Timestamp</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Decision</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Operation</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Actor / Role</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Resource</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Details</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 whitespace-nowrap text-xs text-slate-500">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                        log.decision === 'ALLOW' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {log.decision === 'DENY' && <ShieldAlert className="h-3 w-3" />}
                        {log.decision}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">
                      {log.operation}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-slate-900">ID: {log.actor_id}</div>
                      <div className="text-xs text-slate-500 capitalize">{log.actor_role}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-slate-900">{log.resource_type}</div>
                      {log.resource_id && <div className="text-xs text-slate-500">ID: {log.resource_id}</div>}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500 max-w-xs truncate">
                      {log.denial_reason && <div className="text-red-600 font-medium">{log.denial_reason}</div>}
                      {log.purpose && <div>Purpose: {log.purpose}</div>}
                      {log.consent_state_id && <div>Consent: {log.consent_state_id}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
