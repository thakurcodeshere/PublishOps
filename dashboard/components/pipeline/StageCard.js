import Badge from '@/components/ui/Badge';

export default function StageCard({ stage, index }) {
  const isActive = stage.status === 'running';
  const timeAgo = (iso) => {
    if (!iso) return '—';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    return `${Math.floor(mins / 60)}h ago`;
  };

  return (
    <div className={`glass-card stage-card ${isActive ? 'active' : ''} animate-in`} style={{ animationDelay: `${index * 80}ms` }}>
      <div className="stage-card-header">
        <div className="stage-card-number">{stage.id}</div>
        <div className="stage-card-title">{stage.name}</div>
        <Badge status={stage.status} />
      </div>
      <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginBottom: '12px', lineHeight: 1.4 }}>
        {stage.description}
      </p>
      <div className="stage-card-metrics">
        <div className="stage-card-metric">
          <div className="stage-card-metric-value">{stage.processedCount}</div>
          <div className="stage-card-metric-label">Processed</div>
        </div>
        <div className="stage-card-metric">
          <div className="stage-card-metric-value" style={{ color: stage.errorCount > 0 ? 'var(--accent-rose)' : 'inherit' }}>
            {stage.errorCount}
          </div>
          <div className="stage-card-metric-label">Errors</div>
        </div>
        <div className="stage-card-metric">
          <div className="stage-card-metric-value">{stage.avgTime}</div>
          <div className="stage-card-metric-label">Avg Time</div>
        </div>
      </div>
      <div style={{
        marginTop: '12px',
        paddingTop: '12px',
        borderTop: '1px solid var(--border-glass)',
        fontSize: '0.72rem',
        color: 'var(--text-dim)',
      }}>
        Last run: {timeAgo(stage.lastRun)}
      </div>
    </div>
  );
}
