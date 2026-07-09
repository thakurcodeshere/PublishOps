export default function Loading() {
  return (
    <div className="loading-skeleton" style={{ animation: 'fadeIn 0.3s ease' }}>
      <div className="skeleton-block skeleton-title" />
      <div className="grid grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton-block" style={{ height: '80px', borderRadius: 'var(--radius-md)' }} />
        ))}
      </div>
      <div className="skeleton-block" style={{ height: '220px', borderRadius: 'var(--radius-md)' }} />
      <div className="skeleton-block" style={{ height: '300px', borderRadius: 'var(--radius-md)' }} />
    </div>
  );
}
