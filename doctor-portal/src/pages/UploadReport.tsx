import { useState } from 'react';
import { useDoctorContext } from '../components/Layout';
import { Card, CardContent } from '@shared/ui/Card';
import { Button } from '@shared/ui/Button';
import { FileUp, FileText, UploadCloud, FileIcon, User, ChevronRight } from 'lucide-react';

export default function UploadReport() {
  const { 
    doctorVisits, uploadVisitId, setUploadVisitId, 
    uploadType, setUploadType, uploadTitle, setUploadTitle, 
    uploadDesc, setUploadDesc, uploadFile, setUploadFile, 
    uploading, handleUpload 
  } = useDoctorContext();

  const [step, setStep] = useState(1);

  const canProceedToStep2 = uploadVisitId && uploadType;
  const canProceedToStep3 = uploadTitle && uploadFile;

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-900">Upload Clinical Document</h2>
        <p className="text-sm text-slate-500 mt-1">Securely attach lab reports, prescriptions, or imaging to a patient's record.</p>
      </div>

      <div className="flex items-center justify-between mb-8">
        <div className="flex flex-col items-center">
          <div className={`h-8 w-8 rounded-full flex items-center justify-center font-bold ${step >= 1 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>1</div>
          <span className="text-xs font-medium mt-2 text-slate-600">Context</span>
        </div>
        <div className={`flex-1 h-1 mx-4 rounded-full ${step >= 2 ? 'bg-blue-600' : 'bg-slate-200'}`}></div>
        <div className="flex flex-col items-center">
          <div className={`h-8 w-8 rounded-full flex items-center justify-center font-bold ${step >= 2 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>2</div>
          <span className="text-xs font-medium mt-2 text-slate-600">Details</span>
        </div>
        <div className={`flex-1 h-1 mx-4 rounded-full ${step >= 3 ? 'bg-blue-600' : 'bg-slate-200'}`}></div>
        <div className="flex flex-col items-center">
          <div className={`h-8 w-8 rounded-full flex items-center justify-center font-bold ${step >= 3 ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>3</div>
          <span className="text-xs font-medium mt-2 text-slate-600">Confirm</span>
        </div>
      </div>

      <Card>
        <CardContent className="p-6 md:p-8">
          <form onSubmit={handleUpload}>
            {step === 1 && (
              <div className="space-y-6 animate-in slide-in-from-right-4">
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-900">Select Patient Visit</label>
                  <p className="text-xs text-slate-500">Which active visit does this document belong to?</p>
                  <select 
                    className="w-full border border-slate-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none" 
                    value={uploadVisitId} 
                    onChange={e => setUploadVisitId(e.target.value)} 
                    required
                  >
                    <option value="">Select a patient visit...</option>
                    {doctorVisits.map(v => (
                      <option key={v.id} value={v.id}>Patient #{v.patient_id * 13} (Visit #{v.id})</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-900">Document Category</label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-2">
                    {[
                      { id: 'prescription', label: 'Prescription' },
                      { id: 'lab_report', label: 'Lab Report' },
                      { id: 'imaging', label: 'Imaging/Scan' },
                      { id: 'clinical_note', label: 'Clinical Note' }
                    ].map(type => (
                      <div 
                        key={type.id}
                        onClick={() => setUploadType(type.id)}
                        className={`border rounded-xl p-4 cursor-pointer flex flex-col items-center gap-3 transition-all ${
                          uploadType === type.id 
                            ? 'border-blue-600 bg-blue-50 ring-2 ring-blue-100' 
                            : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                        }`}
                      >
                        <FileText className={`h-6 w-6 ${uploadType === type.id ? 'text-blue-600' : 'text-slate-400'}`} />
                        <span className={`text-xs text-center font-medium ${uploadType === type.id ? 'text-blue-700' : 'text-slate-600'}`}>
                          {type.label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end pt-4">
                  <Button 
                    type="button" 
                    onClick={() => setStep(2)} 
                    disabled={!canProceedToStep2}
                    className="gap-2"
                  >
                    Continue <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-6 animate-in slide-in-from-right-4">
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-900">Document Title</label>
                  <input 
                    type="text" 
                    value={uploadTitle} 
                    onChange={e => setUploadTitle(e.target.value)} 
                    required 
                    placeholder="e.g., Complete Blood Count (CBC) Results" 
                    className="w-full border border-slate-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-900">Clinical Notes (Optional)</label>
                  <textarea 
                    value={uploadDesc} 
                    onChange={e => setUploadDesc(e.target.value)} 
                    rows={3} 
                    placeholder="Add any relevant observations..." 
                    className="w-full border border-slate-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none resize-none"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold text-slate-900">Select File</label>
                  <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center bg-slate-50/50 hover:bg-slate-50 transition-colors">
                    <input 
                      type="file" 
                      id="file-upload"
                      className="hidden"
                      onChange={e => setUploadFile(e.target.files ? e.target.files[0] : null)} 
                      required 
                    />
                    <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center gap-3">
                      <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                        <UploadCloud className="h-6 w-6" />
                      </div>
                      <div>
                        <span className="text-blue-600 font-medium text-sm hover:underline">Click to browse</span>
                        <span className="text-slate-500 text-sm"> or drag and drop</span>
                      </div>
                      <p className="text-xs text-slate-400">PDF, JPG, PNG up to 10MB</p>
                    </label>
                    
                    {uploadFile && (
                      <div className="mt-4 p-3 bg-white border border-slate-200 rounded-lg flex items-center gap-3 text-left">
                        <FileIcon className="h-8 w-8 text-blue-500 shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-slate-900 truncate">{uploadFile.name}</p>
                          <p className="text-xs text-slate-500">{(uploadFile.size / 1024 / 1024).toFixed(2)} MB</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex justify-between pt-4">
                  <Button type="button" variant="outline" onClick={() => setStep(1)}>Back</Button>
                  <Button 
                    type="button" 
                    onClick={() => setStep(3)} 
                    disabled={!canProceedToStep3}
                    className="gap-2"
                  >
                    Review <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-6 animate-in slide-in-from-right-4">
                <div className="bg-slate-50 rounded-xl p-6 border border-slate-200 space-y-4">
                  <h3 className="font-semibold text-slate-900 border-b border-slate-200 pb-2">Upload Summary</h3>
                  
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div className="text-slate-500">Target Patient</div>
                    <div className="col-span-2 font-medium text-slate-900 flex items-center gap-2">
                      <User className="h-4 w-4 text-slate-400" /> 
                      Patient #{doctorVisits.find(v => v.id.toString() === uploadVisitId)?.patient_id! * 13}
                    </div>
                    
                    <div className="text-slate-500">Category</div>
                    <div className="col-span-2 font-medium text-slate-900 capitalize">
                      {uploadType.replace('_', ' ')}
                    </div>
                    
                    <div className="text-slate-500">Title</div>
                    <div className="col-span-2 font-medium text-slate-900">{uploadTitle}</div>
                    
                    <div className="text-slate-500">File</div>
                    <div className="col-span-2 font-medium text-slate-900 flex items-center gap-2">
                      <FileUp className="h-4 w-4 text-blue-500" />
                      {uploadFile?.name}
                    </div>
                  </div>
                </div>

                <div className="flex justify-between pt-4">
                  <Button type="button" variant="outline" onClick={() => setStep(2)}>Edit Details</Button>
                  <Button 
                    type="submit" 
                    disabled={uploading}
                    className="bg-blue-600 hover:bg-blue-700 min-w-[140px]"
                  >
                    {uploading ? (
                      <span className="flex items-center gap-2">
                        <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        Uploading...
                      </span>
                    ) : (
                      <span className="flex items-center gap-2">
                        <UploadCloud className="h-4 w-4" /> Confirm Upload
                      </span>
                    )}
                  </Button>
                </div>
              </div>
            )}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
