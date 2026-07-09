export default function Loading() {
  return (
    <div className="loading-skeleton" style={{ animation: 'fadeIn 0.3s ease' }}>
      <div className="skeleton-block skeleton-title" />
      <div className="skeleton-block" style={{ height: '120px', borderRadius: 'var(--radius-md)' }} />
      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
        {[1, 2, 3, 4, 5, 6, 7].map((i) => (
          <div key={i} className="skeleton-block skeleton-card" />
        ))}
      </div>
      <div className="skeleton-block" style={{ height: '300px', borderRadius: 'var(--radius-md)' }} />
    </div>
  );
}
