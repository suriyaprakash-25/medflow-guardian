import React, { useState, useEffect, useRef, useCallback } from 'react';
import originalAxios from 'axios';
import { api as axios } from '../lib/api';
import { createAuthenticatedWebSocket } from '../lib/websocket';
import { useNavigate, Outlet, Link, useLocation, useOutletContext } from 'react-router-dom';
import { Activity, FileText, Lock, History, User, Bell, LogOut, Menu, Calendar } from 'lucide-react';
import { toast } from 'react-hot-toast';

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
  
  patientProfile: any;
  setPatientProfile: (val: any) => void;
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
  const [patientProfile, setPatientProfile] = useState<any>(null);

  const fetchPatientProfile = useCallback(async () => {
    try {
      const res = await axios.get('/api/users/patient-profile', { headers });
      setPatientProfile(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [token]);

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
      if (originalAxios.isAxiosError(error) && error.response?.status === 401) handleLogout();
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
    // Token is guaranteed by ProtectedRoute
    
    // Fetch authoritative identity from backend
    axios.get('/api/auth/me', { headers }).then((res) => {
      if (res.data.system_role !== 'patient' && res.data.role !== 'patient') {
        toast.error('Session mismatch: You are logged in with a non-patient account. Please log in again.');
        handleLogout();
      }
    }).catch(err => {
      console.error(err);
      if (err.response?.status === 401 || err.status === 401) handleLogout();
    });
    
    fetchPatientProfile();
    fetchPatientVisits();
    fetchRequests();
    fetchReadings();
    fetchDocuments();
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
        ws.current?.close(); // Triggers onclose
      };
    };

    connectWebSocket();

    return () => {
      disposed = true;
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
    // Vitals generation removed for production Phase 7.
    // If real hardware integration is added in Phase 8, it will be placed here.
  }, [vitalsOn, headers, fetchReadings]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    if (!selectedHospitalId) {
      toast.error('Please select a hospital.');
      setSubmitting(false);
      return;
    }
    try {
      await axios.post('/api/triage/', { symptoms, hospital_id: parseInt(selectedHospitalId) }, { headers });
      toast.success('Symptoms submitted successfully!');
      setSymptoms('');
      setSelectedHospitalId('');
      await fetchRequests(); // refresh immediately to show AI result
    } catch (error) {
      toast.error('Failed to submit symptoms.');
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
    } catch (error: any) {
      console.error(error);
      toast.error(error.message || 'Failed to send message');
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
      toast.error('Failed to download document');
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
      toast.success('Access request approved');
      fetchAccessData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Approval failed');
    }
  };

  const handleRejectAccess = async (reqId: number) => {
    try {
      await axios.post(`/api/access-requests/${reqId}/reject`, {
        rejection_reason: 'Rejected by patient'
      }, { headers });
      toast.success('Access request rejected');
      fetchAccessData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Rejection failed');
    }
  };

  const handleRevokeGrant = async (grantId: number) => {
    try {
      await axios.post(`/api/access-grants/${grantId}/revoke`, {}, { headers });
      toast.success('Access revoked successfully');
      fetchAccessData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Revocation failed');
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
    notifications, auditLogs, handleMarkRead, handleMarkAllRead,
    patientProfile, setPatientProfile
  };

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden">
      {/* Sidebar Layout */}
      <div className="w-64 bg-slate-900 text-white flex flex-col hidden md:flex shrink-0">
        <div className="p-6">
          <div className="flex items-center gap-2 text-primary">
            <Activity className="h-6 w-6" />
            <h2 className="m-0 text-lg font-bold">MedFlow</h2>
          </div>
          <p className="m-0 mt-1 text-xs text-slate-400">Patient Portal</p>
        </div>
        
        <div className="flex-1 overflow-y-auto py-4">
          <div className="px-4 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">My Health</div>
          <nav className="flex flex-col gap-1 px-2 mb-6">
            {[
              { path: '/dashboard', label: 'Overview', icon: Activity },
              { path: '/appointments', label: 'Appointments', icon: Calendar },
            ].map(item => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link 
                  key={item.path} 
                  to={item.path} 
                  className={`flex items-center justify-between px-3 py-2 rounded-md transition-all duration-200 ${
                    isActive ? 'bg-primary/10 text-primary font-semibold' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${isActive ? 'text-primary' : 'text-slate-400'}`} />
                    <span className="text-sm">{item.label}</span>
                  </div>
                </Link>
              )
            })}
          </nav>

          <div className="px-4 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Medical Records</div>
          <nav className="flex flex-col gap-1 px-2 mb-6">
            {[
              { path: '/clinical-history', label: 'Clinical History', icon: Activity },
              { path: '/documents', label: 'Documents', icon: FileText },
              { path: '/access-requests', label: 'Access Requests', badge: pendingRequestsCount, icon: Lock },
              { path: '/access-history', label: 'Access History', icon: History },
            ].map(item => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link 
                  key={item.path} 
                  to={item.path} 
                  className={`flex items-center justify-between px-3 py-2 rounded-md transition-all duration-200 ${
                    isActive ? 'bg-primary/10 text-primary font-semibold' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${isActive ? 'text-primary' : 'text-slate-400'}`} />
                    <span className="text-sm">{item.label}</span>
                  </div>
                  {!!item.badge && (
                    <span className="bg-amber-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </Link>
              )
            })}
          </nav>

          <div className="px-4 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Communication</div>
          <nav className="flex flex-col gap-1 px-2 mb-6">
            {[
              { path: '/notifications', label: 'Notifications', badge: unreadCount, icon: Bell },
            ].map(item => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link 
                  key={item.path} 
                  to={item.path} 
                  className={`flex items-center justify-between px-3 py-2 rounded-md transition-all duration-200 ${
                    isActive ? 'bg-primary/10 text-primary font-semibold' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${isActive ? 'text-primary' : 'text-slate-400'}`} />
                    <span className="text-sm">{item.label}</span>
                  </div>
                  {!!item.badge && (
                    <span className="bg-primary text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                      {item.badge}
                    </span>
                  )}
                </Link>
              )
            })}
          </nav>

          <div className="px-4 mb-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Account</div>
          <nav className="flex flex-col gap-1 px-2">
            {[
              { path: '/profile', label: 'Profile Settings', icon: User },
            ].map(item => {
              const isActive = location.pathname === item.path;
              const Icon = item.icon;
              return (
                <Link 
                  key={item.path} 
                  to={item.path} 
                  className={`flex items-center justify-between px-3 py-2 rounded-md transition-all duration-200 ${
                    isActive ? 'bg-primary/10 text-primary font-semibold' : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`h-4 w-4 ${isActive ? 'text-primary' : 'text-slate-400'}`} />
                    <span className="text-sm">{item.label}</span>
                  </div>
                </Link>
              )
            })}
          </nav>
        </div>

        <div className="p-4 border-t border-slate-800">
          <div className="flex items-center gap-2 mb-4 px-2">
            <div className={`w-2.5 h-2.5 rounded-full ${wsStatus === 'connected' ? 'bg-emerald-500' : (wsStatus === 'connecting' ? 'bg-amber-500' : 'bg-red-500')}`}></div>
            <span className="text-xs text-slate-400 font-medium">
              {wsStatus === 'connected' ? 'System Live' : (wsStatus === 'connecting' ? 'Connecting...' : 'Offline')}
            </span>
          </div>
          <button 
            onClick={handleLogout} 
            className="flex w-full items-center justify-center gap-2 bg-transparent border border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white px-4 py-2 rounded-md transition-colors text-sm font-medium"
          >
            <LogOut className="h-4 w-4" />
            Logout
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="bg-white border-b border-border px-6 py-4 flex items-center justify-between shrink-0 z-10 sticky top-0 shadow-sm">
          <div className="flex items-center gap-4">
            <button className="md:hidden p-2 text-slate-500 hover:bg-slate-100 rounded-md transition-colors">
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <h1 className="m-0 text-xl font-semibold text-slate-900 tracking-tight">
                {location.pathname === '/dashboard' ? 'Overview' : location.pathname.replace('/', '').replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </h1>
              {location.pathname === '/dashboard' && (
                <p className="text-xs text-slate-500 mt-0.5">Welcome back to MedFlow Guardian</p>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <button 
              onClick={() => navigate('/notifications')} 
              className="relative p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors"
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-primary rounded-full ring-2 ring-white"></span>
              )}
            </button>
            <div className="h-8 w-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-sm border border-primary/20">
              P
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-6xl">
            <Outlet context={contextValue} />
          </div>
        </main>
      </div>
    </div>
  );
}