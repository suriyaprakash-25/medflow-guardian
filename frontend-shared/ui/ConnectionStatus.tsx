export interface ConnectionStatusProps {
  status: 'connecting' | 'connected' | 'disconnected';
  className?: string;
}

export function ConnectionStatus({ status, className = '' }: ConnectionStatusProps) {
  const copy = status === 'connected'
    ? 'Realtime updates connected'
    : status === 'connecting'
      ? 'Connecting realtime updates'
      : 'Realtime updates unavailable';
  const dot = status === 'connected' ? 'bg-emerald-500' : status === 'connecting' ? 'bg-amber-500' : 'bg-slate-500';

  return (
    <div className={`inline-flex items-center gap-2 text-xs font-medium ${className}`} role="status" aria-live="polite">
      <span className={`h-2.5 w-2.5 rounded-full ${dot}`} aria-hidden="true" />
      <span>{copy}</span>
    </div>
  );
}
