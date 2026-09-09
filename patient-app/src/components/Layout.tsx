import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import { useNavigate, Outlet, Link, useLocation, useOutletContext } from 'react-router-dom';

export interface TriageRequest {
  id: number;
  symptoms: string;
  status: string;
  priority: string | null;
  ai_reasoning: string | null;
  disclaimer: string | null;
  created_at: string;
  hospital_id?: number;
}

export interface Message {
  id: number;
  sender_id: number;
  receiver_id: number;
  content: string;
  created_at: string;
}

export interface Reading {
  id: number;
  patient_id: number;
  heart_rate: number;
  oxygen_level: number;
  blood_pressure_sys: number;
  blood_pressure_dia: number;
  is_simulated: boolean;
  created_at: string;
}

export interface OutletContextType {
  requests: TriageRequest[];
  fetchRequests: () => Promise<void>;
  symptoms: string;
  setSymptoms: (val: string) => void;
  selectedHospitalId: string;
  setSelectedHospitalId: (val: string) => void;
  submitting: boolean;
  handleSubmit: (e: React.FormEvent) => Promise<void>;
  
  messages: Message[];
  chatInput: string;
  setChatInput: (val: string) => void;
  sendMessage: (e: React.FormEvent) => Promise<void>;
  
  readings: Reading[];
  vitalsOn: boolean;
  setVitalsOn: (val: boolean) => void;
  
  activeDoctorId: number | null;
  setActiveDoctorId: (val: number | null) => void;
  
  patientVisits: any[];
  documents: any[];
  docFilterHospital: string;
  setDocFilterHospital: (val: string) => void;
  docFilterType: string;
  setDocFilterType: (val: string) => void;
  handleDownload: (docId: number, filename: string) => Promise<void>;
  
  accessRequests: any[];
  accessGrants: any[];
  durations: Record<number, number>;
  setDurations: (val: Record<number, number>) => void;
  handleApproveAccess: (req: any) => Promise<void>;
  handleRejectAccess: (reqId: number) => Promise<void>;
  handleRevokeGrant: (grantId: number) => Promise<void>;
  
  notifications: any[];
  auditLogs: any[];
  handleMarkRead: (id: number) => Promise<void>;
  handleMarkAllRead: () => Promise<void>;
}

export function usePatientContext() {
  return useOutletContext<OutletContextType>();
}

export default function Layout() {
  const [requests, setRequests] = useState<TriageRequest[]>([]);
  const [symptoms, setSymptoms] = useState('');
  const [selectedHospitalId, setSelectedHospitalId] = useState<string>('');
  const [submitting, setSubmitting] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [readings, setReadings] = useState<Reading[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [vitalsOn, setVitalsOn] = useState(false);
  
  type WsStatus = 'connecting' | 'connected' | 'disconnected';
  const [wsStatus, setWsStatus] = useState<WsStatus>('disconnected');
  
  const navigate = useNavigate();
  const location = useLocation();

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
    if (!selectedHospitalId) {
      alert('Please select a hospital.');
      setSubmitting(false);
      return;
    }
    try {
      await axios.post('/api/triage/', { symptoms, hospital_id: parseInt(selectedHospitalId) }, { headers });
      setSymptoms('');
      setSelectedHospitalId('');
      await fetchRequests(); // refresh immediately to show AI result
    } catch (error) {
      alert('Failed to submit symptoms.');
    } finally {
      setSubmitting(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || !activeDoctorId) return;
    try {
      const res = await axios.post('/api/messages', {
        receiver_id: activeDoctorId,
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

  const unreadCount = notifications.filter(n => !n.is_read).length;
  const pendingRequestsCount = accessRequests.filter(r => r.status === 'pending').length;

  const contextValue: OutletContextType = {
    requests, fetchRequests, symptoms, setSymptoms, selectedHospitalId, setSelectedHospitalId, submitting, handleSubmit,
    messages, chatInput, setChatInput, sendMessage,
    readings, vitalsOn, setVitalsOn,
    activeDoctorId, setActiveDoctorId,
    patientVisits, documents, docFilterHospital, setDocFilterHospital, docFilterType, setDocFilterType, handleDownload,
    accessRequests, accessGrants, durations, setDurations, handleApproveAccess, handleRejectAccess, handleRevokeGrant,
    notifications, auditLogs, handleMarkRead, handleMarkAllRead
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', background: '#f8fafc' }}>
      {/* Sidebar Layout */}
      <div style={{ width: '250px', background: '#0f172a', color: 'white', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#38bdf8' }}>MedFlow Guardian</h2>
          <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>Patient Portal</p>
        </div>
        
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px', padding: '10px 0' }}>
          {[
            { path: '/dashboard', label: 'Dashboard' },
            { path: '/documents', label: 'Documents' },
            { path: '/access-requests', label: 'Access Requests', badge: pendingRequestsCount },
            { path: '/access-history', label: 'Access History' },
            { path: '/profile', label: 'Profile' },
            { path: '/notifications', label: 'Notifications', badge: unreadCount },
          ].map(item => (
            <Link 
              key={item.path} 
              to={item.path} 
              style={{
                padding: '12px 20px', 
                color: location.pathname === item.path ? 'white' : '#cbd5e1', 
                background: location.pathname === item.path ? '#1e293b' : 'transparent',
                textDecoration: 'none',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderLeft: location.pathname === item.path ? '4px solid #38bdf8' : '4px solid transparent'
              }}
            >
              {item.label}
              {!!item.badge && (
                <span style={{ background: '#ef4444', color: 'white', fontSize: '0.7rem', padding: '2px 6px', borderRadius: '12px' }}>
                  {item.badge}
                </span>
              )}
            </Link>
          ))}
        </nav>

        <div style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <div style={{
              width: '10px', height: '10px', borderRadius: '50%',
              background: wsStatus === 'connected' ? '#10b981' : (wsStatus === 'connecting' ? '#f59e0b' : '#ef4444')
            }}></div>
            <span style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
              {wsStatus === 'connected' ? 'Live' : (wsStatus === 'connecting' ? 'Connecting...' : 'Offline')}
            </span>
          </div>
          <button 
            onClick={handleLogout} 
            style={{ width: '100%', background: 'transparent', border: '1px solid #334155', color: '#e2e8f0', padding: '8px', borderRadius: '6px', cursor: 'pointer' }}
          >
            Logout
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <header style={{ background: 'white', padding: '16px 24px', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center' }}>
          <h1 style={{ margin: 0, fontSize: '1.25rem', color: '#0f172a' }}>
            {location.pathname.replace('/', '').replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
          </h1>
        </header>
        <main style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
          <Outlet context={contextValue} />
        </main>
      </div>
    </div>
  );
}
