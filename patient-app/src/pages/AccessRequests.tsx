import { useState } from 'react';
import { usePatientContext } from '../components/Layout';
import { Card, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Select } from '@shared/ui/Select';
import { Badge } from '@shared/ui/Badge';
import { ConfirmModal } from '@shared/ui/ConfirmModal';
import { ShieldAlert, FileText, CheckCircle, XCircle, Building, Clock } from 'lucide-react';
import { EmptyState } from '@shared/ui/EmptyState';
import { toast } from 'react-hot-toast';
export default function AccessRequests() {
  const { accessRequests, patientVisits, durations, setDurations, handleApproveAccess, handleRejectAccess } = usePatientContext();

  const pendingRequests = accessRequests.filter(r => r.status === 'pending');

  const [confirmApproveId, setConfirmApproveId] = useState<number | null>(null);
  const [confirmRejectId, setConfirmRejectId] = useState<number | null>(null);

  const getDoctorName = (doctorId: number) => {
    const visit = patientVisits.find(v => v.doctor_id === doctorId);
    return visit?.doctor?.full_name ? `Dr. ${visit.doctor.full_name}` : `Doctor (ID: ${doctorId})`;
  };

  const getHospitalName = (hospitalId: number) => {
    const visit = patientVisits.find(v => v.hospital?.id === hospitalId);
    return visit?.hospital?.name || `Hospital (ID: ${hospitalId})`;
  };

  const activeRequest = pendingRequests.find(r => r.id === (confirmApproveId || confirmRejectId));

  const executeApprove = () => {
    if (activeRequest) handleApproveAccess(activeRequest);
    setConfirmApproveId(null);
  };

  const executeReject = () => {
    if (activeRequest) handleRejectAccess(activeRequest.id);
    setConfirmRejectId(null);
  };

  console.log("AccessRequests Render - confirmApproveId:", confirmApproveId, "isOpen:", !!confirmApproveId);

  return (
    <div className="flex flex-col gap-6 animate-in fade-in duration-500">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-800 m-0">Document Access Requests</h3>
        <Badge className="bg-amber-100 text-amber-800 hover:bg-amber-100">{pendingRequests.length} Pending</Badge>
      </div>

      {pendingRequests.length === 0 ? (
        <EmptyState 
          icon={<ShieldAlert className="h-12 w-12 text-slate-400" />} 
          title="No pending requests" 
          description="You have no new requests from doctors to view your medical records."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {pendingRequests.map(req => {
            const docName = getDoctorName(req.requesting_doctor_id);
            const hospName = getHospitalName(req.requesting_hospital_id);
            const duration = durations[req.id] || 1;

            return (
              <Card key={req.id} className="border-amber-200 shadow-sm overflow-hidden flex flex-col">
                <div className="h-2 bg-amber-400 w-full"></div>
                <CardContent className="p-6 flex flex-col flex-1">
                  
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h4 className="text-lg font-semibold text-slate-900 m-0">{docName}</h4>
                      <div className="flex items-center gap-1.5 text-sm text-slate-500 mt-1">
                        <Building className="h-4 w-4" />
                        {hospName}
                      </div>
                    </div>
                    <Badge className="bg-amber-100 text-amber-800">Action Required</Badge>
                  </div>

                  <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 mb-6">
                    <p className="text-sm font-medium text-slate-700 mb-2">Reason for Request:</p>
                    <p className="text-sm text-slate-600 italic">"{req.reason}"</p>
                  </div>

                  <div className="mb-6 flex-1">
                    <p className="text-sm font-medium text-slate-700 mb-3 flex items-center gap-2">
                      <FileText className="h-4 w-4 text-primary" />
                      Requested Documents
                    </p>
                    <ul className="space-y-2">
                      {req.requested_documents.map((doc: any) => (
                        <li key={doc.id} className="text-sm text-slate-600 flex items-center gap-2 before:content-['•'] before:text-primary pl-2">
                          {doc.title} <span className="text-xs text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">{doc.document_type}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="pt-4 border-t border-slate-100 mt-auto">
                    <p className="text-sm font-medium text-slate-700 mb-3 flex items-center gap-2">
                      <Clock className="h-4 w-4 text-slate-500" />
                      Allow access for:
                    </p>
                    <div className="flex flex-col sm:flex-row gap-3">
                      <Select 
                        value={duration} 
                        onChange={e => setDurations({...durations, [req.id]: parseInt(e.target.value)})}
                        className="bg-slate-50 sm:w-1/3"
                      >
                        <option value={1}>1 hour</option>
                        <option value={4}>4 hours</option>
                        <option value={24}>1 day</option>
                        <option value={96}>4 days</option>
                      </Select>
                      <div className="flex gap-2 sm:w-2/3">
                        <Button 
                          className="flex-1 flex flex-row items-center justify-center gap-2 text-white border-none whitespace-nowrap h-10 px-3" 
                          style={{ backgroundColor: '#10b981' }}
                          onClick={() => {
                            toast('Please confirm approval in the popup window.', { icon: 'ℹ️' });
                            setConfirmApproveId(req.id);
                          }}
                        >
                          <CheckCircle className="h-4 w-4 shrink-0" />
                          <span>Approve</span>
                        </Button>
                        <Button 
                          variant="outline" 
                          className="flex-1 flex flex-row items-center justify-center gap-2 text-slate-600 hover:text-red-600 hover:border-red-200 hover:bg-red-50 whitespace-nowrap h-10 px-3" 
                          onClick={() => {
                            toast('Please confirm rejection in the popup window.', { icon: 'ℹ️' });
                            setConfirmRejectId(req.id);
                          }}
                        >
                          <XCircle className="h-4 w-4 shrink-0" />
                          <span>Reject</span>
                        </Button>
                      </div>
                    </div>
                  </div>

                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Confirmation Modals */}
      <ConfirmModal
        isOpen={!!confirmApproveId}
        title="Approve Medical Access"
        description={`Are you sure you want to grant ${activeRequest ? getDoctorName(activeRequest.requesting_doctor_id) : 'this doctor'} access to ${activeRequest?.requested_documents?.length} documents for ${durations[confirmApproveId!] || 1} hour(s)?`}
        confirmText="Yes, Approve Access"
        onConfirm={executeApprove}
        onCancel={() => setConfirmApproveId(null)}
      />

      <ConfirmModal
        isOpen={!!confirmRejectId}
        title="Reject Access Request"
        description="Are you sure you want to reject this access request? The doctor will not be able to view these documents."
        confirmText="Yes, Reject"
        isDestructive={true}
        onConfirm={executeReject}
        onCancel={() => setConfirmRejectId(null)}
      />
    </div>
  );
}
