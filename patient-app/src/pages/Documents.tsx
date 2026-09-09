import { usePatientContext } from '../components/Layout';

export default function Documents() {
  const { documents, docFilterHospital, setDocFilterHospital, docFilterType, setDocFilterType, handleDownload } = usePatientContext();

  const filteredDocuments = documents.filter(d => 
    (!docFilterHospital || d.hospital?.name === docFilterHospital) && 
    (!docFilterType || d.document_type === docFilterType)
  );

  return (
    <section className="card documents">
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16}}>
        <h3 style={{margin: 0}}>My Medical Documents</h3>
        <div style={{display: 'flex', gap: 8}}>
          <select className="input-field" style={{padding: '4px 8px', fontSize: 13, margin: 0, width: 140}} value={docFilterHospital} onChange={e => setDocFilterHospital(e.target.value)}>
            <option value="">All Hospitals</option>
            {Array.from(new Set(documents.map(d => d.hospital?.name))).filter(Boolean).map(hName => (
              <option key={hName as string} value={hName as string}>{hName as string}</option>
            ))}
          </select>
          <select className="input-field" style={{padding: '4px 8px', fontSize: 13, margin: 0, width: 140}} value={docFilterType} onChange={e => setDocFilterType(e.target.value)}>
            <option value="">All Types</option>
            {Array.from(new Set(documents.map(d => d.document_type))).filter(Boolean).map(tName => (
              <option key={tName as string} value={tName as string}>{tName as string}</option>
            ))}
          </select>
        </div>
      </div>
      
      {filteredDocuments.length === 0 ? (
        <p className="empty-state">No documents match filters.</p>
      ) : (
        <div className="document-list" style={{marginTop: 12}}>
          {filteredDocuments.map(doc => (
            <div key={doc.id} style={{border: '1px solid var(--border)', padding: 16, borderRadius: 8, marginBottom: 16, background: '#fff'}}>
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                <h4 style={{margin: '0 0 4px 0'}}>{doc.title}</h4>
                <span className="badge" style={{background: '#e2e8f0', color: '#1e293b'}}>{doc.document_type.toUpperCase()}</span>
              </div>
              <p style={{fontSize: 13, color: 'var(--text-muted)', margin: '4px 0'}}>
                Uploaded: {new Date(doc.created_at).toLocaleDateString()} | Size: {(doc.file_size / 1024).toFixed(1)} KB
              </p>
              {doc.description && <p style={{fontSize: 14, margin: '8px 0'}}>{doc.description}</p>}
              <button 
                onClick={() => handleDownload(doc.id, doc.original_filename)} 
                className="btn-secondary" 
                style={{marginTop: 8, padding: '6px 16px', fontSize: 13}}
              >
                Download / Preview
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
