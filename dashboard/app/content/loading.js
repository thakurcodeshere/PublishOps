export default function Loading() {
  return (
    <div className="loading-skeleton" style={{ animation: 'fadeIn 0.3s ease' }}>
      <div className="skeleton-block skeleton-title" />
      <div className="skeleton-block" style={{ height: '48px', borderRadius: 'var(--radius-md)' }} />
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(290px, 1fr))' }}>
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="skeleton-block" style={{ height: '260px', borderRadius: 'var(--radius-lg)' }} />
        ))}
      </div>
    </div>
  );
}
