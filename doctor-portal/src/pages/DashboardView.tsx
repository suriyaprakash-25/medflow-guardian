import { useDoctorContext } from '../components/Layout';

export default function DashboardView() {
  const { isAdmin, adminData, requests, updateStatus } = useDoctorContext();

  if (isAdmin) {
    return (
      <div className="dashboard-grid">
        <div className="column" style={{ width: '100%' }}>
          <section className="card">
            <h3>Hospital Administration (ID: {adminData?.hospital_id})</h3>
            <p style={{fontSize: 13, color: 'var(--text-muted)'}}>Manage hospital operations and monitor data compliance.</p>
            
            <div style={{marginTop: 16}}>
              <h4>Affiliated Doctors ({adminData?.doctors?.length || 0})</h4>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 12, marginTop: 12}}>
                {adminData?.doctors?.map((d: any) => (
                  <div key={d.id} style={{padding: 12, border: '1px solid var(--border)', borderRadius: 8, background: '#f8fafc'}}>
                    <strong>Dr. {d.full_name}</strong>
                    <p style={{margin: '4px 0', fontSize: 13, color: 'var(--text-muted)'}}>{d.email}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </div>
      </div>
    );
  }

  return (
    <section className="card">
      <h3>Patient Triage Queue</h3>
      {requests.length === 0 ? (
        <p className="empty-state">No patients in queue.</p>
      ) : (
        <div className="request-list">
          {requests.map(req => (
            <div key={req.id} className="request-item">
              <div className="request-header">
                <span className="date">Req #{req.id} | {new Date(req.created_at).toLocaleString()}</span>
                <span className={`badge status-${req.status}`}>{req.status.toUpperCase()}</span>
              </div>
              <p className="symptoms">"{req.symptoms}"</p>
              {req.priority && (
                <div className="ai-insight">
                  <span className={`badge priority-${req.priority}`}>AI: {req.priority.toUpperCase()}</span>
                  <p style={{marginTop:8}}>{req.ai_reasoning}</p>
                </div>
              )}
              {req.status === 'pending' && (
                <div className="actions">
                  <button onClick={() => updateStatus(req.id, 'reviewing')} className="btn-primary" style={{marginRight: 8}}>Mark Reviewing</button>
                  <button onClick={() => updateStatus(req.id, 'resolved')} className="btn-secondary">Mark Resolved</button>
                </div>
              )}
              {req.status === 'reviewing' && (
                <div className="actions">
                  <button onClick={() => updateStatus(req.id, 'resolved')} className="btn-primary">Mark Resolved</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
