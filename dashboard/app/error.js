'use client';

export default function Error({ error, reset }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '60vh',
      gap: '20px',
      animation: 'fadeIn 0.5s ease',
    }}>
      <div style={{
        width: '80px',
        height: '80px',
        borderRadius: '50%',
        background: 'rgba(244, 63, 94, 0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '2px solid rgba(244, 63, 94, 0.3)',
      }}>
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--accent-rose)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <h2 style={{
        fontSize: '1.5rem',
        fontWeight: 700,
        color: 'var(--text-primary)',
      }}>
        Something went wrong
      </h2>
      <p style={{
        fontSize: '0.9rem',
        color: 'var(--text-secondary)',
        maxWidth: '400px',
        textAlign: 'center',
        lineHeight: 1.5,
      }}>
        {error?.message || 'An unexpected error occurred while loading this page. Please try again.'}
      </p>
      <button
        id="error-retry-btn"
        className="btn btn-primary"
        onClick={() => reset()}
      >
        Try Again
      </button>
    </div>
  );
}
