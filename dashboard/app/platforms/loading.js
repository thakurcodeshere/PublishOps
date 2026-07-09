export default function Loading() {
  return (
    <div className="loading-skeleton" style={{ animation: 'fadeIn 0.3s ease' }}>
      <div className="skeleton-block skeleton-title" />
      <div className="skeleton-block" style={{ height: '48px', borderRadius: 'var(--radius-md)' }} />
      <div className="skeleton-block" style={{ height: '300px', borderRadius: 'var(--radius-md)' }} />
      <div className="two-column">
        <div className="skeleton-block" style={{ height: '250px', borderRadius: 'var(--radius-md)' }} />
        <div className="skeleton-block" style={{ height: '250px', borderRadius: 'var(--radius-md)' }} />
      </div>
    </div>
  );
}
