'use client';

import { useState } from 'react';

export default function ContentArcsPage() {
  const [arcs, setArcs] = useState([
    {
      id: '1',
      name: 'Async SQLAlchemy Masterclass',
      status: 'active',
      start_date: '2026-06-01',
      end_date: '2026-06-30',
      description: 'Educational campaign on building highly scaleable python backends with SQLALchemy and asyncpg.',
      segments: [
        { title: 'Conquering Async DB Pools in FastAPI', platform: 'YouTube', format: 'educational' },
        { title: 'Why your async queries are blocking the event loop', platform: 'TikTok', format: 'educational' },
        { title: 'Alembic async migrations cheatsheet', platform: 'Twitter', format: 'personal story' }
      ]
    },
    {
      id: '2',
      name: 'Productivity Hacks for Solopreneurs',
      status: 'active',
      start_date: '2026-06-10',
      end_date: '2026-07-15',
      description: 'Focusing on building automated marketing funnels and leveraging serverless workflows.',
      segments: [
        { title: 'How I built a multi-platform content engine in a weekend', platform: 'LinkedIn', format: 'personal story' },
        { title: 'Why I hate manual scheduling tools', platform: 'TikTok', format: 'entertainment' },
        { title: 'Build V1 prototypes with no-code', platform: 'YouTube', format: 'educational' }
      ]
    }
  ]);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Content Arc Planner</h1>
        <p className="page-subtitle">Map out multi-week campaign narratives and cross-platform repurposing paths.</p>
      </div>

      <div className="grid grid-cols-3" style={{ marginBottom: '32px' }}>
        {/* Content Mix stats */}
        <div className="glass-card-static">
          <span className="stat-label">📚 Educational Mix</span>
          <span className="stat-value">40%</span>
          <div className="score-bar-track" style={{ marginTop: '8px' }}>
            <div className="score-bar-fill" style={{ width: '40%', background: 'var(--accent-blue)' }} />
          </div>
        </div>
        <div className="glass-card-static">
          <span className="stat-label">🍿 Entertainment Mix</span>
          <span className="stat-value">30%</span>
          <div className="score-bar-track" style={{ marginTop: '8px' }}>
            <div className="score-bar-fill" style={{ width: '30%', background: 'var(--accent-violet)' }} />
          </div>
        </div>
        <div className="glass-card-static">
          <span className="stat-label">🚀 Offers & Stories</span>
          <span className="stat-value">30%</span>
          <div className="score-bar-track" style={{ marginTop: '8px' }}>
            <div className="score-bar-fill" style={{ width: '30%', background: 'var(--accent-amber)' }} />
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {arcs.map(arc => (
          <div key={arc.id} className="glass-card-static">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div>
                <span className="badge badge-success" style={{ marginBottom: '6px' }}>{arc.status}</span>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 700 }}>{arc.name}</h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>📅 {arc.start_date} to {arc.end_date}</span>
              </div>
            </div>
            
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              {arc.description}
            </p>

            <h4 className="input-label" style={{ marginBottom: '10px' }}>Planned Campaign Variants</h4>
            <div className="data-table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Variant Topic</th>
                    <th>Target Platform</th>
                    <th>Funnel Format</th>
                  </tr>
                </thead>
                <tbody>
                  {arc.segments.map((s, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.title}</td>
                      <td>{s.platform}</td>
                      <td>
                        <span className={`badge badge-${s.format === 'educational' ? 'info' : s.format === 'entertainment' ? 'warning' : 'success'}`}>
                          {s.format}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
