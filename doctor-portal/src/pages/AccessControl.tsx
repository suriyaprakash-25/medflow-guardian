import { useEffect, useState } from 'react';
import { useDoctorContext } from '../lib/doctorContext';
import { Card, CardHeader, CardTitle, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { Badge } from '@shared/ui/Badge';
import { EmptyState } from '@shared/ui/EmptyState';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { FormField } from '@shared/ui/FormField';
import { Input } from '@shared/ui/Input';
import { IconButton } from '@shared/ui/IconButton';
import { Tabs } from '@shared/ui/Tabs';
import { ShieldCheck, Search, ShieldAlert, FileText, CheckCircle, Clock, XCircle, Download, User } from 'lucide-react';

export default function AccessControl() {
  const {
    reqPatientId, setReqPatientId, reqHospitalId, setReqHospitalId,
    reqReason, setReqReason, availableDocs, selectedDocs, setSelectedDocs,
    fetchingDocs, handleFetchPatientDocs, handleRequestAccess, handleDownload,
    accessRequests, accessGrants, doctorVisits,
  } = useDoctorContext();
  const [historyTab, setHistoryTab] = useState<'requests' | 'grants'>('requests');

  useEffect(() => {
    if (!reqHospitalId && doctorVisits.length > 0 && doctorVisits[0].hospital_id) {
      setReqHospitalId(doctorVisits[0].hospital_id.toString());
    }
  }, [doctorVisits, reqHospitalId, setReqHospitalId]);

  const activeGrants = accessGrants.filter((grant) => grant.status === 'active');

  const requestHistory = accessRequests.length === 0 ? (
    <EmptyState icon={<Clock className="h-8 w-8 text-slate-400" />} title="No access requests sent" description="Requests you submit for external records will appear here." />
  ) : (
    <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white">
      {accessRequests.map((request) => (
        <article key={request.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h4 className="text-sm font-semibold text-slate-950">Patient ID {request.patient_id}</h4>
            <p className="mt-1 text-sm text-slate-700">{request.reason || 'No reason recorded'}</p>
            <p className="mt-1 text-xs text-slate-500">Request ID {request.id}</p>
          </div>
          {request.status === 'pending' ? <Badge variant="secondary" className="bg-amber-100 text-amber-900"><Clock className="mr-1 h-3 w-3" aria-hidden="true" />Pending</Badge> : null}
          {request.status === 'approved' ? <Badge className="bg-emerald-100 text-emerald-900"><CheckCircle className="mr-1 h-3 w-3" aria-hidden="true" />Approved</Badge> : null}
          {request.status === 'rejected' ? <Badge variant="destructive" className="bg-rose-100 text-rose-900"><XCircle className="mr-1 h-3 w-3" aria-hidden="true" />Rejected</Badge> : null}
        </article>
      ))}
    </div>
  );

  const grantsHistory = activeGrants.length === 0 ? (
    <EmptyState icon={<FileText className="h-9 w-9 text-slate-400" />} title="No active grants" description="Patient-approved temporary document access will appear here." />
  ) : (
    <div className="space-y-4">
      {activeGrants.map((grant) => (
        <article key={grant.id} className="rounded-xl border border-emerald-200 bg-white p-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-600"><User className="h-5 w-5" aria-hidden="true" /></div>
              <div><h4 className="text-sm font-semibold text-slate-950">Patient ID {grant.patient_id}</h4><p className="text-xs text-slate-600">Grant ID {grant.id}</p></div>
            </div>
            <p className="text-xs font-semibold text-rose-700">Expires {new Date(grant.expires_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</p>
          </div>
          <ul className="mt-4 space-y-2" aria-label={`Documents granted for patient ID ${grant.patient_id}`}>
            {grant.granted_documents.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between gap-3 rounded-lg border border-slate-100 bg-slate-50 p-3">
                <div className="flex min-w-0 items-center gap-2"><FileText className="h-4 w-4 shrink-0 text-blue-600" aria-hidden="true" /><span className="truncate text-sm font-medium text-slate-800">{doc.title}</span></div>
                <IconButton label={`Download ${doc.title}`} onClick={() => handleDownload(doc.id, doc.original_filename)} className="shrink-0"><Download className="h-4 w-4" aria-hidden="true" /></IconButton>
              </li>
            ))}
          </ul>
        </article>
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-950">Patient-authorized access</h2>
        <p className="mt-1 text-sm text-slate-600">Request temporary access to records outside your current visit context. Patient consent and server policy determine whether access is granted.</p>
      </div>

      <FeedbackState tone="info" title="Access is not granted by this form" message="Submitting a request creates a consent workflow. Document release remains enforced by the server using patient, practitioner, organization and purpose context." compact />

      <Card>
        <CardHeader className="border-b border-slate-100 bg-slate-50/50"><CardTitle className="flex items-center gap-2 text-lg"><ShieldAlert className="h-5 w-5 text-blue-700" aria-hidden="true" />Request external records</CardTitle></CardHeader>
        <CardContent className="p-6">
          <form onSubmit={handleRequestAccess} className="space-y-6">
            <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
              <FormField id="access-patient-id" label="Patient ID" hint="Enter the authoritative system patient ID." required>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-500" aria-hidden="true" />
                  <Input id="access-patient-id" type="number" min="1" value={reqPatientId} onChange={(event) => setReqPatientId(event.target.value)} className="pl-10" required />
                </div>
              </FormField>
              <Button type="button" variant="secondary" onClick={handleFetchPatientDocs} disabled={fetchingDocs || !reqPatientId || !reqHospitalId}>{fetchingDocs ? 'Finding records…' : 'Find record metadata'}</Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <FormField id="access-hospital-id" label="Your hospital ID" hint={doctorVisits.length > 0 ? 'Derived from your current clinician assignment.' : 'Required organization context.'} required>
                <Input id="access-hospital-id" type="number" min="1" value={reqHospitalId} onChange={(event) => setReqHospitalId(event.target.value)} readOnly={doctorVisits.length > 0} required />
              </FormField>
              <FormField id="access-reason" label="Clinical purpose" hint="Explain why these records are needed for treatment." required>
                <Input id="access-reason" value={reqReason} onChange={(event) => setReqReason(event.target.value)} placeholder="Example: follow-up consultation" required />
              </FormField>
            </div>

            {availableDocs.length > 0 ? (
              <fieldset>
                <legend className="text-sm font-semibold text-slate-900">Select requested documents</legend>
                <p className="mt-1 text-xs text-slate-600">Only metadata is shown before patient authorization. Select the minimum records necessary.</p>
                <div className="mt-3 max-h-64 divide-y divide-slate-100 overflow-y-auto rounded-xl border border-slate-200 bg-white">
                  {availableDocs.map((doc) => (
                    <label key={doc.id} className={`flex min-h-14 cursor-pointer items-center gap-4 p-4 ${selectedDocs.includes(doc.id) ? 'bg-blue-50' : 'hover:bg-slate-50'}`}>
                      <input type="checkbox" className="h-5 w-5 rounded border-slate-300 text-blue-700 focus:ring-blue-600" checked={selectedDocs.includes(doc.id)} onChange={(event) => setSelectedDocs(event.target.checked ? [...selectedDocs, doc.id] : selectedDocs.filter((id) => id !== doc.id))} />
                      <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-slate-950">{doc.title}</p><p className="text-xs capitalize text-slate-600">{doc.document_type.replace('_', ' ')} · Hospital ID {doc.hospital_id}</p></div>
                    </label>
                  ))}
                </div>
                <p className="mt-2 text-xs font-medium text-slate-600" role="status">{selectedDocs.length} document{selectedDocs.length === 1 ? '' : 's'} selected</p>
              </fieldset>
            ) : null}

            <Button type="submit" className="w-full" disabled={!reqPatientId || !reqHospitalId || !reqReason.trim() || selectedDocs.length === 0}>Send consent request to patient</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-slate-100"><CardTitle className="flex items-center gap-2 text-lg"><ShieldCheck className="h-5 w-5 text-emerald-700" aria-hidden="true" />Access activity</CardTitle></CardHeader>
        <CardContent className="p-5">
          <Tabs
            label="Access activity"
            activeId={historyTab}
            onChange={(id) => setHistoryTab(id as 'requests' | 'grants')}
            items={[
              { id: 'requests', label: `Requests (${accessRequests.length})`, content: requestHistory },
              { id: 'grants', label: `Active grants (${activeGrants.length})`, content: grantsHistory },
            ]}
          />
        </CardContent>
      </Card>
    </div>
  );
}
