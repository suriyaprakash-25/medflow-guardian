import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthShell } from '@shared/ui/AuthShell';
import { Button } from '@shared/ui/Button';
import { FeedbackState } from '@shared/ui/FeedbackState';
import { FormField } from '@shared/ui/FormField';
import { Input } from '@shared/ui/Input';
import type { LoginResponseContract } from '@shared/api/contracts';
import { api, setAccessToken } from '../lib/api';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [preAuthToken, setPreAuthToken] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const completeLogin = (accessToken: string) => {
    setAccessToken(accessToken);
    setPreAuthToken(null);
    navigate('/dashboard');
  };

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('username', email.trim());
      formData.append('password', password);
      const response = await api.post<LoginResponseContract>('/api/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      if (response.data.role !== 'patient') {
        setError('This sign-in page is only for patient accounts.');
        return;
      }
      if (response.data.mfa_required) {
        setPreAuthToken(response.data.access_token);
        setPassword('');
        return;
      }
      completeLogin(response.data.access_token);
    } catch {
      setError('Sign in failed. Verify your email and password, then try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleMfaVerify = async (event: FormEvent) => {
    event.preventDefault();
    if (!preAuthToken) return;
    setError('');
    setLoading(true);
    try {
      const response = await api.post<LoginResponseContract>('/api/auth/mfa/verify', { code: mfaCode.trim() }, {
        headers: { Authorization: `Bearer ${preAuthToken}` },
      });
      completeLogin(response.data.access_token);
    } catch {
      setError('The verification code is invalid or expired. Request a new code and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      portalLabel="Patient portal"
      title="Your health information, with you in control."
      description="Review records, manage consent and communicate with care teams through an authenticated, policy-enforced workspace."
    >
      {error ? <div className="mb-5"><FeedbackState tone="error" title="Unable to sign in" message={error} compact /></div> : null}
      {preAuthToken ? (
        <form onSubmit={handleMfaVerify} className="grid gap-5">
          <FormField id="patient-mfa" label="Authenticator code" hint="Enter the current code from your authenticator app." required>
            <Input id="patient-mfa" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]*" value={mfaCode} onChange={(event) => setMfaCode(event.target.value)} aria-describedby="patient-mfa-hint" required />
          </FormField>
          <Button type="submit" disabled={loading || mfaCode.trim().length === 0} className="w-full">{loading ? 'Verifying…' : 'Verify and continue'}</Button>
          <Button type="button" variant="ghost" className="w-full" onClick={() => { setPreAuthToken(null); setMfaCode(''); setError(''); }}>Use a different account</Button>
        </form>
      ) : (
        <form onSubmit={handleLogin} className="grid gap-5">
          <FormField id="patient-email" label="Email address" required>
            <Input id="patient-email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </FormField>
          <FormField id="patient-password" label="Password" required>
            <Input id="patient-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </FormField>
          <Button type="submit" disabled={loading || !email.trim() || !password} className="w-full">{loading ? 'Signing in…' : 'Sign in securely'}</Button>
        </form>
      )}
    </AuthShell>
  );
}
