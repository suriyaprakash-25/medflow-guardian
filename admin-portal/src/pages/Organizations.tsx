import { useCallback, useEffect, useMemo, useState } from 'react';
import { Building, CheckCircle2, Pencil, Plus, Search, XCircle } from 'lucide-react';
import { Button } from '@shared/ui/Button';
import { Dialog } from '@shared/ui/Dialog';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { FormField } from '@shared/ui/FormField';
import { Input } from '@shared/ui/Input';
import { ResponsiveTable } from '@shared/ui/ResponsiveTable';
import { api } from '../lib/api';

interface Organization {
  id: number;
  name: string;
  address?: string | null;
  contact_info?: string | null;
  is_active: boolean;
}

interface StoredAdminUser {
  role?: string;
  system_role?: string;
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

export default function Organizations() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [contactInfo, setContactInfo] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const user = useMemo(() => readStoredUser(), []);
  const isPlatformAdmin = user.system_role === 'platform_admin' || user.role === 'platform_admin';

  const fetchOrganizations = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/hospitals');
      setOrganizations((response.data || []) as Organization[]);
      setError('');
    } catch (requestError: unknown) {
      setError(getApiDetail(requestError, 'Failed to load organizations'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => { void fetchOrganizations(); });
  }, [fetchOrganizations]);

  const openCreate = () => {
    setEditingId(null);
    setName('');
    setAddress('');
    setContactInfo('');
    setIsActive(true);
    setError('');
    setShowDialog(true);
  };

  const openEdit = (organization: Organization) => {
    setEditingId(organization.id);
    setName(organization.name || '');
    setAddress(organization.address || '');
    setContactInfo(organization.contact_info || '');
    setIsActive(Boolean(organization.is_active));
    setError('');
    setShowDialog(true);
  };

  const handleSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) {
      setError('Organization name is required');
      return;
    }

    setSaving(true);
    setError('');
    const payload = {
      name: name.trim(),
      address: address.trim() || null,
      contact_info: contactInfo.trim() || null,
      is_active: isActive,
    };

    try {
      if (editingId) await api.put(`/api/admin/organization/${editingId}`, payload);
      else await api.post('/api/admin/organization', payload);
      setShowDialog(false);
      await fetchOrganizations();
    } catch (requestError: unknown) {
      setError(getApiDetail(requestError, 'Failed to save organization'));
    } finally {
      setSaving(false);
    }
  };

  const filteredOrganizations = organizations.filter((organization) => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return true;
    return organization.name.toLowerCase().includes(query)
      || (organization.address || '').toLowerCase().includes(query)
      || String(organization.id).includes(query);
  });

  if (!isPlatformAdmin) {
    return <FeedbackState tone="error" title="Organization management unavailable" message="Only platform administrators can provision or edit organizations." />;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">Platform directory</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Organizations</h2>
          <p className="mt-2 text-sm text-slate-600">Provision hospitals and clinical networks using authoritative server records.</p>
        </div>
        <Button type="button" onClick={openCreate} className="gap-2 self-start sm:self-auto"><Plus className="h-4 w-4" aria-hidden="true" />Provision organization</Button>
      </header>

      {error && !showDialog ? <FeedbackState tone="error" title="Organization request failed" message={error} compact /> : null}

      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" aria-hidden="true" />
        <label htmlFor="organization-search" className="sr-only">Search organizations</label>
        <Input id="organization-search" value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} placeholder="Search by name, address, or ID" className="pl-10" />
      </div>

      {loading ? (
        <FeedbackState tone="loading" title="Loading organizations" message="Retrieving current organization records." />
      ) : filteredOrganizations.length === 0 ? (
        <FeedbackState tone="empty" title="No organizations found" message={searchTerm ? 'Try a different search term.' : 'No organizations have been provisioned yet.'} />
      ) : (
        <ResponsiveTable label="Organizations table">
          <table className="w-full border-collapse text-left">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-600">
                <th scope="col" className="p-4 pl-6">Organization</th>
                <th scope="col" className="p-4">Address</th>
                <th scope="col" className="p-4">Status</th>
                <th scope="col" className="p-4 pr-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredOrganizations.map((organization) => (
                <tr key={organization.id} className="hover:bg-slate-50/70">
                  <td className="p-4 pl-6">
                    <div className="font-semibold text-slate-950">{organization.name}</div>
                    <div className="mt-1 text-xs text-slate-500">Organization ID {organization.id}</div>
                  </td>
                  <td className="p-4 text-sm text-slate-600">{organization.address || 'Not provided'}</td>
                  <td className="p-4">
                    {organization.is_active ? (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800"><CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />Active</span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-800"><XCircle className="h-3.5 w-3.5" aria-hidden="true" />Inactive</span>
                    )}
                  </td>
                  <td className="p-4 pr-6 text-right">
                    <Button type="button" variant="ghost" size="sm" onClick={() => openEdit(organization)} className="gap-1.5"><Pencil className="h-4 w-4" aria-hidden="true" />Edit</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ResponsiveTable>
      )}

      <Dialog
        open={showDialog}
        onOpenChange={setShowDialog}
        title={editingId ? 'Edit organization' : 'Provision organization'}
        description="Organization state affects administrative and clinical membership context."
        footer={<div className="flex justify-end gap-3"><Button type="button" variant="outline" onClick={() => setShowDialog(false)}>Cancel</Button><Button type="submit" form="organization-form" disabled={saving}>{saving ? 'Saving…' : editingId ? 'Save changes' : 'Provision'}</Button></div>}
      >
        {error ? <div className="mb-4"><FeedbackState tone="error" title="Unable to save organization" message={error} compact /></div> : null}
        <form id="organization-form" onSubmit={handleSave} className="space-y-4">
          <FormField label="Organization name" htmlFor="organization-name"><Input id="organization-name" value={name} onChange={(event) => setName(event.target.value)} required data-autofocus /></FormField>
          <FormField label="Address" htmlFor="organization-address"><Input id="organization-address" value={address} onChange={(event) => setAddress(event.target.value)} /></FormField>
          <FormField label="Contact information" htmlFor="organization-contact"><Input id="organization-contact" value={contactInfo} onChange={(event) => setContactInfo(event.target.value)} /></FormField>
          <label className="flex min-h-11 items-center gap-3 rounded-xl border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700">
            <input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} className="h-5 w-5" />
            Organization is active
          </label>
        </form>
      </Dialog>
    </div>
  );
}
