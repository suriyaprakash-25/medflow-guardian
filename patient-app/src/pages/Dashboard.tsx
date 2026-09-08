import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

interface TriageRequest {
  id: number;
  symptoms: string;
  status: string;
  priority: string | null;
  ai_reasoning: string | null;
  disclaimer: string | null;
  created_at: string;
}

interface Message {
  id: number;
  sender_id: number;
  receiver_id: number;
  content: string;
  created_at: string;
}

interface Reading {
  id: number;
  patient_id: number;
  heart_rate: number;
  oxygen_level: number;
  blood_pressure_sys: number;
  blood_pressure_dia: number;
  is_simulated: boolean;
  created_at: string;
}

export default function Dashboard() {
  const [requests, setRequests] = useState<TriageRequest[]>([]);
  const [symptoms, setSymptoms] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [readings, setReadings] = useState<Reading[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [vitalsOn, setVitalsOn] = useState(false);
  
  type WsStatus = 'connecting' | 'connected' | 'disconnected';
  const [wsStatus, setWsStatus] = useState<WsStatus>('disconnected');
  
  const navigate = useNavigate();

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<any>(null);

  const [activeDoctorId, setActiveDoctorId] = useState<number | null>(null);
  const [patientVisits, setPatientVisits] = useState<any[]>([]);

  const fetchPatientVisits = useCallback(async () => {
    try {
      const res = await axios.get('/api/visits/patient', { headers });
      setPatientVisits(res.data);
      if (res.data.length > 0 && !activeDoctorId) {
        setActiveDoctorId(res.data[0].doctor_id);
      }
    } catch (error) {
      console.error(error);
    }
  }, [token, activeDoctorId]);

  const fetchRequests = useCallback(async () => {
    try {
      const res = await axios.get('/api/triage/patient', { headers });
      setRequests(res.data);
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 401) handleLogout();
    }
  }, [token]);

  const fetchMessages = useCallback(async () => {
    if (!activeDoctorId) return;
    try {
      const res = await axios.get(`/api/messages/${activeDoctorId}`, { headers });
      setMessages(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [token, activeDoctorId]);

  const fetchReadings = useCallback(async () => {
    try {
      const res = await axios.get('/api/readings/patient', { headers });
      setReadings(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [token]);

  const [documents, setDocuments] = useState<any[]>([]);
  const [docFilterHospital, setDocFilterHospital] = useState<string>('');
  const [docFilterType, setDocFilterType] = useState<string>('');
  
  const fetchDocuments = useCallback(async () => {
    try {
      const res = await axios.get('/api/documents/patient', { headers });
      setDocuments(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [token]);

  const [accessRequests, setAccessRequests] = useState<any[]>([]);
  const [accessGrants, setAccessGrants] = useState<any[]>([]);

  const fetchAccessData = useCallback(async () => {
    try {
      const [reqs, grants] = await Promise.all([
        axios.get('/api/access-requests/patient', { headers }),
        axios.get('/api/access-grants/patient', { headers })
      ]);
      setAccessRequests(reqs.data);
      setAccessGrants(grants.data);
    } catch (error) {
      console.error(error);
    }
  }, [token]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  
  const fetchPhase4Data = useCallback(async () => {
    try {
      const [notifs, audits] = await Promise.all([
        axios.get('/api/notifications', { headers }),
        axios.get('/api/audit/patient', { headers })
      ]);
      setNotifications(notifs.data);
      setAuditLogs(audits.data);
    } catch (error) {
      console.error(error);
    }
  }, [token]);

  useEffect(() => {
    if (!token) {
      navigate('/login');
      return;
    }
    
    fetchPatientVisits();
    fetchRequests();
    fetchReadings();
    fetchDocuments();
    fetchAccessData();
    fetchPhase4Data();

    const connectWebSocket = () => {
      if (ws.current?.readyState === WebSocket.OPEN || ws.current?.readyState === WebSocket.CONNECTING) return;
      
      setWsStatus('connecting');
      const wsUrl = `ws://localhost:8080/ws?token=${token}`;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        setWsStatus('connected');
        if (reconnectTimeout.current) {
          clearTimeout(reconnectTimeout.current);
          reconnectTimeout.current = null;
        }
        // Recover state
        fetchRequests();
        fetchMessages();
      };

      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'message') {
          setMessages(prev => [...prev, data.data]);
        } else if (data.type === 'triage_update') {
          fetchRequests();
        } else if (['access_request_created', 'access_request_approved', 'access_request_rejected', 'access_revoked', 'document_uploaded', 'notification_created'].includes(data.type)) {
          fetchAccessData();
          fetchPhase4Data();
          fetchDocuments();
        }
      };

      ws.current.onclose = () => {
        setWsStatus('disconnected');
        ws.current = null;
        // Exponential backoff or simple delay reconnect
        if (!reconnectTimeout.current) {
          reconnectTimeout.current = setTimeout(() => connectWebSocket(), 3000);
        }
      };
      
      ws.current.onerror = () => {
        ws.current?.close(); // Triggers onclose
      };
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws.current) {
        ws.current.onclose = null; // Prevent reconnect loop on unmount
        ws.current.close();
      }
    };
  }, [token, fetchRequests, fetchMessages, fetchReadings, navigate]);

  useEffect(() => {
    if (activeDoctorId) {
      fetchMessages();
    }
  }, [activeDoctorId, fetchMessages]);

  useEffect(() => {
    let interval: any;
    if (vitalsOn) {
      interval = setInterval(() => {
        axios.post('/api/readings', {
          heart_rate: Math.floor(Math.random() * (100 - 60 + 1) + 60),
          oxygen_level: Math.floor(Math.random() * (100 - 95 + 1) + 95),
          blood_pressure_sys: Math.floor(Math.random() * (130 - 110 + 1) + 110),
          blood_pressure_dia: Math.floor(Math.random() * (85 - 70 + 1) + 70),
          is_simulated: true
        }, { headers }).then(() => {
          fetchReadings();
        }).catch(console.error);
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [vitalsOn, headers, fetchReadings]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post('/api/triage/', { symptoms }, { headers });
      setSymptoms('');
      await fetchRequests(); // refresh immediately to show AI result
    } catch (error) {
      alert('Failed to submit symptoms.');
    } finally {
      setSubmitting(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    try {
      const res = await axios.post('/api/messages', {
        receiver_id: DOCTOR_ID,
        content: chatInput
      }, { headers });
      setMessages(prev => [...prev, res.data]);
      setChatInput('');
    } catch (error) {
      console.error(error);
    }
  };

  const handleDownload = async (docId: number, filename: string) => {
    try {
      const res = await axios.get(`/api/documents/${docId}/download`, { 
        headers, 
        responseType: 'blob' 
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (error) {
      alert('Failed to download document');
    }
  };

  const [durations, setDurations] = useState<Record<number, number>>({});

  const handleApproveAccess = async (req: any) => {
    const duration = durations[req.id] || 1;
    try {
      await axios.post(`/api/access-requests/${req.id}/approve`, {
        duration_hours: duration,
        document_ids: req.requested_documents.map((d: any) => d.id)
      }, { headers });
      alert('Access request approved');
      fetchAccessData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Approval failed');
    }
  };

  const handleRejectAccess = async (reqId: number) => {
    try {
      await axios.post(`/api/access-requests/${reqId}/reject`, {
        rejection_reason: 'Rejected by patient'
      }, { headers });
      fetchAccessData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Rejection failed');
    }
  };

  const handleRevokeGrant = async (grantId: number) => {
    try {
      await axios.post(`/api/access-grants/${grantId}/revoke`, {}, { headers });
      fetchAccessData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Revocation failed');
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await axios.post(`/api/notifications/${id}/read`, {}, { headers });
      fetchPhase4Data();
    } catch (error) {
      console.error(error);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await axios.post(`/api/notifications/read-all`, {}, { headers });
      fetchPhase4Data();
    } catch (error) {
      console.error(error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <div className="container">
      <header className="header">
        <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
          <h2>MedFlow Guardian | Patient</h2>
          <span style={{
            fontSize: 12, padding: '4px 8px', borderRadius: 12, color: 'white',
            background: wsStatus === 'connected' ? 'var(--status-resolved)' : (wsStatus === 'connecting' ? 'var(--status-pending)' : 'var(--priority-critical)')
          }}>
            {wsStatus === 'connected' ? 'Live' : (wsStatus === 'connecting' ? 'Connecting...' : 'Offline')}
          </span>
        </div>
        <button onClick={handleLogout} className="btn-secondary">Logout</button>
      </header>

      <div className="dashboard-grid">
        <div className="column">
          <section className="card">
            <h3>My Profile & Visit History</h3>
            <p style={{fontSize: 13, color: 'var(--text-muted)'}}>Manage your identity and track your interactions across different hospitals.</p>
            {patientVisits.length === 0 ? (
              <p className="empty-state">No visits recorded.</p>
            ) : (
              <div style={{marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8}}>
                {patientVisits.map(v => (
                  <div key={v.id} style={{padding: 8, background: '#f8fafc', border: '1px solid var(--border)', borderRadius: 6}}>
                    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                      <strong>{v.hospital?.name}</strong>
                      <span style={{fontSize: 11, background: 'var(--primary)', color: 'white', padding: '2px 6px', borderRadius: 12}}>{v.status}</span>
                    </div>
                    <p style={{margin: '4px 0', fontSize: 13}}>Dr. {v.doctor?.full_name}</p>
                    <p style={{margin: '4px 0', fontSize: 12, color: 'var(--text-muted)'}}>Reason: {v.reason}</p>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card new-request" style={{marginTop: 24}}>
            <h3>Submit New Symptoms</h3>
            <form onSubmit={handleSubmit}>
              <textarea 
                value={symptoms} 
                onChange={e => setSymptoms(e.target.value)} 
                placeholder="Describe your symptoms..."
                required
                rows={4}
              />
              <br/><br/>
              <button type="submit" className="btn-primary" disabled={submitting}>
                {submitting ? 'Submitting...' : 'Request Triage'}
              </button>
            </form>
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
                        <p style={{marginTop:6}}>{req.ai_reasoning}</p>
                        {req.disclaimer && (
                          <p style={{fontSize:11,color:'#64748b',marginTop:4,fontStyle:'italic'}}>{req.disclaimer}</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card documents" style={{marginTop: 24}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <h3>My Medical Documents</h3>
              <div style={{display: 'flex', gap: 8}}>
                <select className="input-field" style={{padding: '4px', fontSize: 12, margin: 0, width: 120}} value={docFilterHospital} onChange={e => setDocFilterHospital(e.target.value)}>
                  <option value="">All Hospitals</option>
                  {Array.from(new Set(documents.map(d => d.hospital?.name))).filter(Boolean).map(hName => (
                    <option key={hName as string} value={hName as string}>{hName as string}</option>
                  ))}
                </select>
                <select className="input-field" style={{padding: '4px', fontSize: 12, margin: 0, width: 120}} value={docFilterType} onChange={e => setDocFilterType(e.target.value)}>
                  <option value="">All Types</option>
                  {Array.from(new Set(documents.map(d => d.document_type))).filter(Boolean).map(tName => (
                    <option key={tName as string} value={tName as string}>{tName as string}</option>
                  ))}
                </select>
              </div>
            </div>
            
            {documents.filter(d => (!docFilterHospital || d.hospital?.name === docFilterHospital) && (!docFilterType || d.document_type === docFilterType)).length === 0 ? (
              <p className="empty-state">No documents match filters.</p>
            ) : (
              <div className="document-list" style={{marginTop: 12}}>
                {documents.filter(d => (!docFilterHospital || d.hospital?.name === docFilterHospital) && (!docFilterType || d.document_type === docFilterType)).map(doc => (
                  <div key={doc.id} style={{border: '1px solid var(--border)', padding: 12, borderRadius: 6, marginBottom: 12}}>
                    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                      <h4 style={{margin: '0 0 4px 0'}}>{doc.title}</h4>
                      <span className="badge" style={{background: '#e2e8f0', color: '#1e293b'}}>{doc.document_type.toUpperCase()}</span>
                    </div>
                    <p style={{fontSize: 12, color: 'var(--text-muted)', margin: '4px 0'}}>
                      Uploaded: {new Date(doc.created_at).toLocaleDateString()} | Size: {(doc.file_size / 1024).toFixed(1)} KB
                    </p>
                    {doc.description && <p style={{fontSize: 14, margin: '8px 0'}}>{doc.description}</p>}
                    <button 
                      onClick={() => handleDownload(doc.id, doc.original_filename)} 
                      className="btn-secondary" 
                      style={{marginTop: 8, padding: '4px 12px', fontSize: 12}}
                    >
                      Download / Preview
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card" style={{marginTop: 24}}>
            <h3>Document Access Requests</h3>
            {accessRequests.filter(r => r.status === 'pending').length === 0 ? (
              <p className="empty-state">No pending access requests.</p>
            ) : (
              <div className="request-list">
                {accessRequests.filter(r => r.status === 'pending').map(req => (
                  <div key={req.id} style={{border: '1px solid var(--status-pending)', padding: 12, borderRadius: 6, marginBottom: 12, background: '#fdfcbc'}}>
                    <h4 style={{margin: '0 0 8px 0'}}>Request from Doctor ID: {req.requesting_doctor_id} (Hospital {req.requesting_hospital_id})</h4>
                    <p style={{margin: '4px 0', fontSize: 13}}><strong>Reason:</strong> {req.reason}</p>
                    <div style={{margin: '8px 0'}}>
                      <strong>Requested Documents:</strong>
                      <ul style={{margin: '4px 0 0 16px', padding: 0, fontSize: 13}}>
                        {req.requested_documents.map((doc: any) => (
                          <li key={doc.id}>{doc.title} ({doc.document_type})</li>
                        ))}
                      </ul>
                    </div>
                    
                    <div style={{marginTop: 12, display: 'flex', gap: 12, alignItems: 'center'}}>
                      <select 
                        value={durations[req.id] || 1} 
                        onChange={e => setDurations({...durations, [req.id]: parseInt(e.target.value)})}
                        style={{padding: '4px 8px'}}
                      >
                        <option value={1}>1 hour</option>
                        <option value={4}>4 hours</option>
                        <option value={24}>1 day</option>
                        <option value={96}>4 days</option>
                      </select>
                      <button onClick={() => handleApproveAccess(req)} className="btn-primary" style={{padding: '4px 12px', fontSize: 12}}>Approve</button>
                      <button onClick={() => handleRejectAccess(req.id)} className="btn-secondary" style={{padding: '4px 12px', fontSize: 12}}>Reject</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card" style={{marginTop: 24}}>
            <h3>Active Access Grants</h3>
            {accessGrants.filter(g => g.status === 'active').length === 0 ? (
              <p className="empty-state">No active grants.</p>
            ) : (
              <div className="grant-list">
                {accessGrants.filter(g => g.status === 'active').map(grant => (
                  <div key={grant.id} style={{border: '1px solid var(--border)', padding: 12, borderRadius: 6, marginBottom: 12}}>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <h4 style={{margin: '0 0 4px 0'}}>Doctor ID: {grant.doctor_id}</h4>
                      <button onClick={() => handleRevokeGrant(grant.id)} className="btn-secondary" style={{padding: '2px 8px', fontSize: 11, color: 'var(--priority-critical)', borderColor: 'var(--priority-critical)'}}>Revoke Access</button>
                    </div>
                    <p style={{fontSize: 12, margin: '4px 0'}}>Expires: {new Date(grant.expires_at).toLocaleString()}</p>
                    <div style={{marginTop: 8}}>
                      <strong style={{fontSize: 13}}>Accessible Documents:</strong>
                      <ul style={{margin: '4px 0 0 16px', padding: 0, fontSize: 12}}>
                        {grant.granted_documents.map((doc: any) => (
                          <li key={doc.id}>{doc.title}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card" style={{marginTop: 24}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <h3>Notifications</h3>
              {notifications.some(n => !n.is_read) && (
                <button onClick={handleMarkAllRead} className="btn-secondary" style={{fontSize: 12, padding: '2px 8px'}}>Mark all read</button>
              )}
            </div>
            {notifications.length === 0 ? (
              <p className="empty-state">No notifications.</p>
            ) : (
              <div style={{maxHeight: 250, overflowY: 'auto', marginTop: 12}}>
                {notifications.map(n => (
                  <div key={n.id} style={{padding: 8, borderBottom: '1px solid var(--border)', background: n.is_read ? 'transparent' : '#f0f9ff', cursor: 'pointer'}} onClick={() => !n.is_read && handleMarkRead(n.id)}>
                    <p style={{margin: '0 0 4px 0', fontSize: 13, fontWeight: n.is_read ? 'normal' : 'bold'}}>{n.message}</p>
                    <span style={{fontSize: 11, color: 'var(--text-muted)'}}>{new Date(n.created_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card" style={{marginTop: 24}}>
            <h3>Security Audit Logs</h3>
            <p style={{fontSize: 12, color: 'var(--text-muted)', marginBottom: 12}}>Track all accesses and activities on your medical records.</p>
            {auditLogs.length === 0 ? (
              <p className="empty-state">No audit logs.</p>
            ) : (
              <div style={{maxHeight: 250, overflowY: 'auto'}}>
                {auditLogs.map(a => (
                  <div key={a.id} style={{padding: '8px 0', borderBottom: '1px solid var(--border)'}}>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <strong style={{fontSize: 12, textTransform: 'uppercase'}}>{a.action.replace('_', ' ')}</strong>
                      <span style={{fontSize: 11, color: 'var(--text-muted)'}}>{new Date(a.created_at).toLocaleString()}</span>
                    </div>
                    <p style={{fontSize: 12, margin: '4px 0', color: '#475569'}}>
                      Actor: {a.actor_role} ({a.actor_id})
                      {a.document_id && ` | Doc: ${a.document_id}`}
                    </p>
                  </div>
                ))}
              </div>
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
              <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Type a message..." disabled={!activeDoctorId} />
              <button type="submit" className="btn-primary" style={{width: 'auto'}}>Send</button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}

