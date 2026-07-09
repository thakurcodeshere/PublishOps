'use client';

import { useEffect, useState } from 'react';

const stageIcons = {
  search: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>,
  chart: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>,
  edit: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>,
  mic: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>,
  film: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="m10 8 6 4-6 4V8z"/></svg>,
  check: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>,
  upload: <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>,
};

export default function PipelineRing({ stages }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const centerX = 200;
  const centerY = 200;
  const radius = 155;
  const total = stages.length;
  const runningStage = stages.find(s => s.status === 'running');

  const stagePositions = stages.map((stage, i) => {
    const angle = (i / total) * 2 * Math.PI - Math.PI / 2;
    return {
      ...stage,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  });

  const statusColors = {
    completed: '#10b981',
    running: '#3b82f6',
    error: '#f43f5e',
    idle: '#334155',
  };

  return (
    <div className="pipeline-ring-container" style={{ width: '400px', height: '400px', margin: '0 auto', position: 'relative' }}>
      <svg width="400" height="400" viewBox="0 0 400 400">
        <defs>
          <linearGradient id="ring-grad-active" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Connection lines */}
        {stagePositions.map((stage, i) => {
          const next = stagePositions[(i + 1) % total];
          const isActive = stage.status === 'completed' || stage.status === 'running';
          return (
            <line
              key={`line-${i}`}
              x1={stage.x}
              y1={stage.y}
              x2={next.x}
              y2={next.y}
              stroke={isActive ? statusColors[stage.status] : 'rgba(255,255,255,0.08)'}
              strokeWidth={isActive ? 2 : 1}
              strokeDasharray={isActive ? 'none' : '4 4'}
              style={{
                opacity: mounted ? 1 : 0,
                transition: `opacity 0.5s ease ${i * 0.1}s`,
              }}
            />
          );
        })}

        {/* Animated flowing dots on active connections */}
        {stagePositions.map((stage, i) => {
          if (stage.status !== 'completed' && stage.status !== 'running') return null;
          const next = stagePositions[(i + 1) % total];
          return (
            <circle
              key={`dot-${i}`}
              r="3"
              fill={statusColors[stage.status]}
              filter="url(#glow)"
            >
              <animateMotion
                dur="2s"
                repeatCount="indefinite"
                path={`M${stage.x},${stage.y} L${next.x},${next.y}`}
              />
            </circle>
          );
        })}

        {/* Stage nodes */}
        {stagePositions.map((stage, i) => (
          <g
            key={stage.id}
            style={{
              opacity: mounted ? 1 : 0,
              transition: `opacity 0.5s ease ${i * 0.1}s`,
              cursor: 'pointer',
            }}
          >
            {/* Background glow for running */}
            {stage.status === 'running' && (
              <circle
                cx={stage.x}
                cy={stage.y}
                r="35"
                fill="rgba(59, 130, 246, 0.15)"
                filter="url(#glow)"
              >
                <animate attributeName="r" values="32;38;32" dur="2s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.3;0.6;0.3" dur="2s" repeatCount="indefinite" />
              </circle>
            )}

            {/* Node circle */}
            <circle
              cx={stage.x}
              cy={stage.y}
              r="28"
              fill="rgba(17, 24, 39, 0.9)"
              stroke={statusColors[stage.status]}
              strokeWidth={stage.status === 'running' ? 2.5 : 1.5}
            />

            {/* Icon placeholder (colored circle) */}
            <circle
              cx={stage.x}
              cy={stage.y}
              r="10"
              fill={statusColors[stage.status]}
              opacity="0.6"
            />
          </g>
        ))}
      </svg>

      {/* Stage labels */}
      {stagePositions.map((stage) => (
        <div
          key={`label-${stage.id}`}
          className={`pipeline-stage-label`}
          style={{
            position: 'absolute',
            left: stage.x,
            top: stage.y + 36,
            transform: 'translate(-50%, 0)',
            color: stage.status === 'running' ? 'var(--accent-blue)' : stage.status === 'completed' ? 'var(--accent-emerald)' : 'var(--text-dim)',
            fontWeight: stage.status === 'running' ? 700 : 600,
          }}
        >
          {stage.shortName}
        </div>
      ))}

      {/* Center info */}
      <div className="pipeline-center-info">
        {runningStage ? (
          <>
            <div className="pipeline-center-stage" style={{ animation: 'pulse 2s infinite' }}>
              ⚡ {runningStage.name}
            </div>
            <div className="pipeline-center-item">
              {runningStage.currentItem || 'Processing...'}
            </div>
          </>
        ) : (
          <>
            <div style={{ fontSize: '1.5rem', marginBottom: '4px' }}>✓</div>
            <div className="pipeline-center-stage" style={{ color: 'var(--accent-emerald)' }}>
              Pipeline Idle
            </div>
            <div className="pipeline-center-item">
              All stages complete
            </div>
          </>
        )}
      </div>
    </div>
  );
}
