import type { ReactNode } from 'react';

export interface ResponsiveTableProps {
  label: string;
  children: ReactNode;
  className?: string;
}

export function ResponsiveTable({ label, children, className = '' }: ResponsiveTableProps) {
  return (
    <div className={`overflow-x-auto rounded-2xl border border-slate-200 bg-white ${className}`} role="region" aria-label={label} tabIndex={0}>
      <div className="min-w-[44rem]">{children}</div>
    </div>
  );
}
