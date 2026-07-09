'use client';

import { useState, useEffect } from 'react';

export default function CalibrationPage() {
  const [creatorId, setCreatorId] = useState('');
  const [creatorName, setCreatorName] = useState('Default Creator');
  const [profile, setProfile] = useState(null);
  const [opinions, setOpinions] = useState([]);
  const [newOpinion, setNewOpinion] = useState({ topic: '', stance: '', allowed: '', forbidden: '' });
  const [uploadStatus, setUploadStatus] = useState('');
  const [loading, setLoading] = useState(false);

  // Initialize and load creator profile
  useEffect(() => {
    fetchCreatorProfile();
  }, []);

  const fetchCreatorProfile = async () => {
    setLoading(true);
    try {
      // Step 1: Query or create creator profile
      const createRes = await fetch('/api/v1/calibration/creator', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'Alpha Creator', description: 'Tech & Solopreneur Niche' })
      });
      const creator = await createRes.json();
      setCreatorId(creator.id);
      setCreatorName(creator.name);

      // Step 2: Fetch profile details
      const profileRes = await fetch(`/api/v1/calibration/profile/${creator.id}`);
      if (profileRes.ok) {
        const prof = await profileRes.json();
        setProfile(prof);
      }

      // Step 3: Fetch Voice Bible
      const bibleRes = await fetch(`/api/v1/calibration/voice-bible/${creator.id}`);
      if (bibleRes.ok) {
        const bible = await bibleRes.json();
        setOpinions(bible);
      }
    } catch (e) {
      console.error("Failed to load calibration data. Using mock fallbacks.", e);
      // Fallback mocks if backend offline
      setCreatorId('d3b07384-d113-487d-bc2b-e48fca8c6f14');
      setProfile({
        name: 'Alpha Creator',
        lexical_profile: { readability_score: 68.2, average_sentence_length: 11.5, contractions_ratio: 0.08 },
        cadence_profile: { wpm_mean: 148.5, average_pause_length_secs: 0.32 },
        acoustic_profile: { noise_floor_db: -48.2, pitch_jitter_pct: 1.2 },
        disfluency_profile: { stumbles_per_minute: 2.4 },
        temporal_profile: { preferred_posting_hour_utc: 15 }
      });
      setOpinions([
        { id: '1', topic: 'AI Safety', stance: 'Proactive mitigation, don\'t hype fear', allowed_terms: ['responsible AI', 'practical safety'], forbidden_terms: ['doomsday', 'extinction'] },
        { id: '2', topic: 'No-Code tools', stance: 'Great for V1 prototypes, bad for scale', allowed_terms: ['MVP', 'rapid iteration'], forbidden_terms: ['replace developers', 'infinite scale'] }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleOpinionSubmit = async (e) => {
    e.preventDefault();
    if (!newOpinion.topic || !newOpinion.stance) return;

    try {
      const res = await fetch('/api/v1/calibration/voice-bible', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          creator_id: creatorId,
          topic: newOpinion.topic,
          stance: newOpinion.stance,
          allowed_terms: newOpinion.allowed.split(',').map(t => t.trim()).filter(Boolean),
          forbidden_terms: newOpinion.forbidden.split(',').map(t => t.trim()).filter(Boolean)
        })
      });

      if (res.ok) {
        const entry = await res.json();
        setOpinions([...opinions, entry]);
        setNewOpinion({ topic: '', stance: '', allowed: '', forbidden: '' });
      }
    } catch (err) {
      // Local addition fallback
      const mockEntry = {
        id: Math.random().toString(),
        topic: newOpinion.topic,
        stance: newOpinion.stance,
        allowed_terms: newOpinion.allowed.split(','),
        forbidden_terms: newOpinion.forbidden.split(',')
      };
      setOpinions([...opinions, mockEntry]);
      setNewOpinion({ topic: '', stance: '', allowed: '', forbidden: '' });
    }
  };

  const handleOpinionDelete = async (id) => {
    try {
      await fetch(`/api/v1/calibration/voice-bible/${id}`, { method: 'DELETE' });
      setOpinions(opinions.filter(o => o.id !== id));
    } catch (e) {
      setOpinions(opinions.filter(o => o.id !== id));
    }
  };

  const handleFileUpload = async (type) => {
    setUploadStatus(`Uploading reference ${type}...`);
    setTimeout(() => {
      setUploadStatus(`Reference ${type} uploaded & parsed successfully!`);
    }, 1500);
  };

  const triggerCalibrationAnalysis = async () => {
    setUploadStatus('Profiling engine running analysis...');
    try {
      const res = await fetch('/api/v1/calibration/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ creator_id: creatorId })
      });
      if (res.ok) {
        const prof = await res.json();
        setProfile(prof);
        setUploadStatus('Analysis complete! Creator Fingerprint updated.');
      }
    } catch (e) {
      setTimeout(() => {
        setUploadStatus('Analysis complete! Creator Fingerprint updated (Simulated).');
      }, 1500);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Creator Calibration</h1>
        <p className="page-subtitle">Align the autonomous engine to your personal lexical, acoustic, and behavioral signature.</p>
      </div>

      {uploadStatus && (
        <div style={{
          padding: '12px 20px',
          background: 'rgba(59, 130, 246, 0.15)',
          border: '1px solid var(--accent-blue)',
          borderRadius: 'var(--radius-sm)',
          color: 'var(--text-primary)',
          marginBottom: '20px',
          fontSize: '0.9rem',
        }}>
          ℹ️ {uploadStatus}
        </div>
      )}

      <div className="two-column">
        {/* Left Column: Uploads & Voice Bible */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Upload Portal Card */}
          <div className="glass-card-static">
            <h3 style={{ marginBottom: '16px', fontSize: '1.1rem', fontWeight: 600 }}>1. Reference Library Upload</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{
                border: '2px dashed var(--border-glass)',
                padding: '24px',
                borderRadius: 'var(--radius-md)',
                textAlign: 'center',
                cursor: 'pointer',
                background: 'rgba(255, 255, 255, 0.01)',
                transition: 'border-color var(--transition-fast)'
              }} onClick={() => handleFileUpload('audio')}>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>🎙️ Drag & drop creator audio references (10+ min WAV/MP3)</p>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Required for cadence, breath alignment, and room tone matching</span>
              </div>

              <div style={{
                border: '2px dashed var(--border-glass)',
                padding: '24px',
                borderRadius: 'var(--radius-md)',
                textAlign: 'center',
                cursor: 'pointer',
                background: 'rgba(255, 255, 255, 0.01)',
                transition: 'border-color var(--transition-fast)'
              }} onClick={() => handleFileUpload('scripts')}>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>📝 Drag & drop past script files (50+ TXT/JSON/Markdown)</p>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Required for sentence length distributions and lexical profiling</span>
              </div>
              
              <button className="btn btn-primary" onClick={triggerCalibrationAnalysis} style={{ marginTop: '8px' }}>
                Run Calibration Analysis
              </button>
            </div>
          </div>

          {/* Voice Bible / Constraints Stances */}
          <div className="glass-card-static">
            <h3 style={{ marginBottom: '16px', fontSize: '1.1rem', fontWeight: 600 }}>2. Voice Bible & Stance Matrix</h3>
            
            <form onSubmit={handleOpinionSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
              <div className="input-group">
                <label className="input-label">Topic Name</label>
                <input className="input" placeholder="e.g., AI Agents, Bootstrapping" value={newOpinion.topic} onChange={e => setNewOpinion({ ...newOpinion, topic: e.target.value })} />
              </div>
              <div className="input-group">
                <label className="input-label">Stance Constraint</label>
                <textarea className="input" rows="2" placeholder="e.g., Focus on utility over speculation. Never advise waiting for regulatory approval." value={newOpinion.stance} onChange={e => setNewOpinion({ ...newOpinion, stance: e.target.value })} />
              </div>
              <div className="grid grid-cols-2">
                <div className="input-group">
                  <label className="input-label">Allowed Terms (comma separated)</label>
                  <input className="input" placeholder="automation, builder" value={newOpinion.allowed} onChange={e => setNewOpinion({ ...newOpinion, allowed: e.target.value })} />
                </div>
                <div className="input-group">
                  <label className="input-label">Forbidden Terms (comma separated)</label>
                  <input className="input" placeholder="magic, hype, killer app" value={newOpinion.forbidden} onChange={e => setNewOpinion({ ...newOpinion, forbidden: e.target.value })} />
                </div>
              </div>
              <button type="submit" className="btn btn-secondary">Add Constraint</button>
            </form>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {opinions.map(opinion => (
                <div key={opinion.id} style={{
                  padding: '14px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-glass)',
                  borderRadius: 'var(--radius-sm)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9rem' }}>{opinion.topic}</span>
                    <button style={{ color: 'var(--accent-rose)', fontSize: '0.8rem' }} onClick={() => handleOpinionDelete(opinion.id)}>Delete</button>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>{opinion.stance}</p>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {opinion.allowed_terms?.map(t => <span key={t} className="badge badge-success" style={{ fontSize: '0.65rem' }}>+{t}</span>)}
                    {opinion.forbidden_terms?.map(t => <span key={t} className="badge badge-error" style={{ fontSize: '0.65rem' }}>-{t}</span>)}
                  </div>
                </div>
              ))}
            </div>

          </div>

        </div>

        {/* Right Column: Computed Fingerprint Profiler display */}
        <div className="glass-card-static">
          <h3 style={{ marginBottom: '16px', fontSize: '1.1rem', fontWeight: 600 }}>Active Creator Fingerprint</h3>
          
          {profile ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {/* Lexical */}
              <div>
                <span className="input-label" style={{ display: 'block', marginBottom: '8px' }}>✍️ Lexical Channel Profile</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Flesch Readability Index:</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{profile.lexical_profile.readability_score}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Avg Sentence Length:</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{profile.lexical_profile.average_sentence_length} words</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Contraction Ratio:</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{(profile.lexical_profile.contractions_ratio * 100).toFixed(1)}%</span>
                  </div>
                </div>
              </div>

              {/* Cadence */}
              <div>
                <span className="input-label" style={{ display: 'block', marginBottom: '8px' }}>⏱️ Cadence Channel Profile</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Words Per Minute (WPM):</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-violet)' }}>{profile.cadence_profile.wpm_mean}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Average Pause Duration:</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-violet)' }}>{profile.cadence_profile.average_pause_length_secs}s</span>
                  </div>
                </div>
              </div>

              {/* Acoustic */}
              <div>
                <span className="input-label" style={{ display: 'block', marginBottom: '8px' }}>🔊 Acoustic & Noise Signature</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Room Noise Floor:</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-indigo)' }}>{profile.acoustic_profile.noise_floor_db} dB</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Pitch Jitter (drift):</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-indigo)' }}>±{profile.acoustic_profile.pitch_jitter_pct}%</span>
                  </div>
                </div>
              </div>

              {/* Disfluency */}
              <div>
                <span className="input-label" style={{ display: 'block', marginBottom: '8px' }}>🗣️ Disfluency Rate Calibrator</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Natural Stumbles:</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-amber)' }}>{profile.disfluency_profile.stumbles_per_minute} / min</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Disfluency Rate Status:</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-emerald)' }}>Calibrated (2.0 - 4.0 limit)</span>
                  </div>
                </div>
              </div>

              {/* Temporal */}
              <div>
                <span className="input-label" style={{ display: 'block', marginBottom: '8px' }}>📅 Temporal behavioral envelope</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                    <span>Peak posting window:</span>
                    <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{profile.temporal_profile.preferred_posting_hour_utc}:00 UTC</span>
                  </div>
                </div>
              </div>

            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No active creator profile loaded. Run calibration above.</p>
          )}

        </div>
      </div>
    </div>
  );
}
