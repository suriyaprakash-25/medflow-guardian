import { useDoctorContext } from '../components/Layout';

export default function AccessControl() {
  const { 
    reqPatientId, setReqPatientId, reqHospitalId, setReqHospitalId, 
    reqReason, setReqReason, availableDocs, selectedDocs, setSelectedDocs, 
    fetchingDocs, handleFetchPatientDocs, handleRequestAccess, handleDownload,
    accessRequests, accessGrants 
  } = useDoctorContext();

  return (
    <div className="dashboard-grid">
      <div className="column">
        <section className="card">
          <h3>Request External Records</h3>
          <p style={{fontSize: 14, color: 'var(--text-muted)', marginBottom: 24}}>Request temporary access to a patient's documents from other hospitals.</p>
          
          <form onSubmit={handleRequestAccess}>
            <div style={{display: 'flex', gap: 12, marginBottom: 16}}>
              <input className="input-field" style={{flex: 1}} type="number" placeholder="Patient ID" value={reqPatientId} onChange={e => setReqPatientId(e.target.value)} required />
              <button type="button" className="btn-secondary" onClick={handleFetchPatientDocs} disabled={fetchingDocs || !reqPatientId}>
                {fetchingDocs ? 'Fetching...' : 'Find Documents'}
              </button>
            </div>
            
            {availableDocs.length > 0 && (
              <div style={{marginBottom: 20, background: '#f8fafc', padding: 16, borderRadius: 8}}>
                <strong style={{display: 'block', marginBottom: 12}}>Select Documents to Request:</strong>
                {availableDocs.map(doc => (
                  <div key={doc.id} style={{marginBottom: 8}}>
                    <label style={{display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer'}}>
                      <input 
                        type="checkbox" 
                        checked={selectedDocs.includes(doc.id)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedDocs([...selectedDocs, doc.id]);
                          else setSelectedDocs(selectedDocs.filter(id => id !== doc.id));
                        }}
                      />
                      <span>{doc.title} ({doc.document_type}) - Hospital {doc.hospital_id}</span>
                    </label>
                  </div>
                ))}
              </div>
            )}

            <div style={{marginBottom: 16}}>
              <label style={{display: 'block', marginBottom: 8, fontWeight: 'bold'}}>Requesting Hospital ID</label>
              <input className="input-field" type="number" placeholder="Your Hospital ID" value={reqHospitalId} onChange={e => setReqHospitalId(e.target.value)} required />
            </div>
            
            <div style={{marginBottom: 16}}>
              <label style={{display: 'block', marginBottom: 8, fontWeight: 'bold'}}>Reason for Access</label>
              <input className="input-field" type="text" placeholder="e.g. Follow-up consultation" value={reqReason} onChange={e => setReqReason(e.target.value)} required />
            </div>
            
            <button type="submit" className="btn-primary" disabled={selectedDocs.length === 0 || !reqHospitalId}>Submit Request to Patient</button>
          </form>
        </section>

        <section className="card" style={{marginTop: 24}}>
          <h3>Sent Access Requests</h3>
          {accessRequests.length === 0 ? (
            <p className="empty-state">No requests sent.</p>
          ) : (
            <div style={{display: 'flex', flexDirection: 'column', gap: 12}}>
              {accessRequests.map(req => (
                <div key={req.id} style={{padding: 12, border: '1px solid var(--border)', borderRadius: 8, background: req.status === 'pending' ? '#fdfcbc' : req.status === 'approved' ? '#dcfce7' : '#fee2e2'}}>
                  <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 4}}>
                    <strong style={{fontSize: 14}}>Patient {req.patient_id}</strong>
                    <span className={`badge status-${req.status}`}>{req.status.toUpperCase()}</span>
                  </div>
                  <p style={{fontSize: 13, margin: '4px 0'}}>Reason: {req.reason}</p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="column">
        <section className="card">
          <h3>Active Patient Grants</h3>
          <p style={{fontSize: 13, color: 'var(--text-muted)', marginBottom: 16}}>Documents you currently have access to.</p>
          {accessGrants.filter(g => g.status === 'active').length === 0 ? (
            <p className="empty-state">No active grants.</p>
          ) : (
            <div className="grant-list">
              {accessGrants.filter(g => g.status === 'active').map(grant => (
                <div key={grant.id} style={{border: '1px solid var(--border)', padding: 16, borderRadius: 8, marginBottom: 16}}>
                  <h4 style={{margin: '0 0 4px 0'}}>Patient ID: {grant.patient_id}</h4>
                  <p style={{fontSize: 13, margin: '4px 0', color: 'var(--priority-critical)'}}>Expires: {new Date(grant.expires_at).toLocaleString()}</p>
                  <div style={{marginTop: 12}}>
                    {grant.granted_documents.map((doc: any) => (
                      <div key={doc.id} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f5f9'}}>
                        <span style={{fontSize: 14}}>{doc.title}</span>
                        <button onClick={() => handleDownload(doc.id, doc.original_filename)} className="btn-secondary" style={{padding: '4px 12px', fontSize: 12}}>View</button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
