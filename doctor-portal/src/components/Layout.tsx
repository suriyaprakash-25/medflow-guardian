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
}

export interface Message {
  id: number;
  sender_id: number;
  receiver_id: number;
  content: string;
  created_at: string;
}

export interface VitalReading {
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
  isAdmin: boolean;
  adminData: any;
  
  requests: TriageRequest[];
  fetchQueue: () => Promise<void>;
  updateStatus: (id: number, newStatus: string) => Promise<void>;
  
  activePatientId: number | null;
  setActivePatientId: (id: number | null) => void;
  doctorVisits: any[];
  
  messages: Message[];
  chatInput: string;
  setChatInput: (val: string) => void;
  sendMessage: (e: React.FormEvent) => Promise<void>;
  
  liveVitals: Record<number, any>;
  historicalReadings: VitalReading[];
  
  uploadVisitId: string;
  setUploadVisitId: (val: string) => void;
  uploadType: string;
  setUploadType: (val: string) => void;
  uploadTitle: string;
  setUploadTitle: (val: string) => void;
  uploadDesc: string;
  setUploadDesc: (val: string) => void;
  uploadFile: File | null;
  setUploadFile: (val: File | null) => void;
  uploading: boolean;
  handleUpload: (e: React.FormEvent) => Promise<void>;
  
  reqPatientId: string;
  setReqPatientId: (val: string) => void;
  reqHospitalId: string;
  setReqHospitalId: (val: string) => void;
  reqReason: string;
  setReqReason: (val: string) => void;
  availableDocs: any[];
  selectedDocs: number[];
  setSelectedDocs: (val: number[]) => void;
  fetchingDocs: boolean;
  handleFetchPatientDocs: () => Promise<void>;
  handleRequestAccess: (e: React.FormEvent) => Promise<void>;
  handleDownload: (docId: number, filename: string) => Promise<void>;
  
  accessRequests: any[];
  accessGrants: any[];
  
  notifications: any[];
  auditLogs: any[];
  handleMarkRead: (id: number) => Promise<void>;
  handleMarkAllRead: () => Promise<void>;
}

export function useDoctorContext() {
  return useOutletContext<OutletContextType>();
}

export default function Layout() {
  const [requests, setRequests] = useState<TriageRequest[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [liveVitals, setLiveVitals] = useState<Record<number, any>>({});
  const [historicalReadings, setHistoricalReadings] = useState<VitalReading[]>([]);
  
  type WsStatus = 'connecting' | 'connected' | 'disconnected';
  const [wsStatus, setWsStatus] = useState<WsStatus>('disconnected');
  
  const navigate = useNavigate();
  const location = useLocation();

  const token = localStorage.getItem('token');
  const headers = { Authorization: `Bearer ${token}` };
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<any>(null);

  const tokenParts = token ? token.split('.') : [];
  const currentUser = tokenParts.length === 3 ? JSON.parse(atob(tokenParts[1])) : null;
  const isAdmin = currentUser?.sub?.includes('admin') || currentUser?.role === 'admin';

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

  const [accessRequests, setAccessRequests] = useState<any[]>([]);
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

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const contextValue: OutletContextType = {
    isAdmin, adminData,
    requests, fetchQueue, updateStatus,
    activePatientId, setActivePatientId, doctorVisits,
    messages, chatInput, setChatInput, sendMessage,
    liveVitals, historicalReadings,
    uploadVisitId, setUploadVisitId, uploadType, setUploadType, uploadTitle, setUploadTitle, uploadDesc, setUploadDesc, uploadFile, setUploadFile, uploading, handleUpload,
    reqPatientId, setReqPatientId, reqHospitalId, setReqHospitalId, reqReason, setReqReason, availableDocs, selectedDocs, setSelectedDocs, fetchingDocs, handleFetchPatientDocs, handleRequestAccess, handleDownload,
    accessRequests, accessGrants,
    notifications, auditLogs, handleMarkRead, handleMarkAllRead
  };

  const navItems = isAdmin 
    ? [{ path: '/dashboard', label: 'Admin Dashboard' }] 
    : [
        { path: '/dashboard', label: 'Triage Queue' },
        { path: '/patients', label: 'My Patients' },
        { path: '/patient-details', label: 'Patient Details' },
        { path: '/upload-report', label: 'Upload Report' },
        { path: '/access-control', label: 'Access Control' },
        { path: '/profile', label: 'Profile' },
        { path: '/notifications', label: 'Notifications', badge: unreadCount },
      ];

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', background: '#f8fafc' }}>
      {/* Sidebar Layout */}
      <div style={{ width: '250px', background: '#0f172a', color: 'white', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px' }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#10b981' }}>MedFlow Guardian</h2>
          <p style={{ margin: '4px 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>{isAdmin ? 'Admin Portal' : 'Doctor Portal'}</p>
        </div>
        
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px', padding: '10px 0' }}>
          {navItems.map(item => (
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
                borderLeft: location.pathname === item.path ? '4px solid #10b981' : '4px solid transparent'
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
