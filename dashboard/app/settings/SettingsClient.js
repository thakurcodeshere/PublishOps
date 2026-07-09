'use client';

import { useState } from 'react';
import { settingsData } from '@/lib/mockData';

export default function SettingsClient() {
  const [weights, setWeights] = useState(settingsData.scoringWeights);
  const [prefs, setPrefs] = useState(settingsData.preferences);
  const [notifs, setNotifs] = useState(settingsData.notifications);
  const [saved, setSaved] = useState(false);

  const handleWeightChange = (key, value) => {
    const newVal = parseFloat(value);
    const others = Object.keys(weights).filter((k) => k !== key);
    const remaining = 1 - newVal;
    const currentOthersSum = others.reduce((s, k) => s + weights[k], 0);
    const newWeights = { ...weights, [key]: newVal };
    others.forEach((k) => {
      newWeights[k] = currentOthersSum > 0
        ? parseFloat((weights[k] / currentOthersSum * remaining).toFixed(2))
        : parseFloat((remaining / others.length).toFixed(2));
    });
    setWeights(newWeights);
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Configure your PublishOps pipeline and integrations</p>
        </div>
        <button
          id="save-settings-btn"
          className={`btn ${saved ? 'btn-success' : 'btn-primary'}`}
          onClick={handleSave}
        >
          {saved ? '✓ Saved!' : 'Save Changes'}
        </button>
      </div>

      {/* API Configuration */}
      <div className="settings-section animate-in">
        <h2 className="settings-section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          API Configuration
        </h2>
        <div className="settings-grid">
          {settingsData.apis.map((api) => (
            <div key={api.name} className="api-status-item">
              <span className={`api-status-dot ${api.status}`} />
              <span className="api-status-name">{api.name}</span>
              <span className="api-status-time">{api.lastChecked}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Scoring Weights */}
      <div className="settings-section animate-in" style={{ animationDelay: '100ms' }}>
        <h2 className="settings-section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-violet)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/></svg>
          Scoring Weights
        </h2>
        <div className="glass-card-static">
          <p style={{ fontSize: '0.82rem', color: 'var(--text-dim)', marginBottom: '20px' }}>
            Adjust the relative importance of each scoring dimension. Weights must sum to 1.0. Drag one slider and others will auto-adjust.
          </p>
          <div style={{ display: 'grid', gap: '20px' }}>
            {Object.entries(weights).map(([key, val]) => (
              <div key={key} className="slider-container">
                <div className="slider-header">
                  <span className="slider-label" style={{ textTransform: 'capitalize' }}>{key}</span>
                  <span className="slider-value">{val.toFixed(2)}</span>
                </div>
                <input
                  id={`weight-${key}`}
                  type="range"
                  min="0.05"
                  max="0.60"
                  step="0.01"
                  value={val}
                  onChange={(e) => handleWeightChange(key, e.target.value)}
                />
              </div>
            ))}
          </div>
          <div style={{
            marginTop: '16px',
            padding: '10px 14px',
            background: 'var(--bg-glass)',
            borderRadius: 'var(--radius-sm)',
            fontSize: '0.8rem',
            color: 'var(--text-muted)',
            display: 'flex',
            justifyContent: 'space-between',
          }}>
            <span>Total:</span>
            <span style={{
              fontWeight: 700,
              color: Math.abs(Object.values(weights).reduce((s, v) => s + v, 0) - 1) < 0.01
                ? 'var(--accent-emerald)'
                : 'var(--accent-rose)',
            }}>
              {Object.values(weights).reduce((s, v) => s + v, 0).toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Voice Settings */}
      <div className="settings-section animate-in" style={{ animationDelay: '150ms' }}>
        <h2 className="settings-section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>
          Voice Settings
        </h2>
        <div className="glass-card-static">
          <div className="input-group" style={{ marginBottom: '16px' }}>
            <label className="input-label">ElevenLabs Voice ID</label>
            <input
              id="voice-id-input"
              className="input"
              value={prefs.voiceId}
              onChange={(e) => setPrefs({ ...prefs, voiceId: e.target.value })}
              style={{ fontFamily: 'monospace', fontSize: '0.82rem' }}
            />
          </div>
          <div style={{
            padding: '16px',
            background: 'var(--bg-glass)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-glass)',
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
          }}>
            <button id="play-voice-sample" className="btn btn-secondary btn-sm" style={{ gap: '6px' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
              Play Sample
            </button>
            <div style={{ flex: 1 }}>
              <div style={{
                height: '32px',
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-xs)',
                display: 'flex',
                alignItems: 'center',
                gap: '2px',
                padding: '0 8px',
                overflow: 'hidden',
              }}>
                {Array.from({ length: 40 }).map((_, i) => (
                  <div
                    key={i}
                    style={{
                      width: '3px',
                      height: `${8 + Math.random() * 16}px`,
                      background: 'var(--accent-cyan)',
                      borderRadius: '2px',
                      opacity: 0.4,
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content Preferences */}
      <div className="settings-section animate-in" style={{ animationDelay: '200ms' }}>
        <h2 className="settings-section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
          Content Preferences
        </h2>
        <div className="glass-card-static">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="input-group">
              <label className="input-label">Niche / Topic Area</label>
              <input
                id="niche-input"
                className="input"
                value={prefs.niche}
                onChange={(e) => setPrefs({ ...prefs, niche: e.target.value })}
              />
            </div>
            <div className="input-group">
              <label className="input-label">Tone & Style</label>
              <input
                id="tone-input"
                className="input"
                value={prefs.tone}
                onChange={(e) => setPrefs({ ...prefs, tone: e.target.value })}
              />
            </div>
            <div className="input-group">
              <label className="input-label">Posts Per Day</label>
              <select
                id="posts-per-day"
                className="select"
                value={prefs.postsPerDay}
                onChange={(e) => setPrefs({ ...prefs, postsPerDay: Number(e.target.value) })}
              >
                {[1, 2, 3, 4, 5, 6, 8, 10].map((n) => (
                  <option key={n} value={n}>{n} posts/day</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="settings-section animate-in" style={{ animationDelay: '250ms' }}>
        <h2 className="settings-section-title">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-amber)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
          Notifications
        </h2>
        <div className="glass-card-static">
          <div className="input-group" style={{ marginBottom: '20px' }}>
            <label className="input-label">Slack Webhook URL</label>
            <input
              id="slack-webhook-input"
              className="input"
              value={notifs.slackWebhook}
              onChange={(e) => setNotifs({ ...notifs, slackWebhook: e.target.value })}
              style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}
            />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {[
              { key: 'emailAlerts', label: 'Email Alerts', desc: 'Receive email notifications for pipeline events' },
              { key: 'errorAlerts', label: 'Error Alerts', desc: 'Get notified immediately when pipeline stages fail' },
              { key: 'dailyDigest', label: 'Daily Digest', desc: 'Receive a daily summary of pipeline activity at 9 AM' },
            ].map((item) => (
              <div
                key={item.key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  background: 'var(--bg-glass)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-glass)',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '2px' }}>{item.label}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>{item.desc}</div>
                </div>
                <div
                  id={`toggle-${item.key}`}
                  className={`toggle ${notifs[item.key] ? 'active' : ''}`}
                  onClick={() => setNotifs({ ...notifs, [item.key]: !notifs[item.key] })}
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
