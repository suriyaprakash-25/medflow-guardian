import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KeyRound, LogOut, ShieldCheck, UserRound } from 'lucide-react';
import toast from 'react-hot-toast';
import { Button } from '@shared/ui/Button';
import { Dialog } from '@shared/ui/Dialog';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { FormField } from '@shared/ui/FormField';
import { Input } from '@shared/ui/Input';
import { api, clearAccessToken, setAccessToken } from '../lib/api';

interface StoredAdminUser {
  id?: number;
  email?: string;
  full_name?: string;
  system_role?: string;
  role?: string;
  memberships?: Array<{ hospital_id?: number; hospital_name?: string; role?: string }>;
}

interface MfaEnrollment {
  secret: string;
  uri: string;
}

function readStoredUser(): StoredAdminUser {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}') as StoredAdminUser;
  } catch {
    return {};
  }
}

export default function Settings() {
  const navigate = useNavigate();
  const initialUser = useMemo(() => readStoredUser(), []);
  const [user, setUser] = useState<StoredAdminUser>(initialUser);
  const [fullName, setFullName] = useState(initialUser.full_name || '');
  const [email, setEmail] = useState(initialUser.email || '');
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileError, setProfileError] = useState('');

  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);

  const [mfaDialogOpen, setMfaDialogOpen] = useState(false);
  const [mfaEnrollment, setMfaEnrollment] = useState<MfaEnrollment | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const [mfaBusy, setMfaBusy] = useState(false);
  const [mfaMessage, setMfaMessage] = useState('');

  const [revokingSessions, setRevokingSessions] = useState(false);

  const roleLabel = user.system_role === 'platform_admin' || user.role === 'platform_admin'
    ? 'Platform administrator'
    : 'Organization administrator';

  const refreshStoredIdentity = async () => {
    const session = await api.post('/api/auth/refresh');
    if (session.data?.access_token) setAccessToken(session.data.access_token);
    const me = await api.get('/api/auth/me');
    const nextUser = me.data as StoredAdminUser;
    localStorage.setItem('user', JSON.stringify(nextUser));
    setUser(nextUser);
    setFullName(nextUser.full_name || '');
    setEmail(nextUser.email || '');
  };

  const handleProfileSave = async (event: React.FormEvent) => {
    event.preventDefault();
    setProfileError('');
    setSavingProfile(true);
    try {
      await api.patch('/api/auth/me', {
        full_name: fullName.trim() || null,
        email: email.trim() || null,
      });
      await refreshStoredIdentity();
      toast.success('Administrative profile updated');
    } catch (error: unknown) {
      const detail = typeof error === 'object' && error !== null && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      setProfileError(detail || 'Unable to update the administrative profile.');
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setChangingPassword(true);
    try {
      await api.post('/api/auth/change-password', {
        old_password: currentPassword,
        new_password: newPassword,
      });
      clearAccessToken();
      localStorage.removeItem('user');
      toast.success('Password changed. Sign in again with your new password.');
      navigate('/login', { replace: true });
    } catch (error: unknown) {
      const detail = typeof error === 'object' && error !== null && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      toast.error(detail || 'Password change failed');
    } finally {
      setChangingPassword(false);
    }
  };

  const beginMfaEnrollment = async () => {
    setMfaBusy(true);
    setMfaMessage('');
    try {
      const response = await api.post('/api/auth/mfa/enroll');
      setMfaEnrollment({ secret: response.data.secret, uri: response.data.uri });
      setMfaCode('');
      setMfaMessage('Add the account to your authenticator app, then enter the generated six-digit code.');
    } catch (error: unknown) {
      const detail = typeof error === 'object' && error !== null && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      setMfaMessage(detail || 'Unable to start MFA enrollment.');
    } finally {
      setMfaBusy(false);
    }
  };

  const verifyMfa = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!mfaEnrollment) return;
    setMfaBusy(true);
    try {
      const response = await api.post('/api/auth/mfa/verify', { code: mfaCode });
      if (response.data?.access_token) setAccessToken(response.data.access_token);
      setMfaMessage('Multi-factor authentication is enabled for this account.');
      setMfaEnrollment(null);
      setMfaCode('');
      toast.success('Multi-factor authentication enabled');
    } catch (error: unknown) {
      const detail = typeof error === 'object' && error !== null && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      setMfaMessage(detail || 'The verification code could not be confirmed.');
    } finally {
      setMfaBusy(false);
    }
  };

  const revokeOtherSessions = async () => {
    setRevokingSessions(true);
    try {
      await api.post('/api/auth/logout-all');
      clearAccessToken();
      localStorage.removeItem('user');
      toast.success('All sessions revoked. Sign in again to continue.');
      navigate('/login', { replace: true });
    } catch (error: unknown) {
      const detail = typeof error === 'object' && error !== null && 'response' in error
        ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : undefined;
      toast.error(detail || 'Unable to revoke sessions');
      setRevokingSessions(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-in fade-in duration-300">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">Account security</p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-950">Administrative settings</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          These controls call the server directly. MedFlow does not display simulated notification, MFA, or account state.
        </p>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="admin-profile-heading">
        <div className="mb-5 flex items-start gap-3">
          <div className="rounded-xl bg-blue-50 p-2 text-blue-700"><UserRound className="h-5 w-5" aria-hidden="true" /></div>
          <div>
            <h3 id="admin-profile-heading" className="font-bold text-slate-950">Profile and authorization context</h3>
            <p className="mt-1 text-sm text-slate-600">{roleLabel}. Organization access continues to be enforced by server-side policy.</p>
          </div>
        </div>

        {profileError ? <div className="mb-5"><FeedbackState tone="error" title="Profile update failed" message={profileError} compact /></div> : null}

        <form onSubmit={handleProfileSave} className="grid gap-5 sm:grid-cols-2">
          <FormField label="Full name" htmlFor="admin-full-name">
            <Input id="admin-full-name" value={fullName} onChange={(event) => setFullName(event.target.value)} autoComplete="name" />
          </FormField>
          <FormField label="Email address" htmlFor="admin-email" hint="Changing email refreshes the authenticated session before further API calls.">
            <Input id="admin-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required />
          </FormField>
          <div className="sm:col-span-2 flex justify-end">
            <Button type="submit" disabled={savingProfile}>{savingProfile ? 'Saving…' : 'Save profile'}</Button>
          </div>
        </form>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-labelledby="admin-security-heading">
        <div className="mb-5 flex items-start gap-3">
          <div className="rounded-xl bg-indigo-50 p-2 text-indigo-700"><ShieldCheck className="h-5 w-5" aria-hidden="true" /></div>
          <div>
            <h3 id="admin-security-heading" className="font-bold text-slate-950">Security actions</h3>
            <p className="mt-1 text-sm text-slate-600">High-impact actions are explicit and backed by existing authentication endpoints.</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <button type="button" onClick={() => setPasswordDialogOpen(true)} className="min-h-28 rounded-2xl border border-slate-200 p-4 text-left transition-colors hover:border-blue-300 hover:bg-blue-50/40 focus-visible:ring-2 focus-visible:ring-blue-700 focus-visible:ring-offset-2">
            <KeyRound className="h-5 w-5 text-blue-700" aria-hidden="true" />
            <span className="mt-3 block font-semibold text-slate-950">Change password</span>
            <span className="mt-1 block text-sm leading-5 text-slate-600">Revokes all sessions after a successful password change.</span>
          </button>

          <button type="button" onClick={() => { setMfaDialogOpen(true); setMfaMessage(''); }} className="min-h-28 rounded-2xl border border-slate-200 p-4 text-left transition-colors hover:border-indigo-300 hover:bg-indigo-50/40 focus-visible:ring-2 focus-visible:ring-indigo-700 focus-visible:ring-offset-2">
            <ShieldCheck className="h-5 w-5 text-indigo-700" aria-hidden="true" />
            <span className="mt-3 block font-semibold text-slate-950">Enroll MFA</span>
            <span className="mt-1 block text-sm leading-5 text-slate-600">Starts real TOTP enrollment. The server rejects enrollment if MFA is already enabled.</span>
          </button>

          <button type="button" disabled={revokingSessions} onClick={() => void revokeOtherSessions()} className="min-h-28 rounded-2xl border border-rose-200 p-4 text-left transition-colors hover:bg-rose-50 focus-visible:ring-2 focus-visible:ring-rose-700 focus-visible:ring-offset-2 disabled:opacity-60">
            <LogOut className="h-5 w-5 text-rose-700" aria-hidden="true" />
            <span className="mt-3 block font-semibold text-slate-950">Revoke all sessions</span>
            <span className="mt-1 block text-sm leading-5 text-slate-600">{revokingSessions ? 'Revoking sessions…' : 'Invalidates every refresh session and returns you to sign in.'}</span>
          </button>
        </div>
      </section>

      <Dialog
        open={passwordDialogOpen}
        onOpenChange={setPasswordDialogOpen}
        title="Change administrative password"
        description="A successful change revokes every active session for this account."
        footer={<div className="flex justify-end gap-3"><Button type="button" variant="outline" onClick={() => setPasswordDialogOpen(false)}>Cancel</Button><Button type="submit" form="change-password-form" disabled={changingPassword}>{changingPassword ? 'Changing…' : 'Change password'}</Button></div>}
      >
        <form id="change-password-form" onSubmit={handleChangePassword} className="space-y-4">
          <FormField label="Current password" htmlFor="current-password"><Input id="current-password" type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required data-autofocus /></FormField>
          <FormField label="New password" htmlFor="new-password" hint="Use a long, unique password consistent with your organization policy."><Input id="new-password" type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={12} required /></FormField>
        </form>
      </Dialog>

      <Dialog
        open={mfaDialogOpen}
        onOpenChange={(open) => { setMfaDialogOpen(open); if (!open) { setMfaEnrollment(null); setMfaCode(''); setMfaMessage(''); } }}
        title="Authenticator enrollment"
        description="MedFlow uses a time-based one-time password. Enrollment is not considered active until a code is verified."
        footer={mfaEnrollment ? <div className="flex justify-end gap-3"><Button type="button" variant="outline" onClick={() => setMfaDialogOpen(false)}>Cancel</Button><Button type="submit" form="mfa-verify-form" disabled={mfaBusy}>{mfaBusy ? 'Verifying…' : 'Verify and enable'}</Button></div> : undefined}
      >
        {!mfaEnrollment ? (
          <div className="space-y-4">
            {mfaMessage ? <FeedbackState tone={mfaMessage.toLowerCase().includes('already') ? 'info' : 'error'} title="MFA enrollment" message={mfaMessage} compact /> : <FeedbackState tone="info" title="Before you start" message="Have an authenticator application available. The enrollment secret is shown only for setup and should be treated as sensitive." compact />}
            <Button type="button" onClick={() => void beginMfaEnrollment()} disabled={mfaBusy}>{mfaBusy ? 'Starting…' : 'Start MFA enrollment'}</Button>
          </div>
        ) : (
          <form id="mfa-verify-form" onSubmit={verifyMfa} className="space-y-4">
            <FeedbackState tone="info" title="Enrollment created" message={mfaMessage} compact />
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              <p className="font-semibold text-slate-950">Authenticator URI</p>
              <p className="mt-2 break-all font-mono text-xs leading-5">{mfaEnrollment.uri}</p>
              <p className="mt-3 text-xs text-slate-500">Manual secret: <span className="font-mono text-slate-700">{mfaEnrollment.secret}</span></p>
            </div>
            <FormField label="Six-digit authenticator code" htmlFor="mfa-code"><Input id="mfa-code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" value={mfaCode} onChange={(event) => setMfaCode(event.target.value.replace(/\D/g, '').slice(0, 6))} required data-autofocus /></FormField>
          </form>
        )}
      </Dialog>
    </div>
  );
}
