'use client';

import { useState } from 'react';
import StageCard from '@/components/pipeline/StageCard';
import Badge from '@/components/ui/Badge';
import DataTable from '@/components/ui/DataTable';
import { pipelineStages, pipelineRuns } from '@/lib/mockData';

export default function PipelineClient() {
  const [errorLogOpen, setErrorLogOpen] = useState(true);

  const runColumns = [
    { key: 'id', label: 'Run ID', render: (v) => <span style={{ fontFamily: 'monospace', color: 'var(--accent-blue)' }}>{v}</span> },
    { key: 'status', label: 'Status', render: (v) => <Badge status={v} /> },
    { key: 'topicsProcessed', label: 'Topics' },
    { key: 'contentGenerated', label: 'Content' },
    { key: 'errors', label: 'Errors', render: (v) => <span style={{ color: v > 0 ? 'var(--accent-rose)' : 'var(--text-dim)' }}>{v}</span> },
    { key: 'duration', label: 'Duration' },
    { key: 'startedAt', label: 'Started', render: (v) => {
      const d = new Date(v);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }},
  ];

  const errors = [
    { time: '10:45 AM', stage: 'Assembly', message: 'FFmpeg process timeout after 120s — "WebAssembly Beyond Browser" video exceeded maximum render time', severity: 'error' },
    { time: '09:12 AM', stage: 'Scoring', message: 'Google Trends API rate limit hit — retried after 30s backoff, 2 topics dropped', severity: 'warning' },
    { time: '08:30 AM', stage: 'Publishing', message: 'Instagram Graph API 429 — upload quota exceeded, rescheduled for next window', severity: 'error' },
    { time: 'Yesterday', stage: 'Assembly', message: 'Missing font asset "Inter-Bold.woff2" — fell back to system font for thumbnail', severity: 'warning' },
  ];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Pipeline Monitor</h1>
        <p className="page-subtitle">Real-time status of the 7-stage content automation pipeline</p>
      </div>

      {/* Horizontal Pipeline Flow */}
      <div className="glass-card-static animate-in" style={{ marginBottom: '28px', padding: '24px' }}>
        <div className="pipeline-flow">
          {pipelineStages.map((stage, i) => (
            <div key={stage.id} style={{ display: 'flex', alignItems: 'center' }}>
              <div className={`pipeline-flow-stage ${stage.status}`}>
                <div className="pipeline-flow-icon">
                  {stage.status === 'completed' && (
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  )}
                  {stage.status === 'running' && (
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ animation: 'rotate 2s linear infinite' }}><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
                  )}
                  {stage.status === 'idle' && (
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-dim)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                  )}
                  {stage.status === 'error' && (
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--accent-rose)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
                  )}
                </div>
                <div className="pipeline-flow-label">{stage.name}</div>
              </div>
              {i < pipelineStages.length - 1 && (
                <div className={`pipeline-flow-connector ${stage.status === 'completed' ? 'active' : ''}`} />
              )}
            </div>
          ))}
        </div>
        {/* Running stage info */}
        {pipelineStages.find(s => s.status === 'running') && (
          <div style={{
            textAlign: 'center',
            marginTop: '8px',
            padding: '12px',
            background: 'rgba(59, 130, 246, 0.05)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid rgba(59, 130, 246, 0.15)',
          }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--accent-blue)', fontWeight: 600 }}>
              ⚡ Currently processing:
            </span>{' '}
            <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {pipelineStages.find(s => s.status === 'running').currentItem}
            </span>
          </div>
        )}
      </div>

      {/* Stage Cards Grid */}
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', marginBottom: '28px' }}>
        {pipelineStages.map((stage, i) => (
          <StageCard key={stage.id} stage={stage} index={i} />
        ))}
      </div>

      {/* Recent Pipeline Runs */}
      <div style={{ marginBottom: '28px' }}>
        <div className="section-header">
          <h2 className="section-title">Recent Pipeline Runs</h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Last 20 runs</span>
        </div>
        <DataTable columns={runColumns} data={pipelineRuns} pageSize={8} />
      </div>

      {/* Error Log */}
      <div className="glass-card-static error-log animate-in">
        <div
          className="error-log-header"
          onClick={() => setErrorLogOpen(!errorLogOpen)}
        >
          <div className="error-log-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            Error Log ({errors.length} recent issues)
          </div>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-dim)"
            strokeWidth="2"
            style={{
              transform: errorLogOpen ? 'rotate(180deg)' : 'none',
              transition: 'transform var(--transition-fast)',
            }}
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </div>
        {errorLogOpen && (
          <div className="error-log-body">
            {errors.map((err, i) => (
              <div key={i} className="error-log-entry">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-dim)',
                    fontFamily: 'monospace',
                  }}>
                    {err.time}
                  </span>
                  <Badge status={err.severity} label={err.stage} />
                </div>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>{err.message}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
