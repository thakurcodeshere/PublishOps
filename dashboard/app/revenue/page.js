'use client';

import { useState } from 'react';

export default function RevenuePage() {
  const [stats, setStats] = useState({
    total_sales_usd: 12540.00,
    attributable_sales_usd: 8430.00,
    conversion_rate: '2.4%',
    clicks_tracked: 4210
  });

  const [topPerformingVariants, setTopPerformingVariants] = useState([
    { title: 'Conquering DB Connection Pools in SQLAlchemy', platform: 'YouTube', revenue: '$3,200', clicks: 1840 },
    { title: 'Why I hate manual scheduling tools', platform: 'TikTok', revenue: '$2,140', clicks: 920 },
    { title: 'Alembic async migrations cheatsheet', platform: 'Twitter/X', revenue: '$1,850', clicks: 880 }
  ]);

  const [webhooks, setWebhooks] = useState([
    { id: '1', gateway: 'Stripe', event: 'charge.succeeded', amount: '$49.00', time: '10 mins ago', status: 'processed' },
    { id: '2', gateway: 'Shopify', event: 'order/created', amount: '$120.00', time: '40 mins ago', status: 'processed' },
    { id: '3', gateway: 'Gumroad', event: 'sale', amount: '$29.00', time: '2 hours ago', status: 'processed' }
  ]);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Revenue Attribution Engine</h1>
        <p className="page-subtitle">Track UTM-tagged content posts directly to purchases recorded via Stripe, Shopify, and Gumroad webhooks.</p>
      </div>

      <div className="grid grid-cols-4" style={{ marginBottom: '32px' }}>
        <div className="glass-card-static">
          <span className="stat-label">Total Revenue (USD)</span>
          <span className="stat-value">${stats.total_sales_usd.toLocaleString()}</span>
        </div>
        <div className="glass-card-static">
          <span className="stat-label">Attributed Revenue</span>
          <span className="stat-value" style={{ color: 'var(--accent-emerald)' }}>${stats.attributable_sales_usd.toLocaleString()}</span>
        </div>
        <div className="glass-card-static">
          <span className="stat-label">Conversion Rate</span>
          <span className="stat-value">{stats.conversion_rate}</span>
        </div>
        <div className="glass-card-static">
          <span className="stat-label">Clicks Tracked</span>
          <span className="stat-value">{stats.clicks_tracked}</span>
        </div>
      </div>

      <div className="two-column">
        {/* Top revenue generating content */}
        <div className="glass-card-static">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '16px' }}>Top Performing Content (by Revenue)</h3>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Content Variant Title</th>
                  <th>Platform</th>
                  <th>Clicks</th>
                  <th>Revenue</th>
                </tr>
              </thead>
              <tbody>
                {topPerformingVariants.map((v, idx) => (
                  <tr key={idx}>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{v.title}</td>
                    <td>{v.platform}</td>
                    <td>{v.clicks}</td>
                    <td style={{ fontWeight: 700, color: 'var(--accent-emerald)' }}>{v.revenue}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Webhooks activity log */}
        <div className="glass-card-static">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '16px' }}>Recent Webhook Transactions</h3>
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Gateway</th>
                  <th>Event</th>
                  <th>Amount</th>
                  <th>Processed</th>
                </tr>
              </thead>
              <tbody>
                {webhooks.map(w => (
                  <tr key={w.id}>
                    <td>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{w.gateway}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block' }}>{w.time}</span>
                    </td>
                    <td>{w.event}</td>
                    <td>{w.amount}</td>
                    <td>
                      <span className="badge badge-success">{w.status}</span>
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
