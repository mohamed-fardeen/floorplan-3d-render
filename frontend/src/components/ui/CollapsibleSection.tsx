import React, { useState } from 'react';

interface CollapsibleSectionProps {
  title: string;
  badge?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  actions?: React.ReactNode;
}

export const CollapsibleSection: React.FC<CollapsibleSectionProps> = ({
  title,
  badge,
  defaultOpen = true,
  children,
  actions,
}) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-gray-200">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-2 text-left text-xs font-semibold uppercase tracking-wide text-gray-600 hover:bg-gray-50"
      >
        <span className="flex items-center gap-2">
          <span className="text-gray-400">{open ? '▾' : '▸'}</span>
          {title}
          {badge ? (
            <span className="rounded bg-gray-200 px-1.5 py-0.5 text-[10px] font-normal normal-case text-gray-700">
              {badge}
            </span>
          ) : null}
        </span>
        {actions ? <span onClick={(e) => e.stopPropagation()}>{actions}</span> : null}
      </button>
      {open && <div className="px-4 pb-3 pt-1">{children}</div>}
    </div>
  );
};