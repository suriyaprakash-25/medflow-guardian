import { useState } from 'react';
import { usePatientContext } from '../components/Layout';
import { Card, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Badge } from '@shared/ui/Badge';
import { ConfirmModal } from '@shared/ui/ConfirmModal';
import { Shield, ShieldX, Clock, FileText, User } from 'lucide-react';
import { EmptyState } from '@shared/ui/EmptyState';

export default function AccessHistory() {
  const { accessGrants, patientVisits, handleRevokeGrant } = usePatientContext();

  const [confirmRevokeId, setConfirmRevokeId] = useState<number | null>(null);

  const activeGrants = accessGrants.filter(g => g.status === 'active');
  const historicalGrants = accessGrants.filter(g => g.status !== 'active');

  const getDoctorName = (doctorId: number) => {
    const visit = patientVisits.find(v => v.doctor_id === doctorId);
    return visit?.doctor?.full_name ? `Dr. ${visit.doctor.full_name}` : `Doctor (ID: ${doctorId})`;
  };

  const executeRevoke = () => {
    if (confirmRevokeId) handleRevokeGrant(confirmRevokeId);
    setConfirmRevokeId(null);
  };

  return (
    <div className="flex flex-col gap-8 animate-in fade-in duration-500">
      
      {/* Active Grants Section */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Shield className="h-5 w-5 text-emerald-500" />
          <h3 className="text-lg font-semibold text-slate-800 m-0">Active Access Grants</h3>
        </div>
        
        {activeGrants.length === 0 ? (
          <EmptyState 
            icon={<Shield className="h-12 w-12 text-slate-300" />} 
            title="No Active Grants" 
            description="There are currently no doctors with active access to your private records."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {activeGrants.map(grant => (
              <Card key={grant.id} className="border-emerald-100 shadow-sm overflow-hidden flex flex-col">
                <div className="h-1 bg-emerald-400 w-full"></div>
                <CardContent className="p-5 flex flex-col flex-1">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-2">
                      <div className="h-8 w-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">
                        <User className="h-4 w-4" />
                      </div>
                      <div>
                        <h4 className="text-base font-semibold text-slate-900 m-0">{getDoctorName(grant.doctor_id)}</h4>
                        <Badge className="bg-emerald-100 text-emerald-800 text-[10px] mt-1">Active</Badge>
                      </div>
                    </div>
                  </div>

                  <div className="mb-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <FileText className="h-3.5 w-3.5" /> Accessible Documents
                    </p>
                    <ul className="space-y-1">
                      {grant.granted_documents.map((doc: any) => (
                        <li key={doc.id} className="text-sm text-slate-600 flex items-center gap-2 before:content-['•'] before:text-slate-400 pl-2">
                          {doc.title}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="mt-auto pt-4 border-t border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs text-slate-500">
                      <Clock className="h-3.5 w-3.5" />
                      Expires: {new Date(grant.expires_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                    </div>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
                      onClick={() => setConfirmRevokeId(grant.id)}
                    >
                      <ShieldX className="h-3.5 w-3.5 mr-1.5" />
                      Revoke Now
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Historical Grants Section (Timeline Style) */}
      <section>
        <div className="flex items-center gap-2 mb-4 pt-4 border-t border-slate-200">
          <Clock className="h-5 w-5 text-slate-400" />
          <h3 className="text-lg font-semibold text-slate-800 m-0">Access History</h3>
        </div>

        {historicalGrants.length === 0 ? (
          <p className="text-sm text-slate-500 italic">No past access records.</p>
        ) : (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="divide-y divide-slate-100">
              {historicalGrants.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).map(grant => (
                <div key={grant.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50 transition-colors">
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 p-1.5 rounded-full ${grant.status === 'revoked' ? 'bg-red-100 text-red-600' : 'bg-slate-100 text-slate-500'}`}>
                      {grant.status === 'revoked' ? <ShieldX className="h-4 w-4" /> : <Clock className="h-4 w-4" />}
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-slate-900 m-0">{getDoctorName(grant.doctor_id)}</h4>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Granted on {new Date(grant.created_at).toLocaleDateString()} for {grant.granted_documents.length} document(s)
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3 sm:flex-col sm:items-end">
                    <Badge className={grant.status === 'revoked' ? 'bg-red-100 text-red-800' : 'bg-slate-100 text-slate-600'}>
                      {grant.status.charAt(0).toUpperCase() + grant.status.slice(1)}
                    </Badge>
                    <span className="text-xs text-slate-400">
                      Ended: {new Date(grant.expires_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      <ConfirmModal
        isOpen={!!confirmRevokeId}
        title="Revoke Medical Access"
        description="This will prevent new access to this protected information. Any document transfer that is already in progress may continue until the current transfer completes."
        confirmText="Yes, Revoke Access"
        isDestructive={true}
        onConfirm={executeRevoke}
        onCancel={() => setConfirmRevokeId(null)}
      />
    </div>
  );
}
