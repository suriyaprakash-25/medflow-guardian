import type React from 'react';
import { useOutletContext } from 'react-router-dom';
import type {
  AccessGrantContract,
  AccessRequestContract,
  AdminDashboardContract,
  AuditLogContract,
  AuthUserContract,
  DocumentContract,
  MessageContract,
  NotificationContract,
  TriageRequestContract,
  VisitContract,
  VitalReadingContract,
} from '@shared/api/contracts';

export type TriageRequest = TriageRequestContract & { patient_id: number };
export type Message = MessageContract;
export type VitalReading = VitalReadingContract;
export type DoctorUser = AuthUserContract;
export type DoctorVisit = VisitContract;
export type DocumentMetadata = DocumentContract;
export type AccessRequestItem = AccessRequestContract;
export type AccessGrantItem = AccessGrantContract & { granted_documents: DocumentContract[] };
export type DoctorNotification = NotificationContract;
export type DoctorAuditLog = AuditLogContract;
export type AdminDashboardData = AdminDashboardContract;

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
