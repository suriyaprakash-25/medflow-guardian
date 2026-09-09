import { usePatientContext } from '../components/Layout';

export default function AccessRequests() {
  const { accessRequests, durations, setDurations, handleApproveAccess, handleRejectAccess } = usePatientContext();

  const pendingRequests = accessRequests.filter(r => r.status === 'pending');

  return (
    <section className="card">
      <h3 style={{marginBottom: 16}}>Document Access Requests</h3>
      {pendingRequests.length === 0 ? (
        <p className="empty-state">No pending access requests.</p>
      ) : (
        <div className="request-list">
          {pendingRequests.map(req => (
            <div key={req.id} style={{border: '1px solid var(--status-pending)', padding: 16, borderRadius: 8, marginBottom: 16, background: '#fdfcbc'}}>
              <h4 style={{margin: '0 0 8px 0'}}>Request from Doctor ID: {req.requesting_doctor_id} (Hospital {req.requesting_hospital_id})</h4>
              <p style={{margin: '4px 0', fontSize: 14}}><strong>Reason:</strong> {req.reason}</p>
              <div style={{margin: '12px 0'}}>
                <strong>Requested Documents:</strong>
                <ul style={{margin: '6px 0 0 20px', padding: 0, fontSize: 14}}>
                  {req.requested_documents.map((doc: any) => (
                    <li key={doc.id} style={{marginBottom: 4}}>{doc.title} ({doc.document_type})</li>
                  ))}
                </ul>
              </div>
              
              <div style={{marginTop: 16, display: 'flex', gap: 12, alignItems: 'center'}}>
                <select 
                  value={durations[req.id] || 1} 
                  onChange={e => setDurations({...durations, [req.id]: parseInt(e.target.value)})}
                  style={{padding: '6px 12px', borderRadius: 4, border: '1px solid #cbd5e1'}}
                >
                  <option value={1}>1 hour</option>
                  <option value={4}>4 hours</option>
                  <option value={24}>1 day</option>
                  <option value={96}>4 days</option>
                </select>
                <button onClick={() => handleApproveAccess(req)} className="btn-primary" style={{padding: '6px 16px', fontSize: 13}}>Approve</button>
                <button onClick={() => handleRejectAccess(req.id)} className="btn-secondary" style={{padding: '6px 16px', fontSize: 13}}>Reject</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
