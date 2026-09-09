import { useDoctorContext } from '../components/Layout';

export default function PatientDetails() {
  const { 
    activePatientId, doctorVisits, setActivePatientId, 
    liveVitals, historicalReadings, 
    messages, chatInput, setChatInput, sendMessage 
  } = useDoctorContext();

  if (!activePatientId) {
    return (
      <section className="card">
        <h3>Patient Details</h3>
        <p className="empty-state">No patient selected. Please select a patient from the 'My Patients' tab.</p>
        <select 
          className="input-field" 
          value={activePatientId || ''} 
          onChange={(e) => setActivePatientId(Number(e.target.value))}
          style={{marginTop: 16}}
        >
          <option value="">Select a Patient</option>
          {doctorVisits.map(v => (
            <option key={v.patient_id} value={v.patient_id}>Patient ID: {v.patient_id}</option>
          ))}
        </select>
      </section>
    );
  }

  const currentVitals = liveVitals[activePatientId];

  return (
    <div className="dashboard-grid">
      <div className="column">
        <section className="card monitor">
          <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
            <h3>Live Vitals</h3>
            <select 
              className="input-field" 
              style={{width: '200px', margin: 0}}
              value={activePatientId || ''} 
              onChange={(e) => setActivePatientId(Number(e.target.value))}
            >
              {doctorVisits.map(v => (
                <option key={v.patient_id} value={v.patient_id}>Patient {v.patient_id}</option>
              ))}
            </select>
          </div>
          
          <div style={{marginTop: 16, display: 'flex', gap: 16}}>
            <div style={{flex: 1, background: '#f8fafc', padding: 16, borderRadius: 8, textAlign: 'center'}}>
              <p style={{margin: '0 0 8px 0', color: 'var(--text-muted)'}}>Heart Rate</p>
              <h2 style={{margin: 0, color: currentVitals ? '#ef4444' : '#94a3b8'}}>{currentVitals ? currentVitals.heart_rate : '--'} bpm</h2>
            </div>
            <div style={{flex: 1, background: '#f8fafc', padding: 16, borderRadius: 8, textAlign: 'center'}}>
              <p style={{margin: '0 0 8px 0', color: 'var(--text-muted)'}}>SpO2</p>
              <h2 style={{margin: 0, color: currentVitals ? '#3b82f6' : '#94a3b8'}}>{currentVitals ? currentVitals.oxygen_level : '--'} %</h2>
            </div>
            <div style={{flex: 1, background: '#f8fafc', padding: 16, borderRadius: 8, textAlign: 'center'}}>
              <p style={{margin: '0 0 8px 0', color: 'var(--text-muted)'}}>BP</p>
              <h2 style={{margin: 0, color: currentVitals ? '#10b981' : '#94a3b8'}}>{currentVitals ? `${currentVitals.blood_pressure_sys}/${currentVitals.blood_pressure_dia}` : '--/--'}</h2>
            </div>
          </div>

          <div style={{marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border)'}}>
            <h4>Historical Readings</h4>
            {historicalReadings.length === 0 ? (
              <p className="empty-state">No historical readings available.</p>
            ) : (
              <div style={{maxHeight: 250, overflowY: 'auto', fontSize: 14}}>
                {historicalReadings.map(r => (
                  <div key={r.id} style={{padding: '12px 0', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between'}}>
                    <span style={{color: 'var(--text-muted)'}}>{new Date(r.created_at).toLocaleString()}</span>
                    <span>HR: {r.heart_rate} | O2: {r.oxygen_level}% | BP: {r.blood_pressure_sys}/{r.blood_pressure_dia}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      <div className="column">
        <section className="card chat" style={{height: 500, display: 'flex', flexDirection: 'column'}}>
          <h3>Chat with Patient</h3>
          <div style={{flex: 1, overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 8, padding: 16, marginBottom: 16, marginTop: 16}}>
            {messages.length === 0 ? (
              <p className="empty-state">No messages yet. Send a message to start.</p>
            ) : (
              messages.map(m => (
                <div key={m.id} style={{textAlign: m.sender_id === activePatientId ? 'left' : 'right', margin: '12px 0'}}>
                  <span style={{
                    background: m.sender_id === activePatientId ? '#e2e8f0' : 'var(--primary)', 
                    color: m.sender_id === activePatientId ? '#0f172a' : 'white',
                    padding: '10px 16px',
                    borderRadius: 16,
                    display: 'inline-block',
                    maxWidth: '80%'
                  }}>
                    {m.content}
                  </span>
                </div>
              ))
            )}
          </div>
          <form onSubmit={sendMessage} style={{display: 'flex', gap: 12}}>
            <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Type a message..." disabled={!activePatientId} style={{flex: 1, padding: 12, borderRadius: 8, border: '1px solid var(--border)'}} />
            <button type="submit" className="btn-primary" style={{width: 'auto', padding: '0 24px'}}>Send</button>
          </form>
        </section>
      </div>
    </div>
  );
}
