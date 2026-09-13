import { useCallback, useEffect, useMemo, useState } from 'react';
import { Building, CheckCircle2, Plus, Search, XCircle } from 'lucide-react';
import { Button } from '@shared/ui/Button';
import { ConfirmModal } from '@shared/ui/ConfirmModal';
import { Dialog } from '@shared/ui/Dialog';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { FormField } from '@shared/ui/FormField';
import { Input } from '@shared/ui/Input';
import { ResponsiveTable } from '@shared/ui/ResponsiveTable';
import { api } from '../lib/api';

interface Organization {
  id: number;
  name: string;
}

interface StaffMember {
  membership_id: number;
  full_name?: string | null;
  email: string;
  role: string;
  is_active: boolean;
}

interface StoredAdminUser {
  role?: string;
  system_role?: string;
  memberships?: Array<{ hospital_id?: number; hospital_name?: string; role?: string }>;
}

function readStoredUser(): StoredAdminUser {
  try { return JSON.parse(localStorage.getItem('user') || '{}') as StoredAdminUser; }
  catch { return {}; }
}

function getApiDetail(error: unknown, fallback: string) {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const detail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail;
    if (detail) return detail;
  }
  return fallback;
}

export default function Staff() {
  const user = useMemo(() => readStoredUser(), []);
  const isPlatformAdmin = user.system_role === 'platform_admin' || user.role === 'platform_admin';
  const membershipOrgId = user.memberships?.[0]?.hospital_id;

  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [orgLoading, setOrgLoading] = useState(isPlatformAdmin);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedOrgId, setSelectedOrgId] = useState<string>('');
  const [showDialog, setShowDialog] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('doctor');
  const [error, setError] = useState('');
  const [deactivateId, setDeactivateId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const orgId = isPlatformAdmin ? selectedOrgId : membershipOrgId ? String(membershipOrgId) : '';

  useEffect(() => {
    if (!isPlatformAdmin) return;
    queueMicrotask(async () => {
      try {
        const response = await api.get('/api/hospitals');
        const nextOrganizations = (response.data || []) as Organization[];
        setOrganizations(nextOrganizations);
        setSelectedOrgId((current) => current || (nextOrganizations[0] ? String(nextOrganizations[0].id) : ''));
      } catch (requestError: unknown) {
        setError(getApiDetail(requestError, 'Failed to load organizations'));
      } finally {
        setOrgLoading(false);
      }
    });
  }, [isPlatformAdmin]);

  const fetchStaff = useCallback(async () => {
    if (!orgId) {
      setStaff([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const response = await api.get('/api/admin/staff', { params: { hospital_id: orgId } });
      setStaff((response.data || []) as StaffMember[]);
      setError('');
    } catch (requestError: unknown) {
      setStaff([]);
      setError(getApiDetail(requestError, 'Failed to load staff'));
    } finally {
      setLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    queueMicrotask(() => { void fetchStaff(); });
  }, [fetchStaff]);

  const resetDialog = () => {
    setShowDialog(false);
    setNewEmail('');
    setNewFullName('');
    setNewPassword('');
    setNewRole('doctor');
    setError('');
  };

  const handleProvision = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!orgId) return;
    if (newPassword.length < 12) {
      setError('Initial password must be at least 12 characters');
      return;
    }

    setSaving(true);
    setError('');
    try {
      await api.post('/api/admin/staff', {
        email: newEmail.trim(),
        full_name: newFullName.trim() || undefined,
        password: newPassword,
        role: newRole,
      }, { params: { hospital_id: orgId } });
      resetDialog();
      await fetchStaff();
    } catch (requestError: unknown) {
      setError(getApiDetail(requestError, 'Provision failed'));
    } finally {
      setSaving(false);
    }
  };

  const handleChangeRole = async (membershipId: number, role: string) => {
    setError('');
    try {
      await api.put(`/api/admin/staff/${membershipId}`, { role }, { params: { hospital_id: orgId } });
      await fetchStaff();
    } catch (requestError: unknown) {
      setError(getApiDetail(requestError, 'Role update failed'));
    }
  };

  const handleDeactivate = async () => {
    if (!deactivateId) return;
    setError('');
    try {
      await api.delete(`/api/admin/staff/${deactivateId}`, { params: { hospital_id: orgId } });
      setDeactivateId(null);
      await fetchStaff();
    } catch (requestError: unknown) {
      setError(getApiDetail(requestError, 'Deactivation failed'));
      setDeactivateId(null);
    }
  };

  const filteredStaff = staff.filter((member) => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return true;
    return (member.full_name || '').toLowerCase().includes(query)
      || member.email.toLowerCase().includes(query)
      || member.role.toLowerCase().includes(query);
  });

  const selectedOrganization = organizations.find((organization) => String(organization.id) === String(orgId));
  const organizationLabel = selectedOrganization?.name || user.memberships?.[0]?.hospital_name || (orgId ? `Organization ${orgId}` : '');

  if (isPlatformAdmin && orgLoading) {
    return <FeedbackState tone="loading" title="Loading organizations" message="Retrieving the organizations available for staff administration." />;
  }

  if (!orgId) {
    return <FeedbackState tone="empty" title="Organization required" message="Select an organization before managing practitioner and staff membership." action={<Building className="h-6 w-6 text-slate-400" aria-hidden="true" />} />;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">Membership administration</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Staff directory</h2>
          <p className="mt-2 text-sm text-slate-600">Manage practitioner and administrative membership for {organizationLabel}.</p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          {isPlatformAdmin ? (
            <div>
              <label htmlFor="staff-organization" className="sr-only">Organization</label>
              <select id="staff-organization" value={selectedOrgId} onChange={(event) => setSelectedOrgId(event.target.value)} className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm font-medium focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2">
                {organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}
              </select>
            </div>
          ) : null}
          <Button type="button" onClick={() => { setError(''); setShowDialog(true); }} className="gap-2"><Plus className="h-4 w-4" aria-hidden="true" />Provision account</Button>
        </div>
      </header>

      {error && !showDialog ? <FeedbackState tone="error" title="Staff operation failed" message={error} compact /> : null}

      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" aria-hidden="true" />
        <label htmlFor="staff-search" className="sr-only">Search staff</label>
        <Input id="staff-search" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Search by name, email, or role" className="pl-10" />
      </div>

      {loading ? (
        <FeedbackState tone="loading" title="Loading staff" message="Retrieving current organization membership." />
      ) : filteredStaff.length === 0 ? (
        <FeedbackState tone="empty" title="No staff found" message={searchTerm ? 'Try a different search term.' : 'No staff memberships are available for this organization.'} />
      ) : (
        <ResponsiveTable label="Staff directory table">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-600">
                <th scope="col" className="p-4 pl-6">Practitioner</th>
                <th scope="col" className="p-4">Contact</th>
                <th scope="col" className="p-4">Role</th>
                <th scope="col" className="p-4">Status</th>
                <th scope="col" className="p-4 pr-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredStaff.map((member) => (
                <tr key={member.membership_id} className="hover:bg-slate-50/70">
                  <td className="p-4 pl-6 font-semibold text-slate-950">{member.full_name || 'Name not provided'}</td>
                  <td className="p-4 text-sm text-slate-600">{member.email}</td>
                  <td className="p-4">
                    <label htmlFor={`staff-role-${member.membership_id}`} className="sr-only">Role for {member.full_name || member.email}</label>
                    <select id={`staff-role-${member.membership_id}`} value={member.role} onChange={(event) => void handleChangeRole(member.membership_id, event.target.value)} className="min-h-10 rounded-lg border border-slate-300 bg-white px-2 text-sm focus-visible:ring-2 focus-visible:ring-blue-700">
                      <option value="admin">Admin</option><option value="doctor">Doctor</option><option value="staff">Staff</option>
                    </select>
                  </td>
                  <td className="p-4">
                    {member.is_active ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800"><CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />Active</span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-800"><XCircle className="h-3.5 w-3.5" aria-hidden="true" />Inactive</span>
                    )}
                  </td>
                  <td className="p-4 pr-6 text-right">{member.is_active ? <Button type="button" variant="ghost" size="sm" onClick={() => setDeactivateId(member.membership_id)} className="text-rose-700 hover:bg-rose-50 hover:text-rose-800">Deactivate</Button> : <span className="text-xs text-slate-400">Inactive</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ResponsiveTable>
      )}

      <Dialog
        open={showDialog}
        onOpenChange={(open) => { if (!open) resetDialog(); else setShowDialog(true); }}
        title="Provision staff account"
        description={`Create an account and membership within ${organizationLabel}.`}
        footer={<div className="flex justify-end gap-3"><Button type="button" variant="outline" onClick={resetDialog}>Cancel</Button><Button type="submit" form="provision-staff-form" disabled={saving}>{saving ? 'Provisioning…' : 'Provision account'}</Button></div>}
      >
        {error ? <div className="mb-4"><FeedbackState tone="error" title="Unable to provision account" message={error} compact /></div> : null}
        <form id="provision-staff-form" onSubmit={handleProvision} className="space-y-4">
          <FormField label="Email address" htmlFor="new-staff-email"><Input id="new-staff-email" type="email" value={newEmail} onChange={(event) => setNewEmail(event.target.value)} autoComplete="email" required data-autofocus /></FormField>
          <FormField label="Full name" htmlFor="new-staff-name"><Input id="new-staff-name" value={newFullName} onChange={(event) => setNewFullName(event.target.value)} autoComplete="name" /></FormField>
          <FormField label="Initial password" htmlFor="new-staff-password" hint="Minimum 12 characters. The user should change it according to organization policy."><Input id="new-staff-password" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} autoComplete="new-password" minLength={12} required /></FormField>
          <FormField label="Role" htmlFor="new-staff-role">
            <select id="new-staff-role" value={newRole} onChange={(event) => setNewRole(event.target.value)} className="min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3 text-sm focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2">
              <option value="doctor">Doctor</option><option value="admin">Administrator</option><option value="staff">Support staff</option>
            </select>
          </FormField>
        </form>
      </Dialog>

      <ConfirmModal
        isOpen={deactivateId !== null}
        title="Deactivate staff membership"
        description="The staff member will no longer have active membership access for this organization."
        confirmText="Deactivate membership"
        isDestructive
        onConfirm={() => void handleDeactivate()}
        onCancel={() => setDeactivateId(null)}
      />
    </div>
  );
}
