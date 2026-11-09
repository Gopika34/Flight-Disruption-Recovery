import React, { useEffect, useState } from 'react';
import { cn } from '../../utils/cn';

export function BlurText({
  text = '',
  className = '',
  delay = 50,
}) {
  const words = text.split(' ');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <h1 className={cn('inline-block tracking-tight text-white font-extrabold', className)}>
      {words.map((word, i) => (
        <span
          key={i}
          className="inline-block transition-all duration-700 ease-out mr-[0.3em]"
          style={{
            filter: mounted ? 'blur(0px)' : 'blur(10px)',
            opacity: mounted ? 1 : 0,
            transform: mounted ? 'translateY(0)' : 'translateY(8px)',
            transitionDelay: `${i * delay}ms`,
          }}
        >
          {word}
        </span>
      ))}
    </h1>
  );
}

export function ShinyText({ text, className = '' }) {
  return (
    <span
      className={cn(
        'relative inline-block font-semibold bg-gradient-to-r from-teal-300 via-teal-100 to-teal-400 bg-clip-text text-transparent animate-pulse',
        className
      )}
    >
      {text}
    </span>
  );
}

export function CountUp({ end = 0, duration = 1200, prefix = '', suffix = '' }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTimestamp = null;
    const target = Number(end) || 0;
    if (target === 0) {
      setCount(0);
      return;
    }

    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // Ease out quad
      const easedProgress = 1 - (1 - progress) * (1 - progress);
      setCount(Math.floor(easedProgress * target));

      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        setCount(target);
      }
    };

    const animId = window.requestAnimationFrame(step);
    return () => window.cancelAnimationFrame(animId);
  }, [end, duration]);

  return (
    <span className="font-mono tabular-nums">
      {prefix}
      {count.toLocaleString('en-IN')}
      {suffix}
    </span>
  );
}
