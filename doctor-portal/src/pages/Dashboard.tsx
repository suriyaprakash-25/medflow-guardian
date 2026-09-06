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
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  // Hardcode patient id for demo
  const PATIENT_ID = 1;

  const fetchQueue = useCallback(async () => {
    try {
      const res = await axios.get('/api/triage/', { headers });
      setRequests(res.data);
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 401) handleLogout();
    }
  }, [token]);

  const fetchMessages = useCallback(async () => {
    try {
      const res = await axios.get(`/api/messages/${PATIENT_ID}`, { headers });
      setMessages(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [token]);

  const fetchReadings = useCallback(async () => {
    try {
      const res = await axios.get(`/api/readings/${PATIENT_ID}`, { headers });
      setHistoricalReadings(res.data);
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
  }, [token, fetchQueue, fetchMessages, fetchReadings, navigate]);

  const updateStatus = async (id: number, newStatus: string) => {
    try {
      await axios.patch(`/api/triage/${id}/status`, { status: newStatus }, { headers });
    } catch (error) {
      alert('Failed to update status.');
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    try {
      const res = await axios.post('/api/messages', {
        receiver_id: PATIENT_ID,
        content: chatInput
      }, { headers });
      setMessages(prev => [...prev, res.data]);
      setChatInput('');
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

      <div className="dashboard-grid">
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
        </div>

        <div className="column">
          <section className="card monitor">
            <h3>Patient Vitals (ID: {PATIENT_ID})</h3>
            
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
                <div key={m.id} style={{textAlign: m.sender_id !== PATIENT_ID ? 'right' : 'left', margin: '8px 0'}}>
                  <span style={{
                    background: m.sender_id !== PATIENT_ID ? 'var(--primary)' : '#e2e8f0', 
                    color: m.sender_id !== PATIENT_ID ? 'white' : '#0f172a',
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
        </div>
      </div>
    </div>
  );
}
