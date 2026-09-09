import { useDoctorContext } from '../components/Layout';

export default function UploadReport() {
  const { 
    doctorVisits, uploadVisitId, setUploadVisitId, 
    uploadType, setUploadType, uploadTitle, setUploadTitle, 
    uploadDesc, setUploadDesc, setUploadFile, 
    uploading, handleUpload 
  } = useDoctorContext();

  return (
    <section className="card">
      <h3>Upload Medical Document</h3>
      <p style={{fontSize: 14, color: 'var(--text-muted)', marginBottom: 24}}>Upload prescriptions, lab reports, or scans for your patients.</p>
      
      <form onSubmit={handleUpload} style={{maxWidth: 600}}>
        <div style={{marginBottom: 16}}>
          <label style={{display: 'block', marginBottom: 8, fontWeight: 'bold'}}>Select Patient Visit</label>
          <select className="input-field" value={uploadVisitId} onChange={e => setUploadVisitId(e.target.value)} required>
            <option value="">Select a visit...</option>
            {doctorVisits.map(v => (
              <option key={v.id} value={v.id}>Patient {v.patient_id} (Visit #{v.id})</option>
            ))}
          </select>
        </div>
        
        <div style={{marginBottom: 16}}>
          <label style={{display: 'block', marginBottom: 8, fontWeight: 'bold'}}>Document Type</label>
          <select className="input-field" value={uploadType} onChange={e => setUploadType(e.target.value)} required>
            <option value="prescription">Prescription</option>
            <option value="lab_report">Lab Report</option>
            <option value="imaging">Imaging/Scan</option>
            <option value="clinical_note">Clinical Note</option>
            <option value="other">Other</option>
          </select>
        </div>
        
        <div style={{marginBottom: 16}}>
          <label style={{display: 'block', marginBottom: 8, fontWeight: 'bold'}}>Title</label>
          <input className="input-field" type="text" value={uploadTitle} onChange={e => setUploadTitle(e.target.value)} required placeholder="e.g. Blood Test Results" />
        </div>
        
        <div style={{marginBottom: 16}}>
          <label style={{display: 'block', marginBottom: 8, fontWeight: 'bold'}}>Description (Optional)</label>
          <textarea className="input-field" value={uploadDesc} onChange={e => setUploadDesc(e.target.value)} rows={3} placeholder="Add any notes..." />
        </div>
        
        <div style={{marginBottom: 24}}>
          <label style={{display: 'block', marginBottom: 8, fontWeight: 'bold'}}>File</label>
          <input type="file" onChange={e => setUploadFile(e.target.files ? e.target.files[0] : null)} required />
        </div>
        
        <button type="submit" className="btn-primary" disabled={uploading}>
          {uploading ? 'Uploading...' : 'Upload Document'}
        </button>
      </form>
    </section>
  );
}
