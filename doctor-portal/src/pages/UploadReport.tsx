import { useState } from 'react';
import { useDoctorContext } from '../lib/doctorContext';
import { Card, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { FormField } from '@shared/ui/FormField';
import { Input } from '@shared/ui/Input';
import { FileUp, FileText, UploadCloud, FileIcon, User, ChevronRight } from 'lucide-react';

const documentTypes = [
  { id: 'prescription', label: 'Prescription' },
  { id: 'lab_report', label: 'Lab report' },
  { id: 'imaging', label: 'Imaging / scan' },
  { id: 'clinical_note', label: 'Clinical note' },
];

export default function UploadReport() {
  const {
    doctorVisits, uploadVisitId, setUploadVisitId,
    uploadType, setUploadType, uploadTitle, setUploadTitle,
    uploadDesc, setUploadDesc, uploadFile, setUploadFile,
    uploading, handleUpload,
  } = useDoctorContext();
  const [step, setStep] = useState(1);
  const canProceedToStep2 = Boolean(uploadVisitId && uploadType);
  const canProceedToStep3 = Boolean(uploadTitle.trim() && uploadFile);
  const selectedVisit = doctorVisits.find((visit) => visit.id.toString() === uploadVisitId);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-950">Upload clinical document</h2>
        <p className="mt-1 text-sm text-slate-600">Attach a document only to a visit assigned to your authenticated clinician context.</p>
      </div>

      <FeedbackState tone="info" title="Verify patient and visit context before upload" message="The server independently validates the selected visit, clinician, hospital and patient relationship before storing the document." compact />

      <ol className="grid grid-cols-3 gap-2" aria-label="Upload progress">
        {['Context', 'Details', 'Confirm'].map((label, index) => {
          const number = index + 1;
          const active = step === number;
          const complete = step > number;
          return (
            <li key={label} aria-current={active ? 'step' : undefined} className={`rounded-xl border p-3 text-center text-xs font-semibold ${active ? 'border-blue-600 bg-blue-50 text-blue-800' : complete ? 'border-emerald-300 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-white text-slate-600'}`}>
              <span className="block text-sm">{number}</span>{label}
            </li>
          );
        })}
      </ol>

      <Card>
        <CardContent className="p-6 md:p-8">
          <form onSubmit={handleUpload}>
            {step === 1 ? (
              <div className="space-y-6">
                <FormField id="upload-visit" label="Patient visit" hint="Choose the authoritative visit that this document belongs to." required>
                  <select id="upload-visit" className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-blue-600" value={uploadVisitId} onChange={(event) => setUploadVisitId(event.target.value)} required>
                    <option value="">Select a patient visit</option>
                    {doctorVisits.map((visit) => <option key={visit.id} value={visit.id}>Patient ID {visit.patient_id} · Visit ID {visit.id}{visit.hospital?.name ? ` · ${visit.hospital.name}` : ''}</option>)}
                  </select>
                </FormField>

                <fieldset>
                  <legend className="text-sm font-semibold text-slate-900">Document category <span className="text-rose-600">*</span></legend>
                  <p className="mt-1 text-xs text-slate-600">Choose the category that best matches the file being uploaded.</p>
                  <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
                    {documentTypes.map((type) => (
                      <label key={type.id} className={`flex min-h-24 cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border p-3 text-center transition-colors focus-within:ring-2 focus-within:ring-blue-600 ${uploadType === type.id ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}>
                        <input className="sr-only" type="radio" name="document-type" value={type.id} checked={uploadType === type.id} onChange={() => setUploadType(type.id)} required />
                        <FileText className="h-6 w-6" aria-hidden="true" />
                        <span className="text-xs font-semibold">{type.label}</span>
                      </label>
                    ))}
                  </div>
                </fieldset>

                <div className="flex justify-end pt-4"><Button type="button" onClick={() => setStep(2)} disabled={!canProceedToStep2}>Continue <ChevronRight className="ml-2 h-4 w-4" aria-hidden="true" /></Button></div>
              </div>
            ) : null}

            {step === 2 ? (
              <div className="space-y-6">
                <FormField id="upload-title" label="Document title" required>
                  <Input id="upload-title" value={uploadTitle} onChange={(event) => setUploadTitle(event.target.value)} placeholder="Example: Complete blood count results" required />
                </FormField>
                <FormField id="upload-notes" label="Clinical notes" hint="Optional context. Do not add information unrelated to the selected patient visit.">
                  <textarea id="upload-notes" value={uploadDesc} onChange={(event) => setUploadDesc(event.target.value)} rows={4} className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm focus-visible:ring-2 focus-visible:ring-blue-600" />
                </FormField>
                <FormField id="file-upload" label="File" hint="Choose the clinical file from your device. The server applies content validation and malware scanning." required>
                  <input id="file-upload" type="file" className="block min-h-11 w-full rounded-xl border border-slate-300 bg-white p-2 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-blue-50 file:px-3 file:py-2 file:font-semibold file:text-blue-800" onChange={(event) => setUploadFile(event.target.files?.[0] || null)} required />
                </FormField>
                {uploadFile ? (
                  <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3" role="status">
                    <FileIcon className="h-7 w-7 shrink-0 text-blue-600" aria-hidden="true" />
                    <div className="min-w-0"><p className="truncate text-sm font-semibold text-slate-900">{uploadFile.name}</p><p className="text-xs text-slate-600">{(uploadFile.size / 1024 / 1024).toFixed(2)} MB selected</p></div>
                  </div>
                ) : null}
                <div className="flex justify-between gap-3 pt-4"><Button type="button" variant="outline" onClick={() => setStep(1)}>Back</Button><Button type="button" onClick={() => setStep(3)} disabled={!canProceedToStep3}>Review <ChevronRight className="ml-2 h-4 w-4" aria-hidden="true" /></Button></div>
              </div>
            ) : null}

            {step === 3 ? (
              <div className="space-y-6">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
                  <h3 className="font-semibold text-slate-950">Upload summary</h3>
                  <dl className="mt-4 grid grid-cols-[minmax(7rem,0.7fr)_1.3fr] gap-x-4 gap-y-3 text-sm">
                    <dt className="text-slate-600">Patient</dt><dd className="font-semibold text-slate-950"><span className="inline-flex items-center gap-2"><User className="h-4 w-4 text-slate-500" aria-hidden="true" />{selectedVisit ? `Patient ID ${selectedVisit.patient_id}` : 'Not selected'}</span></dd>
                    <dt className="text-slate-600">Visit</dt><dd className="font-semibold text-slate-950">{selectedVisit ? `Visit ID ${selectedVisit.id}` : 'Not selected'}</dd>
                    <dt className="text-slate-600">Category</dt><dd className="font-semibold capitalize text-slate-950">{uploadType.replace('_', ' ')}</dd>
                    <dt className="text-slate-600">Title</dt><dd className="font-semibold text-slate-950">{uploadTitle}</dd>
                    <dt className="text-slate-600">File</dt><dd className="inline-flex min-w-0 items-center gap-2 font-semibold text-slate-950"><FileUp className="h-4 w-4 shrink-0 text-blue-600" aria-hidden="true" /><span className="truncate">{uploadFile?.name}</span></dd>
                  </dl>
                </div>
                <div className="flex justify-between gap-3 pt-4"><Button type="button" variant="outline" onClick={() => setStep(2)}>Edit details</Button><Button type="submit" disabled={uploading}>{uploading ? 'Uploading securely…' : <><UploadCloud className="mr-2 h-4 w-4" aria-hidden="true" />Confirm upload</>}</Button></div>
              </div>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
