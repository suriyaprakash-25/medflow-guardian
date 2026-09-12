import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, clearAccessToken, setAccessToken } from '../lib/api';
import toast from 'react-hot-toast';
import { ShieldCheck, Mail, Lock, ArrowRight, ShieldAlert } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [preAuthToken, setPreAuthToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const completeAdminLogin = async (accessToken: string) => {
    const userRes = await api.get('/api/auth/me', {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    const user = userRes.data;
    const isPlatformAdmin = user.system_role === 'platform_admin';
    const isOrgAdmin = Array.isArray(user.memberships)
      && user.memberships.some((membership: { role?: string }) => membership.role === 'admin');

    if (!isPlatformAdmin && !isOrgAdmin) {
      clearAccessToken();
      localStorage.removeItem('user');
      try {
        await api.post('/api/auth/logout');
      } catch {
        // The account is already being rejected locally; server revocation is
        // best-effort here because no administrative page is rendered.
      }
      throw new Error('This account does not have administrative access.');
    }

    setAccessToken(accessToken);
    localStorage.setItem('user', JSON.stringify(user));
    setPreAuthToken(null);
    toast.success('Secure session established');
    navigate('/dashboard');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const res = await api.post('/api/auth/login', formData);
      if (res.data.mfa_required) {
        setPreAuthToken(res.data.access_token);
        return;
      }

      await completeAdminLogin(res.data.access_token);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleMfaSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!preAuthToken) return;
    setLoading(true);
    try {
      const res = await api.post(
        '/api/auth/mfa/verify',
        { code: mfaCode },
        { headers: { Authorization: `Bearer ${preAuthToken}` } },
      );
      await completeAdminLogin(res.data.access_token);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || err?.message || 'MFA verification failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-100 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-100 rounded-full blur-3xl pointer-events-none"></div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="flex justify-center mb-6">
          <div className="bg-gradient-to-br from-blue-600 to-indigo-700 p-3 rounded-2xl shadow-lg shadow-blue-500/30">
            <ShieldCheck className="h-10 w-10 text-white" />
          </div>
        </div>
        <h2 className="text-center text-3xl font-extrabold text-slate-900 tracking-tight">MedFlow Guardian</h2>
        <p className="mt-2 text-center text-sm text-blue-600 font-semibold tracking-wide uppercase">Central Administration Console</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md relative z-10">
        <div className="bg-white/80 backdrop-blur-xl py-8 px-4 shadow-xl shadow-slate-200/50 sm:rounded-2xl sm:px-10 border border-slate-200">
          {preAuthToken ? (
            <form className="space-y-6" onSubmit={handleMfaSubmit}>
              <div>
                <label className="block text-sm font-medium text-slate-700">Authenticator code</label>
                <div className="mt-1 relative rounded-xl shadow-sm">
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    required
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value)}
                    className="block w-full px-3 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="123456"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Verifying…' : 'Verify MFA'}
              </button>
            </form>
          ) : (
            <form className="space-y-6" onSubmit={handleSubmit}>
              <div>
                <label className="block text-sm font-medium text-slate-700">Administrator Email</label>
                <div className="mt-1 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="block w-full !pl-10 pr-3 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="admin@example.com"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700">Password</label>
                <div className="mt-1 relative rounded-xl shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="block w-full !pl-10 pr-3 py-2.5 bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Authenticating…' : <><span>Authenticate</span><ArrowRight className="h-4 w-4" /></>}
              </button>
            </form>
          )}

          <div className="mt-6 flex items-center justify-center gap-2 text-xs text-slate-500 font-medium">
            <ShieldAlert className="h-4 w-4 text-slate-400" />
            <p>Access is enforced by server-side authorization policy.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
