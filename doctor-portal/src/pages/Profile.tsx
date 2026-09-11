import { useDoctorContext } from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Badge } from '@shared/ui/Badge';
import { EmptyState } from '@shared/ui/EmptyState';
import { ShieldCheck, History, Activity, AlertCircle, Clock } from 'lucide-react';

export default function Profile() {
  const { auditLogs } = useDoctorContext();

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Security Audit Logs</h2>
        <p className="text-sm text-slate-500 mt-1">Review your recent activity, access events, and system interactions.</p>
      </div>

      <Card>
        <CardHeader className="bg-slate-50/50 border-b border-slate-100 pb-4">
          <CardTitle className="text-lg flex items-center gap-2">
            <History className="h-5 w-5 text-slate-500" />
            Activity Timeline
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {auditLogs.length === 0 ? (
            <div className="p-12">
              <EmptyState 
                icon={<ShieldCheck className="h-10 w-10 text-slate-300" />}
                title="No audit logs found"
                description="Your account activity will appear here."
              />
            </div>
          ) : (
            <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
              {auditLogs.map(log => {
                const isWarning = log.action.includes('unauthorized') || log.action.includes('failed');
                
                return (
                  <div key={log.id} className="p-5 hover:bg-slate-50 transition-colors flex gap-4">
                    <div className="mt-0.5 shrink-0">
                      {isWarning ? (
                        <div className="h-8 w-8 rounded-full bg-rose-100 flex items-center justify-center">
                          <AlertCircle className="h-4 w-4 text-rose-600" />
                        </div>
                      ) : (
                        <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center">
                          <Activity className="h-4 w-4 text-slate-500" />
                        </div>
                      )}
                    </div>
                    
                    <div className="flex-1 space-y-1">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="font-semibold text-sm text-slate-900 uppercase tracking-wide">
                          {log.action.replace(/_/g, ' ')}
                        </div>
                        <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
                          <Clock className="h-3 w-3" />
                          {new Date(log.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}
                        </div>
                      </div>
                      
                      <div className="flex flex-wrap gap-2 pt-1">
                        {log.target_user_id && (
                          <Badge variant="outline" className="bg-white text-xs font-medium text-slate-600">
                            Target User ID: {log.target_user_id}
                          </Badge>
                        )}
                        {log.document_id && (
                          <Badge variant="outline" className="bg-white text-xs font-medium text-slate-600">
                            Document ID: {log.document_id}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
