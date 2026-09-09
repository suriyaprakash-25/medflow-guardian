import { useDoctorContext } from '../components/Layout';
import { useNavigate } from 'react-router-dom';

export default function Patients() {
  const { doctorVisits, setActivePatientId } = useDoctorContext();
  const navigate = useNavigate();

  const handleSelectPatient = (patientId: number) => {
    setActivePatientId(patientId);
    navigate('/patient-details');
  };

  return (
    <section className="card">
      <h3>My Active Patients</h3>
      {doctorVisits.length === 0 ? (
        <p className="empty-state">No patient visits recorded.</p>
      ) : (
        <div style={{display: 'grid', gap: 16, marginTop: 16}}>
          {doctorVisits.map(v => (
            <div key={v.id} style={{padding: 16, border: '1px solid var(--border)', borderRadius: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <div>
                <h4 style={{margin: '0 0 4px 0'}}>Patient ID: {v.patient_id}</h4>
                <p style={{margin: '4px 0', fontSize: 13, color: 'var(--text-muted)'}}>Hospital: {v.hospital?.name}</p>
                <p style={{margin: '4px 0', fontSize: 14}}>Reason: {v.reason}</p>
              </div>
              <div>
                <span style={{fontSize: 12, background: 'var(--primary)', color: 'white', padding: '4px 8px', borderRadius: 12, marginRight: 16}}>{v.status}</span>
                <button className="btn-secondary" onClick={() => handleSelectPatient(v.patient_id)}>View Details</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
