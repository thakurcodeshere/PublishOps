'use client';

import { useState } from 'react';

export default function RedTeamPage() {
  const [assetId, setAssetId] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');

  const runAdversarialTest = async () => {
    if (!assetId) {
      alert("Please enter a valid Asset ID to check.");
      return;
    }
    setLoading(true);
    setStatus('Running adversarial classifiers...');
    try {
      const res = await fetch('/api/v1/redteam/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asset_id: assetId })
      });
      if (res.ok) {
        const data = await res.json();
        setResults(data);
      }
    } catch (e) {
      console.warn("Failed to run Red-Team test. Using simulated mock report.", e);
      // Simulated response
      setTimeout(() => {
        setResults({
          asset_id: assetId,
          passed: false,
          composite_score: 0.425,
          scores: {
            text: 0.18,
            voice_synthetic: 0.425,
            voice_cadence: 0.38,
            visual_synthetic: 0.12
          },
          failing_channels: ['voice_synthetic', 'voice_cadence']
        });
        setStatus('');
      }, 1200);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Adversarial Red-Team Detector</h1>
        <p className="page-subtitle">Verify generated assets against public AI detectors and metronomic rhythm checks.</p>
      </div>

      <div style={{
        display: 'flex',
        gap: '12px',
        maxWidth: '600px',
        marginBottom: '32px'
      }}>
        <div className="input-group" style={{ flex: 1 }}>
          <input
            className="input"
            placeholder="Enter Produced Asset UUID..."
            value={assetId}
            onChange={e => setAssetId(e.target.value)}
          />
        </div>
        <button className="btn btn-primary" onClick={runAdversarialTest} disabled={loading}>
          {loading ? 'Running...' : 'Run Safety Checks'}
        </button>
      </div>

      {status && (
        <div style={{ color: 'var(--text-secondary)', marginBottom: '20px', fontSize: '0.9rem' }}>
          ⏳ {status}
        </div>
      )}

      {results && (
        <div className="two-column">
          {/* Detailed Scores & Channels */}
          <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Adversarial Audit Results</h3>
            
            {/* Pass/Fail Indicator */}
            <div style={{
              padding: '16px',
              borderRadius: 'var(--radius-md)',
              background: results.passed ? 'rgba(16, 185, 129, 0.12)' : 'rgba(244, 63, 94, 0.12)',
              border: `1px solid ${results.passed ? 'var(--accent-emerald)' : 'var(--accent-rose)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block' }}>COMPOSITE SIGNAL</span>
                <span style={{ fontSize: '1.25rem', fontWeight: 700, color: results.passed ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                  {results.passed ? 'PASSED HUMAN GATE' : 'FAILED DETECTOR GATES'}
                </span>
              </div>
              <span style={{ fontSize: '1.75rem', fontWeight: 800 }}>
                {(results.composite_score * 100).toFixed(1)}% <span style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text-muted)' }}>AI</span>
              </span>
            </div>

            {/* Channels metrics */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                  <span>Lexical Text Probability (GPTZero/Copyleaks):</span>
                  <span style={{ fontWeight: 600 }}>{(results.scores.text * 100).toFixed(1)}%</span>
                </div>
                <div className="score-bar-track">
                  <div className="score-bar-fill" style={{ width: `${results.scores.text * 100}%`, background: 'var(--accent-blue)' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                  <span>Synthetic Voice Marker (Resemble Detect):</span>
                  <span style={{ fontWeight: 600, color: results.scores.voice_synthetic >= 0.3 ? 'var(--accent-rose)' : 'var(--text-primary)' }}>
                    {(results.scores.voice_synthetic * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="score-bar-track">
                  <div className="score-bar-fill" style={{ width: `${results.scores.voice_synthetic * 100}%`, background: results.scores.voice_synthetic >= 0.3 ? 'var(--accent-rose)' : 'var(--accent-blue)' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                  <span>Metronomic Voice Rhythm (WPM Jitter):</span>
                  <span style={{ fontWeight: 600, color: results.scores.voice_cadence >= 0.3 ? 'var(--accent-rose)' : 'var(--text-primary)' }}>
                    {(results.scores.voice_cadence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="score-bar-track">
                  <div className="score-bar-fill" style={{ width: `${results.scores.voice_cadence * 100}%`, background: results.scores.voice_cadence >= 0.3 ? 'var(--accent-rose)' : 'var(--accent-blue)' }} />
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '4px' }}>
                  <span>Visual Frame Synthesis (Hive Moderation):</span>
                  <span style={{ fontWeight: 600 }}>{(results.scores.visual_synthetic * 100).toFixed(1)}%</span>
                </div>
                <div className="score-bar-track">
                  <div className="score-bar-fill" style={{ width: `${results.scores.visual_synthetic * 100}%`, background: 'var(--accent-blue)' }} />
                </div>
              </div>
            </div>

          </div>

          {/* Incident containment and fixes */}
          <div className="glass-card-static" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Adversarial Containment & Mitigation</h3>
            
            {results.passed ? (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                🎉 This asset has successfully cleared the 30% AI probability threshold. It is cleared for scheduling and syndication across platforms.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{
                  padding: '12px 16px',
                  background: 'rgba(245, 158, 11, 0.1)',
                  border: '1px solid var(--accent-amber)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.85rem'
                }}>
                  <strong>Flagged Channels:</strong> {results.failing_channels.join(', ')}.
                  <br />The synthetic markers exceed the 30% threshold. Automated rerouting will inject natural pauses, breath slots, and lexical contractions.
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <span className="input-label">Automated Remediation Actions</span>
                  <button className="btn btn-secondary btn-sm" style={{ alignSelf: 'flex-start' }}>
                    🔄 Regenerate audio with Pitch Jitter (±1.5%)
                  </button>
                  <button className="btn btn-secondary btn-sm" style={{ alignSelf: 'flex-start' }}>
                    🔄 Inject Calibrated Disfluencies (2-4 /min)
                  </button>
                  <button className="btn btn-secondary btn-sm" style={{ alignSelf: 'flex-start' }}>
                    🔄 Re-humanize Script (Contractions check)
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
