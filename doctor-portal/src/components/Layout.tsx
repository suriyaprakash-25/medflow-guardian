import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import originalAxios from 'axios';
import { api as axios } from '../lib/api';
import { createAuthenticatedWebSocket } from '../lib/websocket';
import { useNavigate, Outlet, Link, useLocation } from 'react-router-dom';
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

export interface DoctorMembership {
  role: string;
  hospital_id?: number;
}

export interface DoctorUser {
  id: number;
  email?: string;
  full_name?: string;
  role?: string;
  system_role?: string;
  memberships?: DoctorMembership[];
}

export interface DoctorVisit {
  id: number;
  patient_id: number;
  doctor_id?: number;
  hospital_id: number;
  status: string;
  reason?: string | null;
  hospital?: {
    id?: number;
    name?: string;
  };
}

export interface DocumentMetadata {
  id: number;
  patient_id?: number;
  hospital_id: number;
  title: string;
  document_type: string;
  original_filename: string;
}

export interface AccessRequestItem {
  id: number;
  patient_id: number;
  status: string;
  reason: string;
}

export interface AccessGrantItem {
  id: number;
  patient_id: number;
  status: string;
  expires_at: string;
  granted_documents: DocumentMetadata[];
}

export interface DoctorNotification {
  id: number;
  is_read: boolean;
  message: string;
  created_at: string;
}

export interface DoctorAuditLog {
  id: number;
  operation: string;
  timestamp: string;
  target_user_id?: number | null;
  document_id?: number | null;
}

export interface AdminDashboardData {
  total_users: number;
  total_hospitals: number;
  total_triage_requests: number;
  active_grants: number;
}

interface ClientError {
  status?: number;
  message?: string;
  response?: {
    data?: {
      detail?: string;
    };
  };
}

function asClientError(error: unknown): ClientError {
  if (typeof error === 'object' && error !== null) {
    return error as ClientError;
  }
  return {};
}

export interface OutletContextType {
  isAdmin: boolean;
  adminData: AdminDashboardData | null;
  currentUser: DoctorUser | null;
  setCurrentUser: React.Dispatch<React.SetStateAction<DoctorUser | null>>;

  requests: TriageRequest[];
  fetchQueue: () => Promise<void>;
  updateStatus: (id: number, newStatus: string) => Promise<void>;

  activePatientId: number | null;
  setActivePatientId: (id: number | null) => void;
  doctorVisits: DoctorVisit[];

  messages: Message[];
  chatInput: string;
  setChatInput: (val: string) => void;
  sendMessage: (e: React.FormEvent) => Promise<void>;

  liveVitals: Record<number, VitalReading>;
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
  availableDocs: DocumentMetadata[];
  selectedDocs: number[];
  setSelectedDocs: (val: number[]) => void;
  fetchingDocs: boolean;
  handleFetchPatientDocs: () => Promise<void>;
  handleRequestAccess: (e: React.FormEvent) => Promise<void>;
  handleDownload: (docId: number, filename: string) => Promise<void>;

  accessRequests: AccessRequestItem[];
  accessGrants: AccessGrantItem[];

  notifications: DoctorNotification[];
  auditLogs: DoctorAuditLog[];
  handleMarkRead: (id: number) => Promise<void>;
  handleMarkAllRead: () => Promise<void>;
}

