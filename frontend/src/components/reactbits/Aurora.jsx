import React from 'react';

export function Aurora({ className = '' }) {
  return (
    <div
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      aria-hidden="true"
    >
      <div
        className="absolute -top-[30%] left-1/2 -translate-x-1/2 w-[700px] h-[450px] rounded-full opacity-20 blur-[120px]"
        style={{
          background: 'radial-gradient(circle, #00e5a3 0%, #0284c7 40%, transparent 70%)',
        }}
      />
      <div
        className="absolute top-[10%] right-[10%] w-[400px] h-[300px] rounded-full opacity-15 blur-[100px]"
        style={{
          background: 'radial-gradient(circle, #14b8a6 0%, #38bdf8 50%, transparent 70%)',
        }}
      />
    </div>
  );
}
