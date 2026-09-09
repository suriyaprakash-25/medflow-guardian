import { usePatientContext } from '../components/Layout';

export default function Profile() {
  const { patientVisits, requests, auditLogs } = usePatientContext();

  return (
    <div className="dashboard-grid">
      <div className="column">
        <section className="card">
          <h3>My Profile & Visit History</h3>
          <p style={{fontSize: 14, color: 'var(--text-muted)', marginBottom: 16}}>Manage your identity and track your interactions across different hospitals.</p>
          {patientVisits.length === 0 ? (
            <p className="empty-state">No visits recorded.</p>
          ) : (
            <div style={{display: 'flex', flexDirection: 'column', gap: 12}}>
              {patientVisits.map(v => (
                <div key={v.id} style={{padding: 12, background: '#f8fafc', border: '1px solid var(--border)', borderRadius: 8}}>
                  <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                    <strong>{v.hospital?.name}</strong>
                    <span style={{fontSize: 12, background: 'var(--primary)', color: 'white', padding: '4px 8px', borderRadius: 12}}>{v.status}</span>
                  </div>
                  <p style={{margin: '6px 0', fontSize: 14}}>Dr. {v.doctor?.full_name}</p>
                  <p style={{margin: '6px 0', fontSize: 13, color: 'var(--text-muted)'}}>Reason: {v.reason}</p>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="card history" style={{marginTop: 24}}>
          <h3>My Triage History</h3>
          {requests.length === 0 ? (
            <p className="empty-state">No past requests.</p>
          ) : (
            <div className="request-list">
              {requests.map(req => (
                <div key={req.id} className="request-item">
                  <div className="request-header">
                    <span className="date">{new Date(req.created_at).toLocaleString()}</span>
                    <span className={`badge status-${req.status}`}>{req.status.toUpperCase()}</span>
                  </div>
                  <p className="symptoms">"{req.symptoms}"</p>
                  {req.priority && (
                    <div className="ai-insight">
                      <span className={`badge priority-${req.priority}`}>AI: {req.priority.toUpperCase()}</span>
                      <p style={{marginTop:8}}>{req.ai_reasoning}</p>
                      {req.disclaimer && (
                        <p style={{fontSize:12,color:'#64748b',marginTop:6,fontStyle:'italic'}}>{req.disclaimer}</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <div className="column">
        <section className="card">
          <h3>Security Audit Logs</h3>
          <p style={{fontSize: 13, color: 'var(--text-muted)', marginBottom: 16}}>Track all accesses and activities on your medical records.</p>
          {auditLogs.length === 0 ? (
            <p className="empty-state">No audit logs.</p>
          ) : (
            <div style={{maxHeight: 400, overflowY: 'auto'}}>
              {auditLogs.map(a => (
                <div key={a.id} style={{padding: '12px 0', borderBottom: '1px solid var(--border)'}}>
                  <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 4}}>
                    <strong style={{fontSize: 13, textTransform: 'uppercase'}}>{a.action.replace('_', ' ')}</strong>
                    <span style={{fontSize: 12, color: 'var(--text-muted)'}}>{new Date(a.created_at).toLocaleString()}</span>
                  </div>
                  <p style={{fontSize: 13, margin: '4px 0', color: '#475569'}}>
                    Actor: {a.actor_role} ({a.actor_id})
                    {a.document_id && ` | Doc: ${a.document_id}`}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
