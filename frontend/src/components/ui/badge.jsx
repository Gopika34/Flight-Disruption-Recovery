import React from 'react';
import { cn } from '../../utils/cn';

export function Badge({ className, variant = 'default', children, ...props }) {
  const variants = {
    default: 'bg-teal-500/10 border-teal-500/20 text-teal-400',
    secondary: 'bg-slate-800 border-slate-700 text-slate-300',
    outline: 'border-slate-700 text-slate-400',
    success: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
    warning: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
    danger: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
    navy: 'bg-sky-500/10 border-sky-500/20 text-sky-400',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border font-mono',
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
