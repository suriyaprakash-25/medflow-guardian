import type React from 'react';
import { useOutletContext } from 'react-router-dom';
import type {
  AccessGrantContract,
  AccessRequestContract,
  AuditLogContract,
  AuthUserContract,
  DocumentContract,
  MessageContract,
  NotificationContract,
  TriageRequestContract,
  VisitContract,
  VitalReadingContract,
} from '@shared/api/contracts';

export type TriageRequest = TriageRequestContract;
export type Message = MessageContract;
export type Reading = VitalReadingContract;

export interface PatientOutletContext {
  requests: TriageRequest[];
  fetchRequests: () => Promise<void>;
  symptoms: string;
  setSymptoms: (value: string) => void;
  selectedHospitalId: string;
  setSelectedHospitalId: (value: string) => void;
  submitting: boolean;
  handleSubmit: (event: React.FormEvent) => Promise<void>;

  messages: Message[];
  chatInput: string;
  setChatInput: (value: string) => void;
  sendMessage: (event: React.FormEvent) => Promise<void>;

  readings: Reading[];
  vitalsOn: boolean;
  setVitalsOn: (value: boolean) => void;

  activeDoctorId: number | null;
  setActiveDoctorId: (value: number | null) => void;

  patientVisits: VisitContract[];
  documents: DocumentContract[];
  docFilterHospital: string;
  setDocFilterHospital: (value: string) => void;
  docFilterType: string;
  setDocFilterType: (value: string) => void;
  handleDownload: (documentId: number, filename: string) => Promise<void>;

  accessRequests: AccessRequestContract[];
  accessGrants: AccessGrantContract[];
  durations: Record<number, number>;
  setDurations: (value: Record<number, number>) => void;
  handleApproveAccess: (request: AccessRequestContract) => Promise<void>;
  handleRejectAccess: (requestId: number) => Promise<void>;
  handleRevokeGrant: (grantId: number) => Promise<void>;

  notifications: NotificationContract[];
  auditLogs: AuditLogContract[];
  handleMarkRead: (id: number) => Promise<void>;
  handleMarkAllRead: () => Promise<void>;

  patientProfile: AuthUserContract | null;
  setPatientProfile: (value: AuthUserContract | null) => void;
}

export function usePatientContext() {
  return useOutletContext<PatientOutletContext>();
}
