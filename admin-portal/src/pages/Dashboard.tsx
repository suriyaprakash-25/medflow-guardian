import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { Users, FileCheck2, Activity, Database, AlertCircle } from 'lucide-react';

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const orgId = user.system_role === 'platform_admin' ? '' : user.memberships?.[0]?.hospital_id;

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const res = await api.get('/api/admin/dashboard', {
          params: { hospital_id: orgId }
        });
        setData(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [orgId]);

  if (loading) return <div className="p-8 text-center text-slate-500">Loading metrics...</div>;
  if (!data) return <div className="p-8 text-center text-red-500">Failed to load dashboard.</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Governance Dashboard</h2>
          <p className="text-sm text-slate-500 mt-1">Operational metrics and security overview.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-start gap-4">
          <div className="p-3 bg-blue-100 text-blue-600 rounded-lg">
            <Users className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Active Staff</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-1">{data.metrics.total_staff}</h3>
          </div>
        </div>
        
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-start gap-4">
          <div className="p-3 bg-emerald-100 text-emerald-600 rounded-lg">
            <FileCheck2 className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Active Patient Consents</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-1">{data.metrics.active_consents}</h3>
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-start gap-4">
          <div className="p-3 bg-purple-100 text-purple-600 rounded-lg">
            <Activity className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Total Patients</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-1">{data.metrics.total_patients}</h3>
          </div>
        </div>
      </div>

      <div className="mt-8 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-slate-500" />
            <h3 className="text-base font-semibold text-slate-800">Recent Security Events</h3>
          </div>
        </div>
        <div className="divide-y divide-slate-100">
          {data.recent_activity?.length === 0 ? (
            <div className="p-8 text-center text-slate-500 flex flex-col items-center">
               <AlertCircle className="h-8 w-8 text-slate-300 mb-2" />
               <p>No recent security events.</p>
            </div>
          ) : (
            data.recent_activity?.map((log: any) => (
              <div key={log.id} className="p-4 px-6 flex items-center justify-between hover:bg-slate-50 transition-colors">
                <div className="flex flex-col">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 text-xs font-semibold rounded ${log.decision === 'ALLOW' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                      {log.decision}
                    </span>
                    <span className="text-sm font-medium text-slate-900">{log.operation}</span>
                    <span className="text-sm text-slate-500">on {log.resource_type}</span>
                  </div>
                  <span className="text-xs text-slate-500 mt-1">Actor ID: {log.actor_id} | {log.denial_reason ? `Reason: ${log.denial_reason}` : ''}</span>
                </div>
                <span className="text-xs text-slate-400">{new Date(log.timestamp).toLocaleString()}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
