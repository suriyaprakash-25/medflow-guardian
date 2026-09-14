// Shared MedFlow HTTP/WebSocket contract types consumed by all three portals.
//
// These are transport contracts only. They do not carry authorization authority:
// the backend remains the collocated PDP+PEP and resolves consent/enforcement
// state server-side.

export type SystemRole = 'patient' | 'doctor' | 'platform_admin' | 'admin' | string;

export interface HospitalSummary {
  id: number;
  name?: string;
}

export interface MembershipContract {
  role: string;
  hospital_id?: number;
  hospital?: HospitalSummary;
}

export interface AuthUserContract {
  id: number;
  email?: string;
  full_name?: string;
  role?: string;
  system_role?: SystemRole;
  memberships?: MembershipContract[];
}

export interface LoginResponseContract {
  access_token: string;
  token_type?: string;
  role?: string;
  mfa_required?: boolean;
}

export interface TriageRequestContract {
  id: number;
  patient_id?: number;
  hospital_id?: number;
  symptoms: string;
  status: string;
  priority: string | null;
  ai_reasoning: string | null;
  disclaimer: string | null;
  created_at: string;
}

export interface MessageContract {
  id: number;
  sender_id: number;
  receiver_id: number;
  content: string;
  created_at: string;
}

export interface VitalReadingContract {
  id: number;
  patient_id: number;
  heart_rate: number;
  oxygen_level: number;
  blood_pressure_sys: number;
  blood_pressure_dia: number;
  is_simulated: boolean;
  created_at: string;
}

export interface VisitContract {
  id: number;
  patient_id: number;
  doctor_id?: number | null;
  hospital_id: number;
  status: string;
  reason?: string | null;
  hospital?: HospitalSummary;
}

export interface DocumentContract {
  id: number;
  patient_id?: number;
  hospital_id: number;
  title: string;
  document_type: string;
  original_filename: string;
}

export interface AccessRequestContract {
  id: number;
  patient_id: number;
  doctor_id?: number;
  hospital_id?: number;
  status: string;
  reason: string;
  requested_documents?: DocumentContract[];
}

export interface AccessGrantContract {
  id: number;
  patient_id: number;
  doctor_id?: number;
  hospital_id?: number;
  consent_id?: number;
  status: string;
  expires_at: string;
  granted_documents?: DocumentContract[];
}

export interface NotificationContract {
  id: number;
  is_read: boolean;
  message: string;
  created_at: string;
}

export interface AuditLogContract {
  id: number;
  operation: string;
  timestamp: string;
  target_user_id?: number | null;
  document_id?: number | null;
  patient_id?: number | null;
  consent_id?: number | null;
  outcome?: string | null;
}

export interface AdminDashboardContract {
  total_users: number;
  total_hospitals: number;
  total_triage_requests: number;
  active_grants: number;
}

export interface ConsentPolicyContract {
  id: number;
  version_number: number;
  status: string;
  policy_payload: {
    allowed_purposes?: string[];
    allowed_operations?: string[];
    [key: string]: unknown;
  };
  valid_from?: string | null;
  valid_until?: string | null;
}

export interface ConsentStateContract {
  id: number;
  status: string;
  reason?: string | null;
  created_at?: string;
}

export interface ConsentContract {
  id: number;
  patient_id: number;
  doctor_id?: number | null;
  hospital_id?: number | null;
  status: string;
  created_at: string;
  updated_at?: string;
  current_state?: ConsentStateContract | null;
  active_policy?: ConsentPolicyContract | null;
}

export interface FhirExportContextContract {
  purpose: string;
  hospital_id?: number;
}

export interface FhirBundleContract {
  resourceType: 'Bundle';
  type: string;
  entry?: Array<{ resource: Record<string, unknown> }>;
}
