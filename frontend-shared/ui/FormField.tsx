import type { ReactNode } from 'react';

export interface FormFieldProps {
  id?: string;
  htmlFor?: string;
  label: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
}

export function FormField({ id, htmlFor, label, hint, error, required, children }: FormFieldProps) {
  const resolvedId = id || htmlFor || '';
  const hintId = hint ? `${resolvedId}-hint` : undefined;
  const errorId = error ? `${resolvedId}-error` : undefined;

  return (
    <div className="grid gap-2">
      <label htmlFor={resolvedId} className="text-sm font-semibold text-slate-800">
        {label}{required ? <span className="ml-1 text-rose-600" aria-hidden="true">*</span> : null}
        {required ? <span className="sr-only"> (required)</span> : null}
      </label>
      {children}
      {hint ? <p id={hintId} className="text-xs leading-5 text-slate-600">{hint}</p> : null}
      {error ? <p id={errorId} role="alert" className="text-sm font-medium text-rose-700">{error}</p> : null}
    </div>
  );
}

export function describedByIds(id: string, hint?: string, error?: string) {
  return [hint ? `${id}-hint` : '', error ? `${id}-error` : ''].filter(Boolean).join(' ') || undefined;
}
