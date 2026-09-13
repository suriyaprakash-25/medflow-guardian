import type React from 'react';
import { useOutletContext } from 'react-router-dom';

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

  patientVisits: any[];
  documents: any[];
  docFilterHospital: string;
  setDocFilterHospital: (value: string) => void;
  docFilterType: string;
  setDocFilterType: (value: string) => void;
  handleDownload: (documentId: number, filename: string) => Promise<void>;

  accessRequests: any[];
  accessGrants: any[];
  durations: Record<number, number>;
  setDurations: (value: Record<number, number>) => void;
  handleApproveAccess: (request: any) => Promise<void>;
  handleRejectAccess: (requestId: number) => Promise<void>;
  handleRevokeGrant: (grantId: number) => Promise<void>;

  notifications: any[];
  auditLogs: any[];
  handleMarkRead: (id: number) => Promise<void>;
  handleMarkAllRead: () => Promise<void>;

  patientProfile: any;
  setPatientProfile: (value: any) => void;
}

export function usePatientContext() {
  return useOutletContext<PatientOutletContext>();
}
