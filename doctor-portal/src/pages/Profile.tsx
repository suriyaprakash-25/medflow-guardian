import { useDoctorContext } from '../components/Layout';

export default function Profile() {
  const { auditLogs } = useDoctorContext();

  return (
    <div className="dashboard-grid">
      <div className="column">
        <section className="card">
          <h3>Security Audit Logs</h3>
          <p style={{fontSize: 13, color: 'var(--text-muted)', marginBottom: 16}}>Track your activity and accesses across patient records.</p>
          {auditLogs.length === 0 ? (
            <p className="empty-state">No audit logs.</p>
          ) : (
            <div style={{maxHeight: 600, overflowY: 'auto'}}>
              {auditLogs.map(a => (
                <div key={a.id} style={{padding: '12px 0', borderBottom: '1px solid var(--border)'}}>
                  <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 4}}>
                    <strong style={{fontSize: 13, textTransform: 'uppercase'}}>{a.action.replace('_', ' ')}</strong>
                    <span style={{fontSize: 12, color: 'var(--text-muted)'}}>{new Date(a.created_at).toLocaleString()}</span>
                  </div>
                  <p style={{fontSize: 13, margin: '4px 0', color: '#475569'}}>
                    Target User: {a.target_user_id || 'N/A'}
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
