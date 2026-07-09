export default function Badge({ status, label }) {
  const statusMap = {
    published: 'success',
    completed: 'success',
    connected: 'success',
    accepted: 'success',
    active: 'success',
    queued: 'info',
    scheduled: 'info',
    info: 'info',
    pending: 'warning',
    warning: 'warning',
    review: 'warning',
    scripting: 'processing',
    assembling: 'processing',
    voiceover: 'processing',
    running: 'processing',
    processing: 'processing',
    failed: 'error',
    error: 'error',
    rejected: 'error',
    idle: 'neutral',
    neutral: 'neutral',
  };

  const type = statusMap[status] || 'neutral';
  const displayLabel = label || status;

  return (
    <span className={`badge badge-${type}`}>
      <span className="badge-dot" />
      {displayLabel}
    </span>
  );
}
