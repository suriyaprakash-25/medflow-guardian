import type { ReactNode } from 'react';
import { AlertCircle, CheckCircle2, Info, LoaderCircle } from 'lucide-react';

export type FeedbackTone = 'loading' | 'empty' | 'error' | 'success' | 'info';

export interface FeedbackStateProps {
  tone: FeedbackTone;
  title: string;
  message?: string;
  action?: ReactNode;
  compact?: boolean;
}

const toneStyles: Record<FeedbackTone, string> = {
  loading: 'border-slate-200 bg-slate-50 text-slate-700',
  empty: 'border-slate-200 bg-white text-slate-700',
  error: 'border-rose-200 bg-rose-50 text-rose-900',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  info: 'border-blue-200 bg-blue-50 text-blue-900',
};

export function FeedbackState({ tone, title, message, action, compact = false }: FeedbackStateProps) {
  const Icon = tone === 'error' ? AlertCircle : tone === 'success' ? CheckCircle2 : tone === 'loading' ? LoaderCircle : Info;
  const live = tone === 'error' ? 'assertive' : 'polite';

  return (
    <div
      className={`rounded-2xl border ${toneStyles[tone]} ${compact ? 'p-4' : 'p-6'}`}
      role={tone === 'error' ? 'alert' : 'status'}
      aria-live={live}
      aria-busy={tone === 'loading'}
    >
      <div className="flex items-start gap-3">
        <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${tone === 'loading' ? 'animate-spin' : ''}`} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{title}</p>
          {message ? <p className="mt-1 text-sm leading-6 opacity-80">{message}</p> : null}
          {action ? <div className="mt-4">{action}</div> : null}
        </div>
      </div>
    </div>
  );
}
