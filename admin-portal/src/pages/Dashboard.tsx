import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { Users, ShieldCheck, Activity, Database, AlertCircle, ArrowUpRight, ActivitySquare } from 'lucide-react';

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const orgId = user.role === 'platform_admin' ? '' : user.memberships?.[0]?.hospital_id;

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

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-4">
      <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      <p className="text-slate-500 font-medium animate-pulse">Synchronizing Platform Metrics...</p>
    </div>
  );

  if (!data) return (
    <div className="bg-red-50 border border-red-200 rounded-xl p-6 flex items-start gap-4 text-red-700 shadow-sm">
      <AlertCircle className="h-6 w-6 mt-0.5" />
      <div>
        <h3 className="font-semibold text-lg">Platform Error</h3>
        <p className="mt-1">Failed to establish secure connection with Central Authorization Engine.</p>
      </div>
    </div>
  );

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex justify-between items-end">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Platform Governance</h2>
          <p className="text-slate-500 mt-1">Real-time operational metrics and security overview.</p>
        </div>
        <div className="px-4 py-2 bg-emerald-50 text-emerald-700 rounded-lg text-sm font-semibold border border-emerald-100 flex items-center gap-2 shadow-sm">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          System Healthy
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Metric 1 */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Users className="h-24 w-24 text-blue-600" />
          </div>
          <div className="relative z-10">
            <div className="p-3 bg-blue-50 text-blue-600 rounded-xl inline-flex shadow-sm border border-blue-100 mb-4">
              <Users className="h-6 w-6" />
            </div>
            <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Active Staff</p>
            <div className="flex items-baseline gap-3">
              <h3 className="text-4xl font-bold text-slate-900 tracking-tight">{data.metrics.total_staff}</h3>
              <span className="flex items-center text-sm font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
                <ArrowUpRight className="h-4 w-4 mr-1" /> 12%
              </span>
            </div>
          </div>
        </div>
        
        {/* Metric 2 */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <ShieldCheck className="h-24 w-24 text-indigo-600" />
          </div>
          <div className="relative z-10">
            <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl inline-flex shadow-sm border border-indigo-100 mb-4">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Active Consents</p>
            <div className="flex items-baseline gap-3">
              <h3 className="text-4xl font-bold text-slate-900 tracking-tight">{data.metrics.active_consents}</h3>
              <span className="flex items-center text-sm font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
                <ArrowUpRight className="h-4 w-4 mr-1" /> 4%
              </span>
            </div>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <ActivitySquare className="h-24 w-24 text-purple-600" />
          </div>
          <div className="relative z-10">
            <div className="p-3 bg-purple-50 text-purple-600 rounded-xl inline-flex shadow-sm border border-purple-100 mb-4">
              <Activity className="h-6 w-6" />
            </div>
            <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">Total Patients</p>
            <div className="flex items-baseline gap-3">
              <h3 className="text-4xl font-bold text-slate-900 tracking-tight">{data.metrics.total_patients}</h3>
              <span className="flex items-center text-sm font-medium text-slate-400 bg-slate-50 px-2 py-0.5 rounded-md">
                Stable
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-200 bg-slate-50/80 backdrop-blur-sm flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-slate-200/50 rounded-lg">
              <Database className="h-5 w-5 text-slate-600" />
            </div>
            <h3 className="text-lg font-bold text-slate-800 tracking-tight">Recent Security Events</h3>
          </div>
          <button className="text-sm font-medium text-blue-600 hover:text-blue-700 transition-colors">
            View Full Audit Log &rarr;
          </button>
        </div>
        
        <div className="divide-y divide-slate-100">
          {data.recent_activity?.length === 0 ? (
            <div className="p-12 text-center flex flex-col items-center">
               <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4 border border-slate-100">
                 <ShieldCheck className="h-8 w-8 text-slate-300" />
               </div>
               <h4 className="text-slate-900 font-medium mb-1">No Recent Events</h4>
               <p className="text-slate-500 text-sm max-w-sm">There have been no security events recorded in the current organization scope.</p>
            </div>
          ) : (
            data.recent_activity?.map((log: any) => (
              <div key={log.id} className="p-4 px-6 flex items-center justify-between hover:bg-slate-50/80 transition-colors group">
                <div className="flex items-center gap-4">
                  <span className={`flex-shrink-0 w-2.5 h-2.5 rounded-full ${log.decision === 'ALLOW' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]'}`}></span>
                  <div className="flex flex-col">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-bold text-slate-900">{log.operation}</span>
                      <span className="text-sm text-slate-500 font-medium">on {log.resource_type}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-500 font-medium">
                      <span className="bg-slate-100 px-2 py-0.5 rounded text-slate-600">Actor: {log.actor_role} ({log.actor_id})</span>
                      {log.denial_reason && (
                        <span className="text-red-600 bg-red-50 px-2 py-0.5 rounded border border-red-100">Reason: {log.denial_reason}</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className={`text-xs font-bold uppercase tracking-wider mb-1 ${log.decision === 'ALLOW' ? 'text-emerald-600' : 'text-red-600'}`}>
                    {log.decision}
                  </div>
                  <span className="text-xs text-slate-400 font-medium">{new Date(log.timestamp).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'})}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
