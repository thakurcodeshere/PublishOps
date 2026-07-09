export default function Loading() {
  return (
    <div className="loading-skeleton" style={{ animation: 'fadeIn 0.3s ease' }}>
      <div className="grid grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton-block skeleton-stat" />
        ))}
      </div>
      <div className="skeleton-block skeleton-card" style={{ height: '400px' }} />
      <div className="two-column">
        <div className="skeleton-block skeleton-card" />
        <div className="skeleton-block skeleton-card" />
      </div>
      <div className="skeleton-block skeleton-card" style={{ height: '250px' }} />
    </div>
  );
}
