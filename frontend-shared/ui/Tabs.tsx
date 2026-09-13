import { useId, useRef, type ReactNode } from 'react';

export interface TabItem {
  id: string;
  label: string;
  content: ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  label: string;
}

export function Tabs({ items, activeId, onChange, label }: TabsProps) {
  const instanceId = useId();
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const activeIndex = Math.max(0, items.findIndex((item) => item.id === activeId));

  const focusIndex = (index: number) => {
    const normalized = (index + items.length) % items.length;
    onChange(items[normalized].id);
    refs.current[normalized]?.focus();
  };

  return (
    <div>
      <div role="tablist" aria-label={label} className="flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
        {items.map((item, index) => {
          const selected = item.id === activeId;
          return (
            <button
              key={item.id}
              ref={(node) => { refs.current[index] = node; }}
              id={`${instanceId}-${item.id}-tab`}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`${instanceId}-${item.id}-panel`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(item.id)}
              onKeyDown={(event) => {
                if (event.key === 'ArrowRight') { event.preventDefault(); focusIndex(index + 1); }
                if (event.key === 'ArrowLeft') { event.preventDefault(); focusIndex(index - 1); }
                if (event.key === 'Home') { event.preventDefault(); focusIndex(0); }
                if (event.key === 'End') { event.preventDefault(); focusIndex(items.length - 1); }
              }}
              className={`min-h-11 whitespace-nowrap rounded-lg px-4 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 ${selected ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-600 hover:text-slate-950'}`}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {items.map((item) => {
        const selected = item.id === activeId;
        return (
          <div
            key={item.id}
            id={`${instanceId}-${item.id}-panel`}
            role="tabpanel"
            aria-labelledby={`${instanceId}-${item.id}-tab`}
            tabIndex={0}
            hidden={!selected}
            className="mt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
          >
            {item.content}
          </div>
        );
      })}
      <span className="sr-only" aria-live="polite">Selected tab: {items[activeIndex]?.label}</span>
    </div>
  );
}
