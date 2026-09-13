import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthShell } from '@shared/ui/AuthShell';
import { Button } from '@shared/ui/Button';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { FormField } from '@shared/ui/FormField';
import { Input } from '@shared/ui/Input';
import { api, clearAccessToken, setAccessToken } from '../lib/api';

interface Membership {
  role?: string;
}

interface AdminIdentity {
  system_role?: string;
  role?: string;
  memberships?: Membership[];
  full_name?: string;
  email?: string;
}

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [preAuthToken, setPreAuthToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const completeAdminLogin = async (accessToken: string) => {
    const userRes = await api.get('/api/auth/me', { headers: { Authorization: `Bearer ${accessToken}` } });
    const user = userRes.data as AdminIdentity;
    const isPlatformAdmin = user.system_role === 'platform_admin';
    const isOrgAdmin = Array.isArray(user.memberships) && user.memberships.some((membership) => membership.role === 'admin');

    if (!isPlatformAdmin && !isOrgAdmin) {
      clearAccessToken();
      localStorage.removeItem('user');
      try { await api.post('/api/auth/logout'); } catch { /* server revocation is best effort after local rejection */ }
      throw new Error('This account does not have administrative access.');
    }

    setAccessToken(accessToken);
    localStorage.setItem('user', JSON.stringify(user));
    setPreAuthToken(null);
    navigate('/dashboard');
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', email.trim());
      formData.append('password', password);
      const response = await api.post('/api/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      if (response.data.mfa_required) {
        setPreAuthToken(response.data.access_token);
        setPassword('');
        return;
      }
      await completeAdminLogin(response.data.access_token);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : 'Authentication failed. Verify your credentials and try again.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleMfaSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!preAuthToken) return;
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/api/auth/mfa/verify', { code: mfaCode.trim() }, {
        headers: { Authorization: `Bearer ${preAuthToken}` },
      });
      await completeAdminLogin(response.data.access_token);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'MFA verification failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      portalLabel="Administration console"
      title="Operational control with explicit administrative scope."
      description="Manage organizations, staff, audit evidence and system configuration without weakening the same server-side authorization boundary used by clinical workflows."
    >
      {error ? <div className="mb-5"><FeedbackState tone="error" title="Access not granted" message={error} compact /></div> : null}
      {preAuthToken ? (
        <form onSubmit={handleMfaSubmit} className="grid gap-5">
          <FormField id="admin-mfa" label="Authenticator code" hint="Enter the current code from your authenticator app." required>
            <Input id="admin-mfa" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]*" value={mfaCode} onChange={(event) => setMfaCode(event.target.value)} aria-describedby="admin-mfa-hint" required />
          </FormField>
          <Button type="submit" disabled={loading || !mfaCode.trim()} className="w-full">{loading ? 'Verifying…' : 'Verify and continue'}</Button>
          <Button type="button" variant="ghost" className="w-full" onClick={() => { setPreAuthToken(null); setMfaCode(''); setError(''); }}>Use a different account</Button>
        </form>
      ) : (
        <form onSubmit={handleSubmit} className="grid gap-5">
          <FormField id="admin-email" label="Administrator email" required>
            <Input id="admin-email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </FormField>
          <FormField id="admin-password" label="Password" required>
            <Input id="admin-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </FormField>
          <Button type="submit" disabled={loading || !email.trim() || !password} className="w-full">{loading ? 'Authenticating…' : 'Authenticate securely'}</Button>
        </form>
      )}
    </AuthShell>
  );
}
