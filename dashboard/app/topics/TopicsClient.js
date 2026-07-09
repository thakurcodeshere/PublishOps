'use client';

import { useState, useMemo } from 'react';
import DataTable from '@/components/ui/DataTable';
import ScoreBar from '@/components/ui/ScoreBar';
import Badge from '@/components/ui/Badge';
import RadarChart from '@/components/charts/RadarChart';
import { topics } from '@/lib/mockData';

export default function TopicsClient() {
  const [statusFilter, setStatusFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [minScore, setMinScore] = useState(0);
  const [expandedRow, setExpandedRow] = useState(null);

  const filtered = useMemo(() => {
    return topics.filter((t) => {
      if (statusFilter !== 'all' && t.status !== statusFilter) return false;
      if (sourceFilter !== 'all' && t.source !== sourceFilter) return false;
      if (t.compositeScore < minScore) return false;
      return true;
    });
  }, [statusFilter, sourceFilter, minScore]);

  const columns = [
    {
      key: 'title',
      label: 'Topic',
      render: (v, row) => (
        <div>
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.85rem' }}>{v}</div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '2px' }}>{row.category}</div>
        </div>
      ),
    },
    {
      key: 'compositeScore',
      label: 'Score',
      render: (v) => <ScoreBar value={v} size="sm" />,
    },
    { key: 'velocity', label: 'Velocity', render: (v) => <span style={{ fontWeight: 600, fontSize: '0.82rem' }}>{v}</span> },
    { key: 'evergreen', label: 'Evergreen', render: (v) => <span style={{ fontWeight: 600, fontSize: '0.82rem' }}>{v}</span> },
    { key: 'platformFit', label: 'Fit', render: (v) => <span style={{ fontWeight: 600, fontSize: '0.82rem' }}>{v}</span> },
    { key: 'saturation', label: 'Saturation', render: (v) => (
      <span style={{ fontWeight: 600, fontSize: '0.82rem', color: v > 50 ? 'var(--accent-rose)' : v > 30 ? 'var(--accent-amber)' : 'var(--accent-emerald)' }}>{v}%</span>
    )},
    { key: 'source', label: 'Source', render: (v) => <span className="badge badge-neutral">{v}</span> },
    { key: 'status', label: 'Status', render: (v) => <Badge status={v} /> },
    {
      key: 'actions',
      label: 'Actions',
      sortable: false,
      render: (_, row) => (
        <div className="btn-group">
          {row.status !== 'accepted' && row.status !== 'rejected' && (
            <>
              <button id={`accept-topic-${row.id}`} className="btn btn-success btn-sm" style={{ padding: '4px 8px', fontSize: '0.7rem' }}>
                ✓ Accept
              </button>
              <button id={`reject-topic-${row.id}`} className="btn btn-ghost btn-sm" style={{ padding: '4px 8px', fontSize: '0.7rem', color: 'var(--accent-rose)' }}>
                ✕ Reject
              </button>
            </>
          )}
        </div>
      ),
    },
  ];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Topic Explorer</h1>
        <p className="page-subtitle">Discover and evaluate trending topics with AI-powered composite scoring</p>
      </div>

      {/* Filters */}
      <div className="filter-bar" style={{ marginBottom: '20px' }}>
        <div className="input-group" style={{ gap: '4px' }}>
          <label className="input-label">Status</label>
          <select
            id="filter-status"
            className="select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="accepted">Accepted</option>
            <option value="scripting">Scripting</option>
            <option value="review">Review</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div className="input-group" style={{ gap: '4px' }}>
          <label className="input-label">Source</label>
          <select
            id="filter-source"
            className="select"
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
          >
            <option value="all">All Sources</option>
            <option value="Reddit">Reddit</option>
            <option value="Hacker News">Hacker News</option>
            <option value="Twitter/X">Twitter/X</option>
            <option value="Google Trends">Google Trends</option>
          </select>
        </div>

        <div className="input-group" style={{ gap: '4px', minWidth: '200px' }}>
          <label className="input-label">Min Score: {minScore}</label>
          <input
            id="filter-min-score"
            type="range"
            min="0"
            max="100"
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
          />
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'flex-end' }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            {filtered.length} topics found
          </span>
        </div>
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={filtered}
        pageSize={10}
        onRowClick={(row) => setExpandedRow(expandedRow === row.id ? null : row.id)}
      />

      {/* Expanded Radar Chart */}
      {expandedRow && (() => {
        const topic = topics.find((t) => t.id === expandedRow);
        if (!topic) return null;
        const radarData = [
          { axis: 'Velocity', value: topic.velocity },
          { axis: 'Evergreen', value: topic.evergreen },
          { axis: 'Platform Fit', value: topic.platformFit },
          { axis: 'Low Saturation', value: 100 - topic.saturation },
          { axis: 'Composite', value: topic.compositeScore },
        ];
        return (
          <div className="glass-card animate-in" style={{ marginTop: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '32px', flexWrap: 'wrap' }}>
              <div style={{ flex: '1 1 300px' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '8px' }}>{topic.title}</h3>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '16px' }}>
                  <Badge status={topic.status} />
                  <span className="badge badge-neutral">{topic.source}</span>
                  <span className="badge badge-info">{topic.category}</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div><ScoreBar value={topic.velocity} label="Velocity" /></div>
                  <div><ScoreBar value={topic.evergreen} label="Evergreen" /></div>
                  <div><ScoreBar value={topic.platformFit} label="Platform Fit" /></div>
                  <div><ScoreBar value={100 - topic.saturation} label="Uniqueness" /></div>
                </div>
              </div>
              <div style={{ flex: '0 0 280px' }}>
                <RadarChart data={radarData} height={260} />
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
