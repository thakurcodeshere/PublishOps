export default function Loading() {
  return (
    <div className="loading-skeleton" style={{ animation: 'fadeIn 0.3s ease' }}>
      <div className="skeleton-block skeleton-title" />
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="skeleton-block" style={{ height: '180px', borderRadius: 'var(--radius-md)' }} />
      ))}
    </div>
  );
}
