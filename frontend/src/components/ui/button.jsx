import React from 'react';
import { cn } from '../../utils/cn';

export function Button({
  className,
  variant = 'default',
  size = 'default',
  disabled,
  children,
  ...props
}) {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-lg transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-500 disabled:pointer-events-none disabled:opacity-50 cursor-pointer select-none';

  const variants = {
    default: 'bg-teal-500 text-slate-950 font-semibold hover:bg-teal-400 active:bg-teal-600 shadow-sm shadow-teal-500/10',
    secondary: 'bg-slate-800 text-slate-100 hover:bg-slate-700 border border-slate-700/80',
    outline: 'border border-slate-700 text-slate-300 hover:text-white hover:bg-slate-800/60',
    ghost: 'text-slate-400 hover:text-white hover:bg-slate-800/50',
    danger: 'bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20',
    navy: 'bg-slate-900 border border-slate-700/80 text-teal-400 hover:border-teal-500/50 hover:bg-slate-850',
  };

  const sizes = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    default: 'text-sm px-4 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5',
    icon: 'h-9 w-9 p-0',
  };

  return (
    <button
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      disabled={disabled}
      {...props}
    >
      {children}
    </button>
  );
}
