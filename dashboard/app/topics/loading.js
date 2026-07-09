export default function Loading() {
  return (
    <div className="loading-skeleton" style={{ animation: 'fadeIn 0.3s ease' }}>
      <div className="skeleton-block skeleton-title" />
      <div className="skeleton-block" style={{ height: '48px', borderRadius: 'var(--radius-md)' }} />
      <div className="skeleton-row-container">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="skeleton-block skeleton-row" style={{ borderRadius: 'var(--radius-sm)' }} />
        ))}
      </div>
    </div>
  );
}
