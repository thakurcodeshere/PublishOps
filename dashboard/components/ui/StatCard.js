export default function StatCard({ label, value, trend, icon, color = 'var(--accent-blue)', delay = 0 }) {
  const isUp = trend >= 0;
  const gradients = {
    blue: 'linear-gradient(135deg, #3b82f6, #6366f1)',
    violet: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
    emerald: 'linear-gradient(135deg, #10b981, #06b6d4)',
    amber: 'linear-gradient(135deg, #f59e0b, #f97316)',
    rose: 'linear-gradient(135deg, #f43f5e, #ec4899)',
    cyan: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
  };
  const bg = gradients[color] || gradients.blue;

  const icons = {
    topics: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>,
    buffer: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>,
    posts: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20V10"/><path d="M18 20V4"/><path d="M6 20v-4"/></svg>,
    engagement: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>,
    views: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>,
    ctr: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 16 16 12 12 8"/><line x1="8" y1="12" x2="16" y2="12"/></svg>,
    saves: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg>,
    growth: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/></svg>,
  };

  return (
    <div
      className="glass-card stat-card animate-in"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="stat-icon" style={{ background: bg }}>
        {icons[icon] || icons.topics}
      </div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className={`stat-trend ${isUp ? 'up' : 'down'}`}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ transform: isUp ? 'none' : 'rotate(180deg)' }}>
          <path d="m18 15-6-6-6 6" />
        </svg>
        {Math.abs(trend)}%
        <span style={{ color: 'var(--text-dim)', fontWeight: 400, marginLeft: '4px' }}>vs last week</span>
      </div>
      <div className="stat-glow" style={{ background: bg }} />
    </div>
  );
}
