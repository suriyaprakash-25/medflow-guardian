import React, { useState, useEffect, useRef, useCallback } from 'react';
import originalAxios from 'axios';
import { api as axios } from '../lib/api';
import { createAuthenticatedWebSocket } from '../lib/websocket';
import { useNavigate, Outlet, Link, useLocation, useOutletContext } from 'react-router-dom';
import { Activity, Users, User, FileText, Lock, Bell, LogOut, Menu, Shield, Calendar } from 'lucide-react';
import { toast } from 'react-hot-toast';
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
  currentUser: any;
  setCurrentUser: (user: any) => void;
  
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

  const [currentUser, setCurrentUser] = useState<any>(null);
  const [isAdmin, setIsAdmin] = useState(false);

  const [activePatientId, setActivePatientId] = useState<number | null>(null);

  const fetchQueue = useCallback(async () => {
    try {
      const res = await axios.get('/api/triage/', { headers });
      setRequests(res.data);
    } catch (error) {
      if (originalAxios.isAxiosError(error) && error.response?.status === 401) handleLogout();
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
    // Token is guaranteed by ProtectedRoute
    
    // Fetch authoritative identity from backend
    axios.get('/api/auth/me', { headers }).then(res => {
      if (res.data.system_role !== 'doctor' && res.data.role !== 'doctor' && res.data.system_role !== 'admin' && res.data.role !== 'admin') {
        toast.error('Session mismatch: You are logged in with a non-doctor account. Please log in again.');
        handleLogout();
        return;
      }
      setCurrentUser(res.data);
      const adminMembership = res.data.memberships?.find((m: any) => m.role === 'admin');
      setIsAdmin(!!adminMembership);
    }).catch(err => {
      console.error(err);
      if (err.response?.status === 401 || err.status === 401) handleLogout();
    });
    
    fetchQueue();
    fetchMessages();
    fetchReadings();
    fetchDoctorVisits();
    fetchAccessData();
    fetchPhase4Data();

    let disposed = false;

    const reconnectAfterAuthFailure = async () => {
      try {
        const response = await axios.post('/api/auth/refresh');
        const refreshedToken = response.data?.access_token;
        if (typeof refreshedToken !== 'string' || !refreshedToken) {
          throw new Error('Refresh response did not include an access token');
        }
        localStorage.setItem('token', refreshedToken);
        if (!disposed) connectWebSocket();
      } catch (error) {
        console.error('Unable to refresh realtime authentication', error);
        if (!disposed) handleLogout();
      }
    };

    const connectWebSocket = () => {
      if (disposed || ws.current?.readyState === WebSocket.OPEN || ws.current?.readyState === WebSocket.CONNECTING) return;

      const currentToken = localStorage.getItem('token');
      if (!currentToken) {
        handleLogout();
        return;
      }
      
      setWsStatus('connecting');
      ws.current = createAuthenticatedWebSocket(currentToken);

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

      ws.current.onclose = (event) => {
        setWsStatus('disconnected');
        ws.current = null;
        if (disposed) return;
        if (event.code === 1008) {
          void reconnectAfterAuthFailure();
          return;
        }
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
      disposed = true;
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
      toast.success(`Triage request marked as ${newStatus}`);
    } catch (error) {
      toast.error('Failed to update status.');
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
    } catch (error: any) {
      console.error(error);
      toast.error(error.message || 'Failed to send message');
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post('/api/auth/logout');
    } catch (error) {
      console.error('Failed to revoke server session during logout', error);
    } finally {
      localStorage.removeItem('token');
      navigate('/login');
    }
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
      toast.success('Document uploaded successfully!');
      setUploadTitle('');
      setUploadDesc('');
      setUploadFile(null);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleFetchPatientDocs = async () => {
    if (!reqPatientId || !reqHospitalId) {
      toast.error('Enter both the patient ID and hospital ID before discovering documents.');
      return;
    }
    setFetchingDocs(true);
    try {
      const res = await axios.get(`/api/documents/metadata/${reqPatientId}`, {
        headers,
        params: { hospital_id: parseInt(reqHospitalId) }
      });
      setAvailableDocs(res.data);
      setSelectedDocs([]);
    } catch (error) {
      toast.error('Failed to fetch patient documents metadata');
    } finally {
      setFetchingDocs(false);
    }
  };

  const handleRequestAccess = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reqHospitalId) {
      toast.error('Please specify your Hospital ID.');
      return;
    }
    if (selectedDocs.length === 0) {
      toast.error('Please find and select at least one patient document.');
      return;
    }
    try {
      await axios.post('/api/access-requests', {
        patient_id: parseInt(reqPatientId),
        hospital_id: parseInt(reqHospitalId),
        document_ids: selectedDocs,
        reason: reqReason
      }, { headers });
      toast.success('Access request submitted');
      setReqReason('');
      setSelectedDocs([]);
      fetchAccessData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Request failed');
    }
  };

  const handleDownload = async (docId: number, filename: string) => {
    try {
      const res = await axios.get(`/api/documents/${docId}/download`, {
        headers,
        responseType: 'blob',
        params: { purpose: 'TREATMENT' }
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
    } catch (error: any) {
      if (error.status === 403) {
        toast.error('Access Denied: The patient has revoked consent or the policy has changed.', { duration: 6000 });
      } else {
        toast.error('Failed to download document. ' + (error.message || ''));
      }
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
      toast.success('All notifications marked as read');
    } catch (error) {
      console.error(error);
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  const contextValue: OutletContextType = {
    isAdmin, adminData, currentUser, setCurrentUser,
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
    ? [{ path: '/dashboard', label: 'Admin Dashboard', icon: Shield }] 
    : [
        { path: '/dashboard', label: 'Triage Queue', icon: Activity },
        { path: '/appointments', label: 'Appointments', icon: Calendar },
        { path: '/patients', label: 'My Patients', icon: Users },
        { path: '/patient-details', label: 'Patient Details', icon: User },
        { path: '/upload-report', label: 'Upload Report', icon: FileText },
        { path: '/access-control', label: 'Access Control', icon: Lock },
        { path: '/profile', label: 'Profile', icon: User },
        { path: '/notifications', label: 'Notifications', badge: unreadCount, icon: Bell },
      ];

  return (
    <div className="flex h-screen w-full bg-slate-50 overflow-hidden font-sans">
      {/* Sidebar Layout */}
      <div className="w-64 bg-slate-900 text-white flex flex-col hidden md:flex shrink-0 shadow-xl z-10">
        <div className="p-6">
          <div className="flex items-center gap-3 text-primary">
            <div className="bg-primary/20 p-2 rounded-lg">
              <Shield className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <h2 className="m-0 text-lg font-bold text-white tracking-tight">MedFlow</h2>
              <p className="m-0 text-[11px] text-slate-400 font-medium tracking-widest uppercase">
                {isAdmin ? 'Admin Portal' : 'Doctor Portal'}
              </p>
            </div>
          </div>
        </div>
        
        <nav className="flex-1 flex flex-col gap-1.5 px-3 py-4 overflow-y-auto">
          <div className="px-3 mb-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Clinical Workspace</p>
          </div>
          {navItems.map(item => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link 
                key={item.path} 
                to={item.path} 
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg transition-all duration-200 group ${
                  isActive 
                    ? 'bg-blue-600 text-white shadow-md' 
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-5 w-5 transition-colors ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-blue-400'}`} />
                  <span className="text-sm font-medium">{item.label}</span>
                </div>
                {!!item.badge && (
                  <span className="bg-rose-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm">
                    {item.badge}
                  </span>
                )}
              </Link>
            )
          })}
        </nav>

        <div className="p-4 border-t border-slate-800/50 bg-slate-900/50">
          <div className="flex items-center gap-2 mb-4 px-2">
            <div className="relative flex h-2.5 w-2.5">
              {wsStatus === 'connected' && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              )}
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${wsStatus === 'connected' ? 'bg-emerald-500' : (wsStatus === 'connecting' ? 'bg-amber-500' : 'bg-rose-500')}`}></span>
            </div>
            <span className="text-xs text-slate-400 font-medium tracking-wide">
              {wsStatus === 'connected' ? 'System Live & Synced' : (wsStatus === 'connecting' ? 'Connecting...' : 'Offline - Reconnecting')}
            </span>
          </div>
          <button 
            onClick={handleLogout} 
            className="flex w-full items-center justify-center gap-2 bg-transparent border border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white px-4 py-2.5 rounded-lg transition-colors text-sm font-medium"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0 shadow-sm z-10 sticky top-0">
          <div className="flex items-center gap-4">
            <button className="md:hidden p-2 text-slate-500 hover:bg-slate-100 rounded-md transition-colors">
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <h1 className="m-0 text-xl font-bold text-slate-900 tracking-tight">
                {location.pathname.replace('/', '').replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </h1>
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            <div className="hidden md:flex items-center gap-3">
              <div className="text-right">
                <p className="text-sm font-semibold text-slate-900 leading-none">
                  Dr. {currentUser?.full_name || currentUser?.email || 'User'}
                </p>
                <p className="text-xs text-slate-500 mt-1 font-medium">
                  General Hospital
                </p>
              </div>
              <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center border-2 border-white shadow-sm">
                <User className="h-5 w-5 text-blue-600" />
              </div>
            </div>
          </div>
        </header>
        
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 bg-slate-50 relative">
          <div className="mx-auto max-w-7xl animate-in fade-in duration-500">
            <Outlet context={contextValue} />
          </div>
        </main>
      </div>
    </div>
  );
}