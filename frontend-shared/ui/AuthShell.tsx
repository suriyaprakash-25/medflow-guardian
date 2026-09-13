import type { ReactNode } from 'react';
import { ShieldCheck } from 'lucide-react';

export interface AuthShellProps {
  portalLabel: string;
  title: string;
  description: string;
  children: ReactNode;
  securityNote?: string;
}

export function AuthShell({ portalLabel, title, description, children, securityNote }: AuthShellProps) {
  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-8">
      <a href="#auth-form" className="skip-link">Skip to sign in</a>
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="hidden rounded-3xl bg-slate-950 p-10 text-white shadow-2xl lg:block" aria-labelledby="auth-intro-title">
          <div className="mb-8 inline-flex items-center gap-3 rounded-2xl bg-white/10 px-4 py-3">
            <ShieldCheck className="h-6 w-6 text-blue-300" aria-hidden="true" />
            <span className="text-sm font-semibold tracking-wide">MedFlow Guardian</span>
          </div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-blue-300">{portalLabel}</p>
          <h1 id="auth-intro-title" className="mt-4 max-w-xl text-4xl font-bold tracking-tight">{title}</h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-slate-300">{description}</p>
          <div className="mt-10 grid gap-3 text-sm text-slate-300">
            <p>• Your access is checked by server-side authorization policy.</p>
            <p>• Protected health information is released only after the required identity, relationship and consent checks.</p>
            <p>• Clinical recommendations remain subject to qualified clinician review.</p>
          </div>
        </section>

        <section className="mx-auto w-full max-w-md" aria-labelledby="auth-form-title">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/50 sm:p-8">
            <div className="mb-6 lg:hidden">
              <div className="mb-4 inline-flex items-center gap-2 rounded-xl bg-blue-50 px-3 py-2 text-blue-700">
                <ShieldCheck className="h-5 w-5" aria-hidden="true" />
                <span className="text-sm font-semibold">MedFlow Guardian</span>
              </div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">{portalLabel}</p>
            </div>
            <h2 id="auth-form-title" className="text-2xl font-bold tracking-tight text-slate-950">Secure sign in</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">Enter your assigned credentials. This form does not prefill account secrets.</p>
            <div id="auth-form" tabIndex={-1} className="mt-6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-4">{children}</div>
            <p className="mt-6 border-t border-slate-100 pt-5 text-xs leading-5 text-slate-500">
              {securityNote || 'Authentication establishes identity only; every protected action is still authorized by the server.'}
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
