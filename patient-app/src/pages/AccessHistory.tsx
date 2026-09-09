import { usePatientContext } from '../components/Layout';

export default function AccessHistory() {
  const { accessGrants, handleRevokeGrant } = usePatientContext();

  const activeGrants = accessGrants.filter(g => g.status === 'active');

  return (
    <section className="card">
      <h3 style={{marginBottom: 16}}>Active Access Grants</h3>
      {activeGrants.length === 0 ? (
        <p className="empty-state">No active grants.</p>
      ) : (
        <div className="grant-list">
          {activeGrants.map(grant => (
            <div key={grant.id} style={{border: '1px solid var(--border)', padding: 16, borderRadius: 8, marginBottom: 16, background: '#fff'}}>
              <div style={{display: 'flex', justifyContent: 'space-between'}}>
                <h4 style={{margin: '0 0 8px 0'}}>Doctor ID: {grant.doctor_id}</h4>
                <button onClick={() => handleRevokeGrant(grant.id)} className="btn-secondary" style={{padding: '4px 12px', fontSize: 12, color: 'var(--priority-critical)', borderColor: 'var(--priority-critical)'}}>Revoke Access</button>
              </div>
              <p style={{fontSize: 13, margin: '4px 0'}}>Expires: {new Date(grant.expires_at).toLocaleString()}</p>
              <div style={{marginTop: 12}}>
                <strong style={{fontSize: 14}}>Accessible Documents:</strong>
                <ul style={{margin: '6px 0 0 20px', padding: 0, fontSize: 13}}>
                  {grant.granted_documents.map((doc: any) => (
                    <li key={doc.id} style={{marginBottom: 4}}>{doc.title}</li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
