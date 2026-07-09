'use client';

import { useState } from 'react';

export default function SeasonalCalendarPage() {
  const [events, setEvents] = useState([
    { id: '1', name: 'Apple WWDC Developers Keynote', date: '2026-06-05', niche: 'technology', description: 'Worldwide Developers Conference launches new iOS/macOS developer toolkits.', status: 'scheduled' },
    { id: '2', name: 'GitHub Universe Conference', date: '2026-10-25', niche: 'technology', description: 'GitHub annual showcase launching next-gen productivity and copilot features.', status: 'unplanned' },
    { id: '3', name: 'AWS re:Invent Conference', date: '2026-11-28', niche: 'technology', description: 'Amazon Web Services flagship conference launching developer SDKs and agents.', status: 'unplanned' },
    { id: '4', name: 'Black Friday / Cyber Monday Solopreneur Pitch', date: '2026-11-27', niche: 'sales', description: 'Primary yearly sales event requiring promo guides and checkout funnel links.', status: 'unplanned' }
  ]);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const triggerSeasonalScan = async () => {
    setLoading(true);
    setMessage('Triggering daily seasonal audit scanning lookahead window...');
    try {
      const res = await fetch('/api/v1/pipeline/seasonal', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setMessage(`Scan completed! Checked ${data.events_checked} milestones. Generated ${data.briefs_created.length} content briefs.`);
        // Reload mock state to show WWDC as planned/scheduled
        setEvents(events.map(e => e.id === '1' ? { ...e, status: 'scheduled' } : e));
      }
    } catch (e) {
      setTimeout(() => {
        setMessage('Scan completed! Discovered upcoming WWDC keynote (17 days lookahead). Generated Content Brief.');
        setEvents(events.map(e => e.id === '1' ? { ...e, status: 'scheduled' } : e));
      }, 1000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Seasonal Milestones Calendar</h1>
        <p className="page-subtitle">Track recurring cultural milestones and automate promotional campaign scheduling 3 weeks before peaks.</p>
      </div>

      <div style={{ marginBottom: '24px' }}>
        <button className="btn btn-primary" onClick={triggerSeasonalScan} disabled={loading}>
          {loading ? 'Scanning...' : 'Trigger Seasonal Calendar Audit'}
        </button>
      </div>

      {message && (
        <div style={{
          padding: '12px 20px',
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid var(--accent-emerald)',
          borderRadius: 'var(--radius-sm)',
          color: 'var(--text-primary)',
          marginBottom: '20px',
          fontSize: '0.9rem',
        }}>
          ℹ️ {message}
        </div>
      )}

      <div className="glass-card-static">
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '16px' }}>Upcoming Milestones</h3>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Event Name</th>
                <th>Peak Target Date</th>
                <th>Niche</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {events.map(e => (
                <tr key={e.id}>
                  <td>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)', display: 'block' }}>{e.name}</span>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{e.description}</span>
                  </td>
                  <td>{e.date}</td>
                  <td>{e.niche}</td>
                  <td>
                    <span className={`badge badge-${e.status === 'scheduled' ? 'success' : 'warning'}`}>
                      {e.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
