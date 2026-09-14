import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Clock3, Plus, RefreshCw, ShieldCheck } from 'lucide-react';
import { toast } from 'react-hot-toast';
import { Badge } from '@shared/ui/Badge';
import { Button } from '@shared/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@shared/ui/Card';
import { EmptyState } from '@shared/ui/EmptyState';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { Input } from '@shared/ui/Input';
import { Label } from '@shared/ui/Label';
import { api } from '../lib/api';

type Policy = {
  id: number;
  version_number: number;
  policy_payload: { allowed_purposes?: string[]; allowed_operations?: string[] };
  valid_from?: string | null;
  valid_until?: string | null;
};

type Consent = {
  id: number;
  doctor_id?: number | null;
  hospital_id?: number | null;
  status: string;
  current_state?: { status: string; created_at: string } | null;
  active_policy?: Policy | null;
};

const OPERATIONS = ['read', 'download', 'share', 'list', 'create'];
const TRANSITIONS: Record<string, string[]> = {
  active: ['suspended', 'revoked', 'expired'],
  suspended: ['active', 'revoked'],
};

function apiMessage(error: unknown): string {
  if (typeof error === 'object' && error && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return 'The consent request could not be completed.';
}

function toIso(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}

export default function Consents() {
  const [consents, setConsents] = useState<Consent[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [purpose, setPurpose] = useState('TREATMENT');
  const [operations, setOperations] = useState<string[]>(['read', 'download', 'list', 'create']);
  const [doctorId, setDoctorId] = useState('');
  const [hospitalId, setHospitalId] = useState('');
  const [validFrom, setValidFrom] = useState('');
  const [validUntil, setValidUntil] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get<Consent[]>('/api/consents');
      setConsents(response.data);
    } catch (error) {
      toast.error(apiMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const purposeList = useMemo(
    () => purpose.split(',').map((item) => item.trim()).filter(Boolean),
    [purpose],
  );

  const reset = () => {
    setEditingId(null);
    setPurpose('TREATMENT');
    setOperations(['read', 'download', 'list', 'create']);
    setDoctorId('');
    setHospitalId('');
    setValidFrom('');
    setValidUntil('');
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!purposeList.length || !operations.length) {
      toast.error('Choose at least one purpose and one operation.');
      return;
    }
    if (validFrom && validUntil && new Date(validUntil) <= new Date(validFrom)) {
      toast.error('The valid-until time must be later than valid-from.');
      return;
    }
    const policy = {
      allowed_purposes: purposeList,
      allowed_operations: operations,
      valid_from: toIso(validFrom),
      valid_until: toIso(validUntil),
    };
    setSaving(true);
    try {
      if (editingId) {
        await api.post(`/api/consents/${editingId}/policy-versions`, {
          ...policy,
          reason: 'Updated by patient in the consent portal',
        });
        toast.success('A new authoritative policy version was created.');
      } else {
        await api.post('/api/consents', {
          ...policy,
          doctor_id: doctorId ? Number(doctorId) : null,
          hospital_id: hospitalId ? Number(hospitalId) : null,
        });
        toast.success('Consent created and activated.');
      }
      reset();
      await load();
    } catch (error) {
      toast.error(apiMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const revise = (consent: Consent) => {
    const policy = consent.active_policy;
    setEditingId(consent.id);
    setPurpose((policy?.policy_payload.allowed_purposes || ['TREATMENT']).join(', '));
    setOperations(policy?.policy_payload.allowed_operations || ['read', 'list']);
    setValidFrom(policy?.valid_from ? policy.valid_from.slice(0, 16) : '');
    setValidUntil(policy?.valid_until ? policy.valid_until.slice(0, 16) : '');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const transition = async (consent: Consent, target: string) => {
    setSaving(true);
    try {
      await api.post(`/api/consents/${consent.id}/transition`, {
        target_status: target,
        reason: `Patient changed consent to ${target}`,
      });
      toast.success(`Consent ${target}.`);
      await load();
    } catch (error) {
      toast.error(apiMessage(error));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-950">Consent policies</h1>
        <p className="mt-1 text-sm text-slate-600">Control who may use your records, why, how, and for how long.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            {editingId ? <RefreshCw className="h-5 w-5" /> : <Plus className="h-5 w-5" />}
            {editingId ? `Create a new version for consent #${editingId}` : 'Create consent'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-5 md:grid-cols-2" onSubmit={submit}>
            {!editingId && <>
              <div><Label htmlFor="doctor-id">Doctor ID (optional)</Label><Input id="doctor-id" type="number" min="1" value={doctorId} onChange={(e) => setDoctorId(e.target.value)} /></div>
              <div><Label htmlFor="hospital-id">Hospital ID (optional)</Label><Input id="hospital-id" type="number" min="1" value={hospitalId} onChange={(e) => setHospitalId(e.target.value)} /></div>
            </>}
            <div className="md:col-span-2"><Label htmlFor="purposes">Allowed purposes</Label><Input id="purposes" value={purpose} onChange={(e) => setPurpose(e.target.value)} placeholder="TREATMENT, PAYMENT" /><p className="mt-1 text-xs text-slate-500">Use comma-separated policy purpose codes.</p></div>
            <fieldset className="md:col-span-2"><legend className="mb-2 text-sm font-medium">Allowed operations</legend><div className="flex flex-wrap gap-4">{OPERATIONS.map((operation) => <label className="flex items-center gap-2 text-sm" key={operation}><input type="checkbox" checked={operations.includes(operation)} onChange={() => setOperations((current) => current.includes(operation) ? current.filter((item) => item !== operation) : [...current, operation])} />{operation}</label>)}</div></fieldset>
            <div><Label htmlFor="valid-from">Valid from (optional)</Label><Input id="valid-from" type="datetime-local" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} /></div>
            <div><Label htmlFor="valid-until">Valid until (optional)</Label><Input id="valid-until" type="datetime-local" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} /></div>
            <div className="flex gap-3 md:col-span-2"><Button type="submit" disabled={saving}>{saving ? 'Saving…' : editingId ? 'Create policy version' : 'Create and activate'}</Button>{editingId && <Button variant="outline" onClick={reset}>Cancel</Button>}</div>
          </form>
        </CardContent>
      </Card>

      {loading ? <FeedbackState tone="loading" title="Loading consent policies" message="Reading the authoritative consent state." /> : consents.length === 0 ? <EmptyState icon={<ShieldCheck className="h-10 w-10" />} title="No consent policies" description="Create your first consent policy above." /> : (
        <div className="grid gap-4 lg:grid-cols-2">
          {consents.map((consent) => {
            const policy = consent.active_policy;
            const status = consent.current_state?.status || consent.status;
            return <Card key={consent.id}><CardHeader><div className="flex items-start justify-between gap-4"><div><CardTitle className="text-lg">Consent #{consent.id}</CardTitle><p className="mt-1 text-xs text-slate-500">Policy version {policy?.version_number || '—'}</p></div><Badge variant={status === 'active' ? 'success' : status === 'revoked' ? 'destructive' : 'secondary'}>{status}</Badge></div></CardHeader><CardContent className="space-y-4"><div className="text-sm"><p><span className="font-medium">Purposes:</span> {(policy?.policy_payload.allowed_purposes || []).join(', ') || 'None'}</p><p><span className="font-medium">Operations:</span> {(policy?.policy_payload.allowed_operations || []).join(', ') || 'None'}</p></div><div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600"><div className="flex items-center gap-2 font-medium text-slate-800"><Clock3 className="h-4 w-4" />Validity window</div><p className="mt-1">From: {policy?.valid_from ? new Date(policy.valid_from).toLocaleString() : 'Immediately'}</p><p>Until: {policy?.valid_until ? new Date(policy.valid_until).toLocaleString() : 'No expiry'}</p></div><div className="flex flex-wrap gap-2"><Button size="sm" variant="outline" onClick={() => revise(consent)} disabled={saving}>Revise policy</Button>{(TRANSITIONS[status] || []).map((target) => <Button key={target} size="sm" variant={target === 'revoked' ? 'destructive' : 'secondary'} onClick={() => void transition(consent, target)} disabled={saving}>{target}</Button>)}</div></CardContent></Card>;
          })}
        </div>
      )}
    </div>
  );
}
