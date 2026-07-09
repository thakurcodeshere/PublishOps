'use client';

import { useState } from 'react';
import { platformRules } from '@/lib/mockData';

const platformKeys = ['youtube', 'tiktok', 'instagram', 'twitter', 'linkedin'];
const tabLabels = { youtube: 'YouTube', tiktok: 'TikTok', instagram: 'Instagram', twitter: 'Twitter/X', linkedin: 'LinkedIn' };

const weightColors = {
  'Very High': 'var(--accent-rose)',
  'High': 'var(--accent-amber)',
  'Medium': 'var(--accent-blue)',
  'Low': 'var(--text-dim)',
};

export default function PlatformsClient() {
  const [activeTab, setActiveTab] = useState('youtube');
  const platform = platformRules[activeTab];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Platform Rules</h1>
        <p className="page-subtitle">Algorithm signals, format specs, and optimization strategies per platform</p>
      </div>

      {/* Tabs */}
      <div className="tabs" style={{ marginBottom: '28px' }}>
        {platformKeys.map((key) => (
          <button
            key={key}
            id={`tab-${key}`}
            className={`tab ${activeTab === key ? 'active' : ''}`}
            onClick={() => setActiveTab(key)}
            style={{
              borderBottom: activeTab === key ? `2px solid ${platformRules[key].color}` : 'none',
            }}
          >
            {tabLabels[key]}
          </button>
        ))}
      </div>

      {/* Platform Content */}
      <div style={{ animation: 'fadeIn 0.3s ease' }} key={activeTab}>
        {/* Algorithm Signals */}
        <div className="glass-card-static animate-in" style={{ marginBottom: '24px' }}>
          <h2 className="section-title" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: platform.color,
              display: 'inline-block',
            }} />
            Algorithm Signals — {platform.name}
          </h2>
          <div className="data-table-container" style={{ padding: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Signal</th>
                  <th>Weight</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {platform.signals.map((s, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.signal}</td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          color: weightColors[s.weight],
                          background: `${weightColors[s.weight]}15`,
                          border: `1px solid ${weightColors[s.weight]}30`,
                        }}
                      >
                        {s.weight}
                      </span>
                    </td>
                    <td>{s.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Format Specs + Optimal Hours */}
        <div className="two-column" style={{ marginBottom: '24px' }}>
          {/* Format Specs */}
          <div className="glass-card-static animate-in" style={{ animationDelay: '100ms' }}>
            <h2 className="section-title" style={{ marginBottom: '16px' }}>Format Specifications</h2>
            {Object.entries(platform.formats).map(([format, specs]) => (
              <div key={format} style={{
                padding: '14px 16px',
                background: 'var(--bg-glass)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-glass)',
                marginBottom: '10px',
              }}>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9rem', marginBottom: '8px', textTransform: 'capitalize' }}>
                  {format.replace(/([A-Z])/g, ' $1').trim()}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  {Object.entries(specs).map(([key, val]) => (
                    <div key={key}>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textTransform: 'capitalize' }}>
                        {key.replace(/([A-Z])/g, ' $1').trim()}
                      </span>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--accent-blue)' }}>{val}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Optimal Hours */}
          <div className="glass-card-static animate-in" style={{ animationDelay: '200ms' }}>
            <h2 className="section-title" style={{ marginBottom: '16px' }}>Optimal Posting Windows</h2>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' }}>
              {Array.from({ length: 24 }, (_, h) => {
                const isOptimal = platform.optimalHours.includes(h);
                return (
                  <div
                    key={h}
                    style={{
                      width: '44px',
                      height: '44px',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.75rem',
                      fontWeight: isOptimal ? 700 : 400,
                      background: isOptimal ? `${platform.color}25` : 'var(--bg-glass)',
                      color: isOptimal ? platform.color : 'var(--text-dim)',
                      border: `1px solid ${isOptimal ? `${platform.color}40` : 'var(--border-glass)'}`,
                      transition: 'all var(--transition-fast)',
                    }}
                  >
                    {h}:00
                  </div>
                );
              })}
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
              ⏰ Highlighted hours show the best posting windows based on audience engagement patterns.
            </div>
          </div>
        </div>

        {/* Platform Tips */}
        <div className="glass-card-static animate-in" style={{ animationDelay: '300ms' }}>
          <h2 className="section-title" style={{ marginBottom: '16px' }}>💡 Optimization Tips</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {platform.tips.map((tip, i) => (
              <div key={i} className="tip-item">
                <span className="tip-bullet" style={{ background: platform.color }} />
                <span>{tip}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
