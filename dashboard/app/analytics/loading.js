export default function Loading() {
  return (
    <div className="loading-skeleton" style={{ animation: 'fadeIn 0.3s ease' }}>
      <div className="skeleton-block skeleton-title" />
      <div className="grid grid-cols-5">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="skeleton-block skeleton-stat" />
        ))}
      </div>
      <div className="skeleton-block" style={{ height: '350px', borderRadius: 'var(--radius-md)' }} />
      <div className="two-column">
        <div className="skeleton-block" style={{ height: '280px', borderRadius: 'var(--radius-md)' }} />
        <div className="skeleton-block" style={{ height: '280px', borderRadius: 'var(--radius-md)' }} />
      </div>
    </div>
  );
}
