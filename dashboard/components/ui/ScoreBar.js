'use client';

import { useEffect, useState } from 'react';

export default function ScoreBar({ value = 0, label = '', showValue = true, size = 'md' }) {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setWidth(value), 100);
    return () => clearTimeout(timer);
  }, [value]);

  const getColor = (v) => {
    if (v < 40) return 'var(--accent-rose)';
    if (v < 65) return 'var(--accent-amber)';
    if (v < 85) return 'var(--accent-emerald)';
    return 'var(--accent-blue)';
  };

  const getGradient = (v) => {
    if (v < 40) return 'linear-gradient(90deg, #f43f5e, #fb7185)';
    if (v < 65) return 'linear-gradient(90deg, #f59e0b, #fbbf24)';
    if (v < 85) return 'linear-gradient(90deg, #10b981, #34d399)';
    return 'linear-gradient(90deg, #3b82f6, #8b5cf6)';
  };

  const height = size === 'sm' ? '5px' : size === 'lg' ? '12px' : '8px';

  return (
    <div className="score-bar-container">
      {label && (
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', minWidth: '60px' }}>
          {label}
        </span>
      )}
      <div className="score-bar-track" style={{ height }}>
        <div
          className="score-bar-fill"
          style={{
            width: `${width}%`,
            background: getGradient(value),
            height,
          }}
        />
      </div>
      {showValue && (
        <span className="score-bar-value" style={{ color: getColor(value) }}>
          {value}
        </span>
      )}
    </div>
  );
}