export default function Layout() {
  const [requests, setRequests] = useState<TriageRequest[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [liveVitals, setLiveVitals] = useState<Record<number, VitalReading>>({});
  const [historicalReadings, setHistoricalReadings] = useState<VitalReading[]>([]);

  type WsStatus = 'connecting' | 'connected' | 'disconnected';
  const [wsStatus, setWsStatus] = useState<WsStatus>('disconnected');

  const navigate = useNavigate();
  const location = useLocation();

  const token = localStorage.getItem('token');
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [currentUser, setCurrentUser] = useState<DoctorUser | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [activePatientId, setActivePatientId] = useState<number | null>(null);

  const handleLogout = useCallback(async () => {
    try {
      await axios.post('/api/auth/logout');
    } catch (error) {
      console.error('Failed to revoke server session during logout', error);
    } finally {
      localStorage.removeItem('token');
      navigate('/login');
    }
  }, [navigate]);

  const fetchQueue = useCallback(async () => {
    try {
      const res = await axios.get('/api/triage/', { headers });
      setRequests(res.data);
    } catch (error) {
      if (originalAxios.isAxiosError(error) && error.response?.status === 401) {
        void handleLogout();
      }
    }
  }, [handleLogout, headers]);

  const fetchMessages = useCallback(async () => {
    if (!activePatientId) return;
    try {
      const res = await axios.get(`/api/messages/${activePatientId}`, { headers });
      setMessages(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [activePatientId, headers]);

  const fetchReadings = useCallback(async () => {
    if (!activePatientId) return;
    try {
      const res = await axios.get(`/api/readings/${activePatientId}`, { headers });
      setHistoricalReadings(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [activePatientId, headers]);

  const [uploadVisitId, setUploadVisitId] = useState('');
  const [uploadType, setUploadType] = useState('prescription');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDesc, setUploadDesc] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [doctorVisits, setDoctorVisits] = useState<DoctorVisit[]>([]);

  const fetchDoctorVisits = useCallback(async () => {
    try {
      const res = await axios.get('/api/visits/doctor', { headers });
      const visits = res.data as DoctorVisit[];
      setDoctorVisits(visits);
      if (visits.length > 0) {
        setUploadVisitId(visits[0].id.toString());
        if (!activePatientId) setActivePatientId(visits[0].patient_id);
      }
    } catch (error) {
      console.error(error);
    }
  }, [activePatientId, headers]);

  const [accessRequests, setAccessRequests] = useState<AccessRequestItem[]>([]);
  const [accessGrants, setAccessGrants] = useState<AccessGrantItem[]>([]);

  const [reqPatientId, setReqPatientId] = useState('');
  const [reqHospitalId, setReqHospitalId] = useState('');
  const [reqReason, setReqReason] = useState('');
  const [availableDocs, setAvailableDocs] = useState<DocumentMetadata[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<number[]>([]);
  const [fetchingDocs, setFetchingDocs] = useState(false);

  const fetchAccessData = useCallback(async () => {
    try {
      const [reqs, grants] = await Promise.all([
        axios.get('/api/access-requests/doctor', { headers }),
        axios.get('/api/access-grants/doctor', { headers }),
      ]);
      setAccessRequests(reqs.data);
      setAccessGrants(grants.data);
    } catch (error) {
      console.error(error);
    }
  }, [headers]);

  const [notifications, setNotifications] = useState<DoctorNotification[]>([]);
  const [auditLogs, setAuditLogs] = useState<DoctorAuditLog[]>([]);

  const fetchPhase4Data = useCallback(async () => {
    try {
      const [notifs, audits] = await Promise.all([
        axios.get('/api/notifications', { headers }),
        axios.get('/api/audit/doctor', { headers }),
      ]);
      setNotifications(notifs.data);
      setAuditLogs(audits.data);
    } catch (error) {
      console.error(error);
    }
  }, [headers]);

  useEffect(() => {
    axios.get('/api/auth/me', { headers }).then((res) => {
      if (
        res.data.system_role !== 'doctor'
        && res.data.role !== 'doctor'
        && res.data.system_role !== 'admin'
        && res.data.role !== 'admin'
      ) {
        toast.error('Session mismatch: You are logged in with a non-doctor account. Please log in again.');
        void handleLogout();
        return;
      }
      const user = res.data as DoctorUser;
      setCurrentUser(user);
      const adminMembership = user.memberships?.find((membership) => membership.role === 'admin');
      setIsAdmin(Boolean(adminMembership));
    }).catch((error) => {
      console.error(error);
      const clientError = asClientError(error);
      if (clientError.response?.data || clientError.status === 401) {
        if (clientError.status === 401) void handleLogout();
      }
    });

    queueMicrotask(() => {
      void fetchQueue();
      void fetchMessages();
      void fetchReadings();
      void fetchDoctorVisits();
      void fetchAccessData();
      void fetchPhase4Data();
    });

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
        if (!disposed) void handleLogout();
      }
    };

    const connectWebSocket = () => {
      if (
        disposed
        || ws.current?.readyState === WebSocket.OPEN
        || ws.current?.readyState === WebSocket.CONNECTING
      ) return;

      const currentToken = localStorage.getItem('token');
      if (!currentToken) {
        void handleLogout();
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
        void fetchQueue();
        void fetchMessages();
      };

      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'message') {
          setMessages((previous) => [...previous, data.data]);
        } else if (data.type === 'triage_update') {
          void fetchQueue();
        } else if (data.type === 'reading') {
          const reading = data.data as VitalReading;
          setLiveVitals((previous) => ({
            ...previous,
            [reading.patient_id]: reading,
          }));
          void fetchReadings();
        } else if (
          [
            'access_request_created',
            'access_request_approved',
            'access_request_rejected',
            'access_revoked',
            'notification_created',
          ].includes(data.type)
        ) {
          void fetchAccessData();
          void fetchPhase4Data();
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
  }, [
    fetchAccessData,
    fetchDoctorVisits,
    fetchMessages,
    fetchPhase4Data,
    fetchQueue,
    fetchReadings,
    handleLogout,
    headers,
  ]);

  useEffect(() => {
    if (!activePatientId) return;
    queueMicrotask(() => {
      void fetchMessages();
      void fetchReadings();
    });
  }, [activePatientId, fetchMessages, fetchReadings]);

  const [adminData, setAdminData] = useState<AdminDashboardData | null>(null);
  const fetchAdminData = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const res = await axios.get('/api/admin/dashboard', { headers });
      setAdminData(res.data);
    } catch (error) {
      console.error(error);
    }
  }, [headers, isAdmin]);

  useEffect(() => {
    if (!isAdmin) return;
    queueMicrotask(() => {
      void fetchAdminData();
    });
  }, [isAdmin, fetchAdminData]);

  const updateStatus = async (id: number, newStatus: string) => {
    try {
      await axios.patch(`/api/triage/${id}/status`, { status: newStatus }, { headers });
      toast.success(`Triage request marked as ${newStatus}`);
    } catch {
      toast.error('Failed to update status.');
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || !activePatientId) return;
    try {
      await axios.post('/api/messages', {
        receiver_id: activePatientId,
        content: chatInput,
      }, { headers });
      setChatInput('');
    } catch (error) {
      console.error(error);
      const clientError = asClientError(error);
      toast.error(clientError.message || 'Failed to send message');
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
        headers: { ...headers, 'Content-Type': 'multipart/form-data' },
      });
      toast.success('Document uploaded successfully!');
      setUploadTitle('');
      setUploadDesc('');
      setUploadFile(null);
    } catch (error) {
      const clientError = asClientError(error);
      toast.error(clientError.response?.data?.detail || clientError.message || 'Upload failed');
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
        params: { hospital_id: parseInt(reqHospitalId, 10) },
      });
      setAvailableDocs(res.data);
      setSelectedDocs([]);
    } catch {
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
        patient_id: parseInt(reqPatientId, 10),
        hospital_id: parseInt(reqHospitalId, 10),
        document_ids: selectedDocs,
        reason: reqReason,
      }, { headers });
      toast.success('Access request submitted');
      setReqReason('');
      setSelectedDocs([]);
      void fetchAccessData();
    } catch (error) {
      const clientError = asClientError(error);
      toast.error(clientError.response?.data?.detail || clientError.message || 'Request failed');
    }
  };

  const handleDownload = async (docId: number, filename: string) => {
    try {
      const res = await axios.get(`/api/documents/${docId}/download`, {
        headers,
        responseType: 'blob',
        params: { purpose: 'TREATMENT' },
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      const clientError = asClientError(error);
      if (clientError.status === 403) {
        toast.error('Access Denied: The patient has revoked consent or the policy has changed.', { duration: 6000 });
      } else {
        toast.error(`Failed to download document. ${clientError.message || ''}`.trim());
      }
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await axios.post(`/api/notifications/${id}/read`, {}, { headers });
      void fetchPhase4Data();
    } catch (error) {
      console.error(error);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await axios.post('/api/notifications/read-all', {}, { headers });
      void fetchPhase4Data();
      toast.success('All notifications marked as read');
    } catch (error) {
      console.error(error);
    }
  };

  const unreadCount = notifications.filter((notification) => !notification.is_read).length;

  const contextValue: OutletContextType = {
    isAdmin,
    adminData,
    currentUser,
    setCurrentUser,
    requests,
    fetchQueue,
    updateStatus,
    activePatientId,
    setActivePatientId,
    doctorVisits,
    messages,
    chatInput,
    setChatInput,
    sendMessage,
    liveVitals,
    historicalReadings,
    uploadVisitId,
    setUploadVisitId,
    uploadType,
    setUploadType,
    uploadTitle,
    setUploadTitle,
    uploadDesc,
    setUploadDesc,
    uploadFile,
    setUploadFile,
    uploading,
    handleUpload,
    reqPatientId,
    setReqPatientId,
    reqHospitalId,
    setReqHospitalId,
    reqReason,
    setReqReason,
    availableDocs,
    selectedDocs,
    setSelectedDocs,
    fetchingDocs,
    handleFetchPatientDocs,
    handleRequestAccess,
    handleDownload,
    accessRequests,
    accessGrants,
    notifications,
    auditLogs,
    handleMarkRead,
    handleMarkAllRead,
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
          {navItems.map((item) => {
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
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-800/50 bg-slate-900/50">
          <div className="flex items-center gap-2 mb-4 px-2">
            <div className="relative flex h-2.5 w-2.5">
              {wsStatus === 'connected' && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              )}
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${wsStatus === 'connected' ? 'bg-emerald-500' : (wsStatus === 'connecting' ? 'bg-amber-500' : 'bg-rose-500')}`} />
            </div>
            <span className="text-xs text-slate-400 font-medium tracking-wide">
              {wsStatus === 'connected' ? 'System Live & Synced' : (wsStatus === 'connecting' ? 'Connecting...' : 'Offline - Reconnecting')}
            </span>
          </div>
          <button
            onClick={() => void handleLogout()}
            className="flex w-full items-center justify-center gap-2 bg-transparent border border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-white px-4 py-2.5 rounded-lg transition-colors text-sm font-medium"
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0 shadow-sm z-10 sticky top-0">
          <div className="flex items-center gap-4">
            <button className="md:hidden p-2 text-slate-500 hover:bg-slate-100 rounded-md transition-colors">
              <Menu className="h-5 w-5" />
            </button>
            <div>
              <h1 className="m-0 text-xl font-bold text-slate-900 tracking-tight">
                {location.pathname.replace('/', '').replace('-', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="hidden md:flex items-center gap-3">
              <div className="text-right">
                <p className="text-sm font-semibold text-slate-900 leading-none">
                  Dr. {currentUser?.full_name || currentUser?.email || 'User'}
                </p>
                <p className="text-xs text-slate-500 mt-1 font-medium">General Hospital</p>
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
