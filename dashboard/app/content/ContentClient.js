'use client';

import { useState, useMemo } from 'react';
import Badge from '@/components/ui/Badge';
import DataTable from '@/components/ui/DataTable';
import { contentItems } from '@/lib/mockData';

const platformColors = {
  YouTube: '#FF0000',
  TikTok: '#00f2ea',
  Instagram: '#E1306C',
  'Twitter/X': '#1DA1F2',
  LinkedIn: '#0A66C2',
};

const platformEmojis = {
  YouTube: '▶️',
  TikTok: '♪',
  Instagram: '📷',
  'Twitter/X': '𝕏',
  LinkedIn: '💼',
};

function formatNum(n) {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toString();
}

export default function ContentClient() {
  const [view, setView] = useState('grid');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [formatFilter, setFormatFilter] = useState('all');

  const filtered = useMemo(() => {
    return contentItems.filter((c) => {
      if (platformFilter !== 'all' && c.platform !== platformFilter) return false;
      if (statusFilter !== 'all' && c.status !== statusFilter) return false;
      if (formatFilter !== 'all' && c.format !== formatFilter) return false;
      return true;
    });
  }, [platformFilter, statusFilter, formatFilter]);

  const columns = [
    {
      key: 'title',
      label: 'Title',
      render: (v, row) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.2rem' }}>{platformEmojis[row.platform] || '📄'}</span>
          <div>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.85rem' }}>{v}</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{row.duration}</div>
          </div>
        </div>
      ),
    },
    { key: 'platform', label: 'Platform', render: (v) => (
      <span className="badge" style={{ background: `${platformColors[v]}20`, color: platformColors[v], border: `1px solid ${platformColors[v]}40` }}>{v}</span>
    )},
    { key: 'format', label: 'Format' },
    { key: 'status', label: 'Status', render: (v) => <Badge status={v} /> },
    { key: 'views', label: 'Views', render: (v) => <span style={{ fontWeight: 600 }}>{formatNum(v)}</span> },
    { key: 'engagementRate', label: 'Eng. Rate', render: (v) => v > 0 ? (
      <span style={{ fontWeight: 600, color: v > 10 ? 'var(--accent-emerald)' : 'var(--text-primary)' }}>{v}%</span>
    ) : <span style={{ color: 'var(--text-dim)' }}>—</span> },
  ];

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Content Library</h1>
          <p className="page-subtitle">All generated content across platforms and formats</p>
        </div>
        <div className="view-toggle">
          <button
            id="view-grid"
            className={`view-toggle-btn ${view === 'grid' ? 'active' : ''}`}
            onClick={() => setView('grid')}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
          </button>
          <button
            id="view-list"
            className={`view-toggle-btn ${view === 'list' ? 'active' : ''}`}
            onClick={() => setView('list')}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar" style={{ marginBottom: '20px' }}>
        <select id="filter-content-platform" className="select" value={platformFilter} onChange={(e) => setPlatformFilter(e.target.value)}>
          <option value="all">All Platforms</option>
          <option value="YouTube">YouTube</option>
          <option value="TikTok">TikTok</option>
          <option value="Instagram">Instagram</option>
          <option value="Twitter/X">Twitter/X</option>
          <option value="LinkedIn">LinkedIn</option>
        </select>
        <select id="filter-content-format" className="select" value={formatFilter} onChange={(e) => setFormatFilter(e.target.value)}>
          <option value="all">All Formats</option>
          <option value="Short-form Video">Short-form Video</option>
          <option value="Carousel">Carousel</option>
          <option value="Thread">Thread</option>
        </select>
        <select id="filter-content-status" className="select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="all">All Statuses</option>
          <option value="published">Published</option>
          <option value="scheduled">Scheduled</option>
          <option value="review">Review</option>
          <option value="assembling">Assembling</option>
          <option value="scripting">Scripting</option>
          <option value="voiceover">Voiceover</option>
        </select>
        <span style={{ marginLeft: 'auto', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          {filtered.length} items
        </span>
      </div>

      {/* Grid View */}
      {view === 'grid' && (
        <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))' }}>
          {filtered.map((item, i) => (
            <div
              key={item.id}
              className="glass-card content-grid-card animate-in"
              style={{ animationDelay: `${i * 60}ms`, padding: 0 }}
            >
              <div
                className="content-thumbnail"
                style={{
                  background: `linear-gradient(135deg, ${platformColors[item.platform]}30, ${platformColors[item.platform]}10)`,
                }}
              >
                <span style={{ fontSize: '2.5rem', opacity: 0.4 }}>{platformEmojis[item.platform]}</span>
                <div style={{
                  position: 'absolute',
                  top: '8px',
                  right: '8px',
                }}>
                  <Badge status={item.status} />
                </div>
                {item.duration && (
                  <div style={{
                    position: 'absolute',
                    bottom: '8px',
                    right: '8px',
                    background: 'rgba(0,0,0,0.7)',
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-xs)',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                  }}>
                    {item.duration}
                  </div>
                )}
              </div>
              <div className="content-card-body">
                <div className="content-card-title">{item.title}</div>
                <div className="content-card-meta">
                  <span className="badge" style={{
                    background: `${platformColors[item.platform]}20`,
                    color: platformColors[item.platform],
                    border: `1px solid ${platformColors[item.platform]}40`,
                    fontSize: '0.68rem',
                  }}>
                    {item.platform}
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{item.format}</span>
                </div>
                {item.status === 'published' && (
                  <div className="content-card-stats">
                    <div className="content-stat">
                      <div className="content-stat-value">{formatNum(item.views)}</div>
                      <div className="content-stat-label">Views</div>
                    </div>
                    <div className="content-stat">
                      <div className="content-stat-value">{formatNum(item.likes)}</div>
                      <div className="content-stat-label">Likes</div>
                    </div>
                    <div className="content-stat">
                      <div className="content-stat-value">{formatNum(item.comments)}</div>
                      <div className="content-stat-label">Comments</div>
                    </div>
                    <div className="content-stat">
                      <div className="content-stat-value" style={{ color: 'var(--accent-emerald)' }}>{item.engagementRate}%</div>
                      <div className="content-stat-label">Eng.</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* List View */}
      {view === 'list' && (
        <DataTable columns={columns} data={filtered} pageSize={10} />
      )}
    </div>
  );
}
