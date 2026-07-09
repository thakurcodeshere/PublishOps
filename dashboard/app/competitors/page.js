'use client';

import { useState } from 'react';

export default function CompetitorsPage() {
  const [competitors, setCompetitors] = useState([
    { id: '1', name: 'DevOpsWizard', url: 'youtube.com/devopswizard', audience: '250k subscribers', coverage_rate: '85%' },
    { id: '2', name: 'CodeSlinger', url: 'tiktok.com/@codeslinger', audience: '120k followers', coverage_rate: '40%' },
    { id: '3', name: 'SolopreneurSaaS', url: 'twitter.com/solopreneursaas', audience: '80k followers', coverage_rate: '60%' }
  ]);

  const [keywordGaps, setKeywordGaps] = useState([
    { keyword: 'alembic async migrations', search_volume: '4,500/mo', competitor_coverage: 'low', priority: 'high' },
    { keyword: 'fastapi background task queue', search_volume: '12,000/mo', competitor_coverage: 'medium', priority: 'high' },
    { keyword: 'docker compose redis local dev', search_volume: '8,200/mo', competitor_coverage: 'low', priority: 'high' },
    { keyword: 'boto3 presigned url upload', search_volume: '5,100/mo', competitor_coverage: 'high', priority: 'medium' }
  ]);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Competitive Gap Mapper</h1>
        <p className="page-subtitle">Identify keyword niches that are highly requested by the audience but under-served by competitors.</p>
      </div>

      <div className="two-column">
        {/* Tracked Competitors List */}
        <div className="glass-card-static">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '16px' }}>Tracked Competitors</h3>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Competitor Name</th>
                  <th>Audience size</th>
                  <th>Coverage Rate</th>
                </tr>
              </thead>
              <tbody>
                {competitors.map(c => (
                  <tr key={c.id}>
                    <td>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'block' }}>{c.name}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{c.url}</span>
                    </td>
                    <td>{c.audience}</td>
                    <td>
                      <span className="badge badge-info">{c.coverage_rate}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Opportunity Gap Matrix */}
        <div className="glass-card-static">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '16px' }}>Content Opportunity Gaps</h3>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Keyword / Topic</th>
                  <th>Search Volume</th>
                  <th>Coverage</th>
                  <th>Priority</th>
                </tr>
              </thead>
              <tbody>
                {keywordGaps.map((g, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{g.keyword}</td>
                    <td>{g.search_volume}</td>
                    <td>
                      <span className={`badge badge-${g.competitor_coverage === 'low' ? 'success' : g.competitor_coverage === 'medium' ? 'warning' : 'neutral'}`}>
                        {g.competitor_coverage}
                      </span>
                    </td>
                    <td>
                      <span className={`badge badge-${g.priority === 'high' ? 'error' : 'info'}`}>
                        {g.priority}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
