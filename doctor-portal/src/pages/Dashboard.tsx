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

interface VitalReading {
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
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [liveVitals, setLiveVitals] = useState<Record<number, any>>({});
  const [historicalReadings, setHistoricalReadings] = useState<VitalReading[]>([]);
  
  type WsStatus = 'connecting' | 'connected' | 'disconnected';
  const [wsStatus, setWsStatus] = useState<WsStatus>('disconnected');
  
  const navigate = useNavigate();

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<any>(null);

  const tokenParts = token ? token.split('.') : [];
  const currentUser = tokenParts.length === 3 ? JSON.parse(atob(tokenParts[1])) : null;
  const isAdmin = currentUser?.sub?.includes('admin') || currentUser?.role === 'admin'; // Wait, need to see the exact structure. Let's just assume role is in the token.

  const [activePatientId, setActivePatientId] = useState<number | null>(null);

  const fetchQueue = useCallback(async () => {
    try {
      const res = await axios.get('/api/triage/', { headers });
      setRequests(res.data);
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 401) handleLogout();
    }
  }, [token]);

  const fetchMessages = useCallback(async () => {
    if (!activePatientId) return;
    try {
      const res = await axios.get(`/api/messages/${activePatientId}`, { headers });
      setMessages(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [token, activePatientId]);

  const fetchReadings = useCallback(async () => {
    if (!activePatientId) return;
    try {
      const res = await axios.get(`/api/readings/${activePatientId}`, { headers });
      setHistoricalReadings(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [token, activePatientId]);

  const [uploadVisitId, setUploadVisitId] = useState('');
  const [uploadType, setUploadType] = useState('prescription');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDesc, setUploadDesc] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [doctorVisits, setDoctorVisits] = useState<any[]>([]);

  const fetchDoctorVisits = useCallback(async () => {
    try {
      const res = await axios.get('/api/visits/doctor', { headers });
      setDoctorVisits(res.data);
      if (res.data.length > 0) {
        setUploadVisitId(res.data[0].id.toString());
        if (!activePatientId) setActivePatientId(res.data[0].patient_id);
      }
    } catch (error) {
      console.error(error);
    }
  }, [token, activePatientId]);

  const [, setAccessRequests] = useState<any[]>([]);
  const [accessGrants, setAccessGrants] = useState<any[]>([]);
  
  // Request Form State
  const [reqPatientId, setReqPatientId] = useState('');
  const [reqHospitalId, setReqHospitalId] = useState('');
  const [reqReason, setReqReason] = useState('');
  const [availableDocs, setAvailableDocs] = useState<any[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<number[]>([]);
  const [fetchingDocs, setFetchingDocs] = useState(false);
  
  const fetchAccessData = useCallback(async () => {
    try {
      const [reqs, grants] = await Promise.all([
        axios.get('/api/access-requests/doctor', { headers }),
        axios.get('/api/access-grants/doctor', { headers })
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
        axios.get('/api/audit/doctor', { headers })
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
    
    fetchQueue();
    fetchMessages();
    fetchReadings();
    fetchDoctorVisits();
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
        fetchQueue();
        fetchMessages();
      };

      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'message') {
          setMessages(prev => [...prev, data.data]);
        } else if (data.type === 'triage_update') {
          fetchQueue();
        } else if (data.type === 'reading') {
          // Update live vitals
          setLiveVitals(prev => ({
            ...prev,
            [data.data.patient_id]: data.data
          }));
          // Fetch historical readings silently to keep list updated
          fetchReadings();
        } else if (['access_request_created', 'access_request_approved', 'access_request_rejected', 'access_revoked', 'notification_created'].includes(data.type)) {
          fetchAccessData();
          fetchPhase4Data();
        }
      };

      ws.current.onclose = () => {
        setWsStatus('disconnected');
        ws.current = null;
        if (!reconnectTimeout.current) {
          reconnectTimeout.current = setTimeout(() => connectWebSocket(), 3000);
        }
      };

      ws.current.onerror = () => {
        ws.current?.close();
      };
    };

    connectWebSocket();

    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.close();
      }
    };
    };
  }, [token, fetchQueue, fetchDoctorVisits, fetchAccessData, fetchPhase4Data, navigate]);

  useEffect(() => {
    if (activePatientId) {
      fetchMessages();
      fetchReadings();
    }
  }, [activePatientId, fetchMessages, fetchReadings]);

  // Admin Dashboard State
  const [adminData, setAdminData] = useState<any>(null);
  const fetchAdminData = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const res = await axios.get('/api/admin/dashboard', { headers });
      setAdminData(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [token, isAdmin]);

  useEffect(() => {
    if (isAdmin) {
      fetchAdminData();
    }
  }, [isAdmin, fetchAdminData]);

  const updateStatus = async (id: number, newStatus: string) => {
    try {
      await axios.patch(`/api/triage/${id}/status`, { status: newStatus }, { headers });
    } catch (error) {
      alert('Failed to update status.');
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || !activePatientId) return;
    try {
      await axios.post('/api/messages', {
        receiver_id: activePatientId,
        content: chatInput
      }, { headers });
      setChatInput('');
    } catch (error) {
      console.error(error);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !uploadVisitId) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('visit_id', uploadVisitId);
    formData.append('document_type', uploadType);
    formData.append('title', uploadTitle);
    if (uploadDesc) formData.append('description', uploadDesc);
    formData.append('file', uploadFile);

    try {
      await axios.post('/api/documents', formData, {
        headers: { ...headers, 'Content-Type': 'multipart/form-data' }
      });
      alert('Document uploaded successfully!');
      setUploadTitle('');
      setUploadDesc('');
      setUploadFile(null);
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleFetchPatientDocs = async () => {
    if (!reqPatientId) return;
    setFetchingDocs(true);
    try {
      const res = await axios.get(`/api/documents/metadata/${reqPatientId}`, { headers });
      setAvailableDocs(res.data);
      setSelectedDocs([]);
    } catch (error) {
      alert('Failed to fetch patient documents metadata');
    } finally {
      setFetchingDocs(false);
    }
  };

  const handleRequestAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedDocs.length === 0 || !reqHospitalId) return;
    try {
      await axios.post('/api/access-requests', {
        patient_id: parseInt(reqPatientId),
        hospital_id: parseInt(reqHospitalId),
        document_ids: selectedDocs,
        reason: reqReason
      }, { headers });
      alert('Access request submitted');
      setReqReason('');
      setSelectedDocs([]);
      fetchAccessData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Request failed');
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
      alert('Failed to download document. Access may be expired or denied.');
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

  return (
    <div className="container">
      <header className="header">
        <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
          <h2>MedFlow Guardian | Doctor</h2>
          <span style={{
            fontSize: 12, padding: '4px 8px', borderRadius: 12, color: 'white',
            background: wsStatus === 'connected' ? 'var(--status-resolved)' : (wsStatus === 'connecting' ? 'var(--status-pending)' : 'var(--priority-critical)')
          }}>
            {wsStatus === 'connected' ? 'Live' : (wsStatus === 'connecting' ? 'Connecting...' : 'Offline')}
          </span>
        </div>
        <button onClick={handleLogout} className="btn-secondary">Logout</button>
      </header>

      {isAdmin ? (
        <main className="dashboard-grid">
          <div className="column">
            <section className="card">
              <h3>Hospital Administration (ID: {adminData?.hospital_id})</h3>
              <p style={{fontSize: 13, color: 'var(--text-muted)'}}>Manage hospital operations and monitor data compliance.</p>
              
              <div style={{marginTop: 16}}>
                <h4>Affiliated Doctors ({adminData?.doctors?.length || 0})</h4>
                <div style={{display: 'grid', gap: 8, marginTop: 8}}>
                  {adminData?.doctors?.map((d: any) => (
                    <div key={d.id} style={{padding: 8, border: '1px solid var(--border)', borderRadius: 6, background: '#f8fafc'}}>
                      <strong>Dr. {d.full_name}</strong>
                      <p style={{margin: '4px 0', fontSize: 12, color: 'var(--text-muted)'}}>{d.email}</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </div>
          <div className="column">
            <section className="card">
              <h4>Hospital Visits ({adminData?.visits?.length || 0})</h4>
              <div style={{maxHeight: 200, overflowY: 'auto', marginTop: 8}}>
                {adminData?.visits?.map((v: any) => (
                  <div key={v.id} style={{padding: '8px 0', borderBottom: '1px solid var(--border)'}}>
                    <div style={{display: 'flex', justifyContent: 'space-between'}}>
                      <span style={{fontSize: 13}}>Patient {v.patient_id} ↔ Doctor {v.doctor_id}</span>
                      <span style={{fontSize: 11, background: 'var(--primary)', color: 'white', padding: '2px 6px', borderRadius: 12}}>{v.status}</span>
                    </div>
                    <p style={{margin: '4px 0', fontSize: 12, color: 'var(--text-muted)'}}>{v.reason}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="card" style={{marginTop: 24}}>
              <h4>Origin Documents ({adminData?.documents?.length || 0})</h4>
              <div style={{maxHeight: 200, overflowY: 'auto', marginTop: 8}}>
                {adminData?.documents?.map((d: any) => (
                  <div key={d.id} style={{padding: '8px 0', borderBottom: '1px solid var(--border)'}}>
                    <strong style={{fontSize: 13}}>{d.title}</strong>
                    <p style={{margin: '4px 0', fontSize: 12, color: 'var(--text-muted)'}}>Type: {d.document_type} | By: Dr. {d.uploaded_by_doctor_id}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </main>
      ) : (
      <main className="dashboard-grid">
        <div className="column">
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
                        <p style={{marginTop:6}}>{req.ai_reasoning}</p>
                        {req.disclaimer && (
                          <p style={{fontSize:11,color:'#64748b',marginTop:4,fontStyle:'italic'}}>{req.disclaimer}</p>
                        )}
                      </div>
                    )}
                    
                    <div className="action-bar">
                      <span>Update Status:</span>
                      <button onClick={() => updateStatus(req.id, 'reviewed')} disabled={req.status === 'reviewed'} className="btn-secondary">Mark Reviewed</button>
                      <button onClick={() => updateStatus(req.id, 'resolved')} disabled={req.status === 'resolved'} className="btn-secondary">Mark Resolved</button>
                      <button onClick={() => updateStatus(req.id, 'pending')} disabled={req.status === 'pending'} className="btn-secondary">Re-open</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="card" style={{marginTop: 24}}>
            <h3>Upload Medical Document</h3>
            <form onSubmit={handleUpload} style={{display: 'flex', flexDirection: 'column', gap: 12}}>
              <div>
                <label>Target Visit:</label><br/>
                <select value={uploadVisitId} onChange={e => setUploadVisitId(e.target.value)} required style={{width: '100%', padding: 8}}>
                  {doctorVisits.map(v => (
                    <option key={v.id} value={v.id}>Visit #{v.id} (Hospital #{v.hospital_id})</option>
                  ))}
                </select>
              </div>
              <div>
                <label>Document Type:</label><br/>
                <select value={uploadType} onChange={e => setUploadType(e.target.value)} required style={{width: '100%', padding: 8}}>
                  <option value="prescription">Prescription</option>
                  <option value="medicine report">Medicine Report</option>
                  <option value="lab report">Lab Report</option>
                  <option value="scan report">Scan Report</option>
                  <option value="diagnosis report">Diagnosis Report</option>
                  <option value="discharge summary">Discharge Summary</option>
                  <option value="other medical document">Other</option>
                </select>
              </div>
              <div>
                <label>Title:</label><br/>
                <input type="text" value={uploadTitle} onChange={e => setUploadTitle(e.target.value)} required placeholder="e.g. Blood Test Results" style={{width: '100%', padding: 8}}/>
              </div>
              <div>
                <label>Description (optional):</label><br/>
                <textarea value={uploadDesc} onChange={e => setUploadDesc(e.target.value)} rows={2} style={{width: '100%', padding: 8}}/>
              </div>
              <div>
                <label>File:</label><br/>
                <input type="file" onChange={e => setUploadFile(e.target.files ? e.target.files[0] : null)} required accept=".pdf,.png,.jpg,.jpeg,.txt" />
              </div>
              <button type="submit" className="btn-primary" disabled={uploading || !uploadFile}>
                {uploading ? 'Uploading...' : 'Upload Document'}
              </button>
            </form>
          </section>

          <section className="card" style={{marginTop: 24}}>
            <h3>Request Document Access</h3>
            <div style={{display: 'flex', gap: 8, marginBottom: 12}}>
              <input type="number" placeholder="Patient ID" value={reqPatientId} onChange={e => setReqPatientId(e.target.value)} style={{flex: 1, padding: 8}} />
              <button onClick={handleFetchPatientDocs} disabled={fetchingDocs} className="btn-secondary">Get Docs</button>
            </div>
            
            {availableDocs.length > 0 && (
              <form onSubmit={handleRequestAccess} style={{display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12, borderTop: '1px solid var(--border)', paddingTop: 12}}>
                <div>
                  <label>Select Documents:</label>
                  <div style={{maxHeight: 150, overflowY: 'auto', border: '1px solid var(--border)', padding: 8, borderRadius: 4, marginTop: 4}}>
                    {availableDocs.map(doc => (
                      <label key={doc.id} style={{display: 'block', padding: '4px 0'}}>
                        <input type="checkbox" checked={selectedDocs.includes(doc.id)} onChange={e => {
                          if (e.target.checked) setSelectedDocs([...selectedDocs, doc.id]);
                          else setSelectedDocs(selectedDocs.filter(id => id !== doc.id));
                        }} /> {doc.title} ({doc.document_type})
                      </label>
                    ))}
                  </div>
                </div>
                <div>
                  <label>Requesting as Hospital ID:</label>
                  <input type="number" required value={reqHospitalId} onChange={e => setReqHospitalId(e.target.value)} style={{width: '100%', padding: 8, marginTop: 4}} />
                </div>
                <div>
                  <label>Reason:</label>
                  <input type="text" required value={reqReason} onChange={e => setReqReason(e.target.value)} placeholder="e.g. Follow-up consultation" style={{width: '100%', padding: 8, marginTop: 4}} />
                </div>
                <button type="submit" className="btn-primary" disabled={selectedDocs.length === 0}>Submit Request</button>
              </form>
            )}
          </section>

          <section className="card" style={{marginTop: 24}}>
            <h3>Active Access Grants</h3>
            {accessGrants.length === 0 ? (
              <p className="empty-state">No access grants.</p>
            ) : (
              <div className="grant-list">
                {accessGrants.map(grant => (
                  <div key={grant.id} style={{border: '1px solid var(--border)', padding: 12, borderRadius: 6, marginBottom: 12, opacity: grant.status !== 'active' ? 0.6 : 1}}>
                    <h4 style={{margin: '0 0 4px 0'}}>Patient ID: {grant.patient_id} <span className={`badge status-${grant.status}`}>{grant.status.toUpperCase()}</span></h4>
                    <p style={{fontSize: 12, margin: '4px 0'}}>Expires: {new Date(grant.expires_at).toLocaleString()}</p>
                    {grant.status === 'active' ? (
                      <div style={{marginTop: 8}}>
                        <strong>Accessible Documents:</strong>
                        <ul style={{margin: '4px 0 0 16px', padding: 0, fontSize: 13}}>
                          {grant.granted_documents.map((doc: any) => (
                            <li key={doc.id}>
                              {doc.title} 
                              <button onClick={() => handleDownload(doc.id, doc.original_filename)} style={{background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', marginLeft: 8, textDecoration: 'underline'}}>Download</button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <p style={{color: 'var(--priority-high)', fontSize: 13, marginTop: 8}}>Access denied or expired.</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>

        </div>

        <div className="column">
          <section className="card monitor">
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
              <h3>Patient Vitals</h3>
              <select 
                className="input-field" 
                style={{width: '200px', margin: 0, padding: '4px', fontSize: 13}}
                value={activePatientId || ''} 
                onChange={(e) => setActivePatientId(Number(e.target.value))}
              >
                <option value="" disabled>Select Patient</option>
                {Array.from(new Map(doctorVisits.map(v => [v.patient_id, v])).values()).map(v => (
                  <option key={v.patient_id} value={v.patient_id}>{v.patient.full_name} (ID: {v.patient_id})</option>
                ))}
              </select>
            </div>
            
            <div style={{marginBottom: 16}}>
              <h4 style={{margin: '0 0 8px 0'}}>Live Monitor</h4>
              {Object.keys(liveVitals).length === 0 ? (
                <p className="empty-state">No active monitors.</p>
              ) : (
                <div>
                  {Object.values(liveVitals).map((vital: any) => (
                    <div key={vital.patient_id} style={{border: '1px solid var(--border)', padding: 12, borderRadius: 6, marginBottom: 12, background: '#f8fafc'}}>
                      <h4 style={{margin: '0 0 8px 0'}}>{vital.patient_name} {vital.is_simulated && <span style={{fontSize: 10, color: 'var(--priority-high)'}}>[SIMULATED]</span>}</h4>
                      <p style={{margin: '4px 0'}}><strong>Heart Rate:</strong> <span style={{fontSize: 18, fontWeight: 'bold'}}>{vital.heart_rate}</span> bpm</p>
                      <p style={{margin: '4px 0'}}><strong>O2 Level:</strong> <span style={{fontSize: 18, fontWeight: 'bold'}}>{vital.oxygen_level}</span>%</p>
                      <p style={{margin: '4px 0'}}><strong>Blood Pressure:</strong> <span style={{fontSize: 18, fontWeight: 'bold'}}>{vital.blood_pressure}</span></p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div style={{marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)'}}>
              <h4>Historical Readings</h4>
              {historicalReadings.length === 0 ? (
                <p className="empty-state">No past readings.</p>
              ) : (
                <div style={{maxHeight: 200, overflowY: 'auto', fontSize: 14}}>
                  {historicalReadings.map(r => (
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
            <h3>Chat with Patient</h3>
            <div style={{flex: 1, overflowY: 'auto', border: '1px solid var(--border)', borderRadius: 6, padding: 12, marginBottom: 12}}>
              {messages.map(m => (
                <div key={m.id} style={{textAlign: m.sender_id !== activePatientId ? 'right' : 'left', margin: '8px 0'}}>
                  <span style={{
                    background: m.sender_id !== activePatientId ? 'var(--primary)' : '#e2e8f0', 
                    color: m.sender_id !== activePatientId ? 'white' : '#0f172a',
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
              <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)} placeholder="Type a message..." />
              <button type="submit" className="btn-primary" style={{width: 'auto'}}>Send</button>
            </form>
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
            <p style={{fontSize: 12, color: 'var(--text-muted)', marginBottom: 12}}>Track your interactions and document accesses.</p>
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
                      Patient: {a.patient_id}
                      {a.document_id && ` | Doc: ${a.document_id}`}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>

        </div>
      </main>
    </div>
  );
};

export default Dashboard;
