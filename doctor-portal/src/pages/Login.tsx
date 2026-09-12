import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api as axios, setAccessToken } from '../lib/api';

export default function Login() {
  const [email, setEmail] = useState('doctor@demo.com');
  const [password, setPassword] = useState('password');
  const [mfaCode, setMfaCode] = useState('');
  const [preAuthToken, setPreAuthToken] = useState<string | null>(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const completeLogin = (accessToken: string) => {
    setAccessToken(accessToken);
    setPreAuthToken(null);
    navigate('/dashboard');
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await axios.post('/api/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      if (response.data.role !== 'doctor') {
        setError('Only doctors can log in here.');
        return;
      }

      if (response.data.mfa_required) {
        setPreAuthToken(response.data.access_token);
        return;
      }

      completeLogin(response.data.access_token);
    } catch {
      setError('Login failed. Please check credentials.');
    }
  };

  const handleMfaVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!preAuthToken) return;
    setError('');
    try {
      const response = await axios.post(
        '/api/auth/mfa/verify',
        { code: mfaCode },
        { headers: { Authorization: `Bearer ${preAuthToken}` } },
      );
      completeLogin(response.data.access_token);
    } catch {
      setError('Invalid or expired MFA code. Please try again.');
    }
  };

  return (
    <div className="container center-page">
      <div className="card login-card">
        <h1>Doctor Portal</h1>
        {preAuthToken ? (
          <form onSubmit={handleMfaVerify}>
            {error && <div className="error">{error}</div>}
            <div className="form-group">
              <label>Authenticator code</label>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn-primary">Verify MFA</button>
          </form>
        ) : (
          <form onSubmit={handleLogin}>
            {error && <div className="error">{error}</div>}
            <div className="form-group">
              <label>Email</label>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <button type="submit" className="btn-primary">Sign In</button>
          </form>
        )}
      </div>
    </div>
  );
}
