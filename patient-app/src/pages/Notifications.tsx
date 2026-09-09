import { usePatientContext } from '../components/Layout';

export default function Notifications() {
  const { notifications, handleMarkRead, handleMarkAllRead } = usePatientContext();

  return (
    <section className="card">
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16}}>
        <h3 style={{margin: 0}}>Notifications</h3>
        {notifications.some(n => !n.is_read) && (
          <button onClick={handleMarkAllRead} className="btn-secondary" style={{fontSize: 13, padding: '4px 12px'}}>Mark all read</button>
        )}
      </div>
      {notifications.length === 0 ? (
        <p className="empty-state">No notifications.</p>
      ) : (
        <div style={{overflowY: 'auto'}}>
          {notifications.map(n => (
            <div 
              key={n.id} 
              style={{
                padding: 12, 
                borderBottom: '1px solid var(--border)', 
                background: n.is_read ? 'transparent' : '#f0f9ff', 
                cursor: 'pointer',
                borderRadius: 4
              }} 
              onClick={() => !n.is_read && handleMarkRead(n.id)}
            >
              <p style={{margin: '0 0 6px 0', fontSize: 14, fontWeight: n.is_read ? 'normal' : 'bold'}}>{n.message}</p>
              <span style={{fontSize: 12, color: 'var(--text-muted)'}}>{new Date(n.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
