import { useEffect } from 'react';
import { useDoctorContext } from '../components/Layout';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Badge } from '@shared/ui/Badge';
import { EmptyState } from '@shared/ui/EmptyState';
import { ShieldCheck, Search, ShieldAlert, FileText, CheckCircle, Clock, XCircle, Download, User } from 'lucide-react';

export default function AccessControl() {
  const { 
    reqPatientId, setReqPatientId, reqHospitalId, setReqHospitalId, 
    reqReason, setReqReason, availableDocs, selectedDocs, setSelectedDocs, 
    fetchingDocs, handleFetchPatientDocs, handleRequestAccess, handleDownload,
    accessRequests, accessGrants, doctorVisits 
  } = useDoctorContext();

  // Auto-populate the doctor's primary hospital based on their active visits
  useEffect(() => {
    if (!reqHospitalId && doctorVisits.length > 0 && doctorVisits[0].hospital_id) {
      setReqHospitalId(doctorVisits[0].hospital_id.toString());
    }
  }, [doctorVisits, reqHospitalId, setReqHospitalId]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Access Control</h2>
        <p className="text-sm text-slate-500 mt-1">Manage temporary access to patient documents from external hospitals.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Request Form & Sent Requests */}
        <div className="lg:col-span-7 space-y-6">
          <Card>
            <CardHeader className="bg-slate-50/50 border-b border-slate-100">
              <CardTitle className="text-lg flex items-center gap-2">
                <ShieldAlert className="h-5 w-5 text-blue-600" />
                Request External Records
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <form onSubmit={handleRequestAccess} className="space-y-6">
                
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-900">1. Select Patient</label>
                  <div className="flex gap-3">
                    <div className="relative flex-1">
                      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-4 w-4 text-slate-400" />
                      </div>
                      <input 
                        className="w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" 
                        type="number" 
                        placeholder="Patient ID (e.g., 3)" 
                        value={reqPatientId} 
                        onChange={e => setReqPatientId(e.target.value)} 
                        required 
                      />
                    </div>
                    <Button 
                      type="button" 
                      variant="secondary"
                      onClick={handleFetchPatientDocs} 
                      disabled={fetchingDocs || !reqPatientId}
                      className="shrink-0"
                    >
                      {fetchingDocs ? 'Searching...' : 'Find Records'}
                    </Button>
                  </div>
                </div>
                
                {availableDocs.length > 0 && (
                  <div className="space-y-3 animate-in slide-in-from-bottom-2">
                    <label className="text-sm font-semibold text-slate-900 flex justify-between">
                      <span>2. Select Documents</span>
                      <span className="text-slate-500 font-normal text-xs">{selectedDocs.length} selected</span>
                    </label>
                    <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 bg-white max-h-60 overflow-y-auto">
                      {availableDocs.map(doc => (
                        <label 
                          key={doc.id} 
                          className={`flex items-center gap-4 p-4 cursor-pointer transition-colors ${selectedDocs.includes(doc.id) ? 'bg-blue-50/50' : 'hover:bg-slate-50'}`}
                        >
                          <input 
                            type="checkbox" 
                            className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                            checked={selectedDocs.includes(doc.id)}
                            onChange={(e) => {
                              if (e.target.checked) setSelectedDocs([...selectedDocs, doc.id]);
                              else setSelectedDocs(selectedDocs.filter(id => id !== doc.id));
                            }}
                          />
                          <div className="flex-1">
                            <p className="text-sm font-medium text-slate-900">{doc.title}</p>
                            <p className="text-xs text-slate-500 capitalize">{doc.document_type.replace('_', ' ')} • Hospital #{doc.hospital_id}</p>
                          </div>
                        </label>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-slate-900">3. Your Hospital ID</label>
                    <input 
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 focus:ring-2 focus:ring-blue-500 outline-none" 
                      type="number" 
                      value={reqHospitalId} 
                      onChange={e => setReqHospitalId(e.target.value)} 
                      required 
                      readOnly={doctorVisits.length > 0} 
                      title={doctorVisits.length > 0 ? "Auto-filled based on your current assignment" : ""}
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <label className="text-sm font-semibold text-slate-900">4. Clinical Reason</label>
                    <input 
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none" 
                      type="text" 
                      placeholder="e.g. Follow-up consultation" 
                      value={reqReason} 
                      onChange={e => setReqReason(e.target.value)} 
                      required 
                    />
                  </div>
                </div>
                
                <div className="pt-2">
                  <Button 
                    type="submit" 
                    className="w-full bg-blue-600 hover:bg-blue-700" 
                    disabled={selectedDocs.length === 0 || !reqHospitalId}
                  >
                    Submit Request to Patient
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Sent Requests */}
          <Card>
            <CardHeader className="bg-slate-50/50 border-b border-slate-100">
              <CardTitle className="text-lg">Sent Access Requests</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {accessRequests.length === 0 ? (
                <div className="p-8">
                  <EmptyState 
                    icon={<Clock className="h-8 w-8 text-slate-300" />}
                    title="No requests sent"
                    description="You haven't requested any external records recently."
                  />
                </div>
              ) : (
                <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
                  {accessRequests.map(req => (
                    <div key={req.id} className="p-4 hover:bg-slate-50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-semibold text-slate-900">Patient #{req.patient_id * 13}</h4>
                            <span className="text-xs text-slate-400 font-mono">(ID: {req.patient_id})</span>
                          </div>
                          <p className="text-sm text-slate-600 mt-1">"{req.reason}"</p>
                        </div>
                        
                        {req.status === 'pending' && <Badge variant="secondary" className="bg-amber-100 text-amber-700 border-none"><Clock className="h-3 w-3 mr-1"/> Pending</Badge>}
                        {req.status === 'approved' && <Badge variant="default" className="bg-emerald-100 text-emerald-700 border-none"><CheckCircle className="h-3 w-3 mr-1"/> Approved</Badge>}
                        {req.status === 'rejected' && <Badge variant="destructive" className="bg-rose-100 text-rose-700 border-none"><XCircle className="h-3 w-3 mr-1"/> Rejected</Badge>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Column: Active Grants */}
        <div className="lg:col-span-5">
          <Card className="h-full border-t-4 border-t-emerald-500">
            <CardHeader className="bg-emerald-50/50 border-b border-emerald-100">
              <CardTitle className="text-lg flex items-center gap-2 text-emerald-900">
                <ShieldCheck className="h-5 w-5 text-emerald-600" />
                Active Grants
              </CardTitle>
              <p className="text-sm text-emerald-700/70 mt-1">Documents you currently have clearance to view.</p>
            </CardHeader>
            <CardContent className="p-0">
              {accessGrants.filter(g => g.status === 'active').length === 0 ? (
                <div className="p-12">
                  <EmptyState 
                    icon={<FileText className="h-10 w-10 text-slate-300" />}
                    title="No active grants"
                    description="You don't have temporary access to any external documents."
                  />
                </div>
              ) : (
                <div className="divide-y divide-slate-100">
                  {accessGrants.filter(g => g.status === 'active').map(grant => (
                    <div key={grant.id} className="p-5">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-500">
                          <User className="h-5 w-5" />
                        </div>
                        <div>
                          <h4 className="text-sm font-semibold text-slate-900">Patient #{grant.patient_id * 13}</h4>
                          <p className="text-xs font-medium text-rose-500">
                            Expires: {new Date(grant.expires_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                          </p>
                        </div>
                      </div>
                      
                      <div className="space-y-2">
                        {grant.granted_documents.map((doc: any) => (
                          <div key={doc.id} className="flex items-center justify-between p-3 bg-slate-50 border border-slate-100 rounded-lg group">
                            <div className="flex items-center gap-2 overflow-hidden">
                              <FileText className="h-4 w-4 text-blue-500 shrink-0" />
                              <span className="text-sm font-medium text-slate-700 truncate" title={doc.title}>{doc.title}</span>
                            </div>
                            <Button 
                              variant="ghost" 
                              size="sm" 
                              onClick={() => handleDownload(doc.id, doc.original_filename)}
                              className="h-8 w-8 p-0 text-slate-400 hover:text-blue-600 hover:bg-blue-50 shrink-0"
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

      </div>
    </div>
  );
}
