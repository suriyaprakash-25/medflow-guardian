import { usePatientContext } from '../components/Layout';

export default function DashboardView() {
  const { 
    patientVisits, selectedHospitalId, setSelectedHospitalId, symptoms, setSymptoms, 
    submitting, handleSubmit, vitalsOn, setVitalsOn, readings, activeDoctorId, setActiveDoctorId,
    messages, chatInput, setChatInput, sendMessage
  } = usePatientContext();

  return (
    <div className="dashboard-grid">
      <div className="column">
        <section className="card new-request">
          <h3>Submit New Symptoms</h3>
          {patientVisits.length === 0 ? (
            <p>You need at least one hospital visit to request triage.</p>
          ) : (
            <form onSubmit={handleSubmit}>
              <select 
                value={selectedHospitalId}
                onChange={e => setSelectedHospitalId(e.target.value)}
                required
                style={{ width: '100%', padding: '10px', marginBottom: '10px' }}
              >
                <option value="">Select a Hospital</option>
                {Array.from(new Map(patientVisits.filter(v => v.hospital).map(v => [v.hospital.id, v.hospital])).values()).map(h => (
                  <option key={h.id} value={h.id}>{h.name}</option>
                ))}
              </select>
              <textarea 
                value={symptoms} 
                onChange={e => setSymptoms(e.target.value)} 
                placeholder="Describe your symptoms..."
                required
                rows={4}
                style={{ width: '100%', padding: '10px', boxSizing: 'border-box' }}
              />
              <br/><br/>
              <button type="submit" className="btn-primary" disabled={submitting}>
                {submitting ? 'Submitting...' : 'Request Triage'}
              </button>
            </form>
          )}
        </section>
      </div>

      <div className="column">
        <section className="card monitor">
          <h3>Vitals Monitor</h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <p>Simulate hardware readings?</p>
            <button onClick={() => setVitalsOn(!vitalsOn)} className={vitalsOn ? 'btn-primary' : 'btn-secondary'}>
              {vitalsOn ? 'Monitor ON' : 'Monitor OFF'}
            </button>
          </div>
          {vitalsOn && <p style={{color: 'var(--priority-high)', fontSize: 12}}>Broadcasting simulated vitals every 5s...</p>}
          
          <div style={{marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)'}}>
            <h4>Recent Readings</h4>
            {readings.length === 0 ? (
              <p className="empty-state">No past readings.</p>
            ) : (
              <div style={{maxHeight: 200, overflowY: 'auto', fontSize: 14}}>
                {readings.map(r => (
                  <div key={r.id} style={{padding: '8px 0', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between'}}>
                    <span style={{color: 'var(--text-muted)'}}>{new Date(r.created_at).toLocaleTimeString()}</span>
                    <span>HR: {r.heart_rate} | O2: {r.oxygen_level}% | BP: {r.blood_pressure_sys}/{r.blood_pressure_dia}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="card chat" style={{marginTop: 24, height: 400, display: 'flex', flexDirection: 'column'}}>
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
            <h3>Chat with Doctor</h3>
            <select 
              className="input-field" 
              style={{width: '200px', margin: 0}}
              value={activeDoctorId || ''} 
              onChange={(e) => setActiveDoctorId(Number(e.target.value))}
            >
              {patientVisits.map(v => (
                <option key={v.doctor_id} value={v.doctor_id}>Dr. {v.doctor.full_name}</option>
              ))}
            </select>
          </div>
          
          <div style={{flex: 1, overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 6, padding: 12, marginBottom: 12, marginTop: 12}}>
            {messages.map(m => (
              <div key={m.id} style={{textAlign: m.sender_id === activeDoctorId ? 'left' : 'right', margin: '8px 0'}}>
                <span style={{
                  background: m.sender_id === activeDoctorId ? '#e2e8f0' : 'var(--primary)', 
                  color: m.sender_id === activeDoctorId ? '#0f172a' : 'white',
                  padding: '8px 12px',
                  borderRadius: 16,
                  display: 'inline-block',
                  maxWidth: '80%'
                }}>
                  {m.content}
                </span>
              </div>
            ))}
          </div>
          <form onSubmit={sendMessage} style={{display: 'flex', gap: 8}}>
            <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Type a message..." disabled={!activeDoctorId} style={{flex: 1, padding: 8}} />
            <button type="submit" className="btn-primary" style={{width: 'auto'}}>Send</button>
          </form>
        </section>
      </div>
    </div>
  );
}
