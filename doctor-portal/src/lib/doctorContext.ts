import type React from 'react';
import { useOutletContext } from 'react-router-dom';

export interface TriageRequest {
  id: number;
  patient_id: number;
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
  hospital?: { id?: number; name?: string };
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

export interface DoctorOutletContext {
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
  setChatInput: (value: string) => void;
  sendMessage: (event: React.FormEvent) => Promise<void>;
  liveVitals: Record<number, VitalReading>;
  historicalReadings: VitalReading[];
  uploadVisitId: string;
  setUploadVisitId: (value: string) => void;
  uploadType: string;
  setUploadType: (value: string) => void;
  uploadTitle: string;
  setUploadTitle: (value: string) => void;
  uploadDesc: string;
  setUploadDesc: (value: string) => void;
  uploadFile: File | null;
  setUploadFile: (value: File | null) => void;
  uploading: boolean;
  handleUpload: (event: React.FormEvent) => Promise<void>;
  reqPatientId: string;
  setReqPatientId: (value: string) => void;
  reqHospitalId: string;
  setReqHospitalId: (value: string) => void;
  reqReason: string;
  setReqReason: (value: string) => void;
  availableDocs: DocumentMetadata[];
  selectedDocs: number[];
  setSelectedDocs: (value: number[]) => void;
  fetchingDocs: boolean;
  handleFetchPatientDocs: () => Promise<void>;
  handleRequestAccess: (event: React.FormEvent) => Promise<void>;
  handleDownload: (documentId: number, filename: string) => Promise<void>;
  accessRequests: AccessRequestItem[];
  accessGrants: AccessGrantItem[];
  notifications: DoctorNotification[];
  auditLogs: DoctorAuditLog[];
  handleMarkRead: (id: number) => Promise<void>;
  handleMarkAllRead: () => Promise<void>;
}

export function useDoctorContext() {
  return useOutletContext<DoctorOutletContext>();
}
