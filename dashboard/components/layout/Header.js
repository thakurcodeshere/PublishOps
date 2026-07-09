'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';

const pageTitles = {
  '/': 'Dashboard',
  '/pipeline': 'Pipeline Monitor',
  '/topics': 'Topic Explorer',
  '/content': 'Content Library',
  '/analytics': 'Analytics',
  '/scheduler': 'Upload Scheduler',
  '/platforms': 'Platform Rules',
  '/settings': 'Settings',
};

export default function Header() {
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  const title = pageTitles[pathname] || 'Dashboard';

  return (
    <header
      id="dashboard-header"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        left: 'var(--sidebar-width)',
        height: 'var(--header-height)',
        background: 'rgba(10, 15, 30, 0.85)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--border-glass)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 32px',
        zIndex: 90,
        transition: 'left var(--transition-base)',
      }}
    >
      {/* Page Title */}
      <h1 style={{
        fontSize: '1.2rem',
        fontWeight: 700,
        letterSpacing: '-0.02em',
        color: 'var(--text-primary)',
      }}>
        {title}
      </h1>

      {/* Right Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Search */}
        <div
          id="header-search"
          style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-dim)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ position: 'absolute', left: '12px', pointerEvents: 'none' }}
          >
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
          </svg>
          <input
            type="text"
            placeholder="Search topics, content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input"
            style={{
              width: '260px',
              paddingLeft: '36px',
              background: 'var(--bg-glass)',
              border: '1px solid var(--border-glass)',
              height: '38px',
              fontSize: '0.82rem',
            }}
          />
        </div>

        {/* Notifications */}
        <div style={{ position: 'relative' }}>
          <button
            id="notification-bell"
            className="btn-icon"
            onClick={() => { setShowNotifications(!showNotifications); setShowUserMenu(false); }}
            style={{
              position: 'relative',
              color: 'var(--text-secondary)',
              padding: '8px',
              borderRadius: 'var(--radius-sm)',
              transition: 'all var(--transition-fast)',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-glass)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
            <span style={{
              position: 'absolute',
              top: '4px',
              right: '4px',
              width: '16px',
              height: '16px',
              borderRadius: '50%',
              background: 'var(--accent-rose)',
              color: 'white',
              fontSize: '0.6rem',
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              3
            </span>
          </button>

          {showNotifications && (
            <div
              id="notification-dropdown"
              style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '8px',
                width: '340px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-glass)',
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-lg)',
                overflow: 'hidden',
                animation: 'slideDown 0.2s ease',
                zIndex: 100,
              }}
            >
              <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-glass)', fontWeight: 600, fontSize: '0.85rem' }}>
                Notifications
              </div>
              {[
                { msg: 'Pipeline run #100 completed — 8 items processed', time: '2m ago', type: 'completed' },
                { msg: 'Assembly failed: FFmpeg timeout on "WebAssembly"', time: '15m ago', type: 'error' },
                { msg: '12 new trending topics discovered from Reddit', time: '30m ago', type: 'discovered' },
              ].map((n, i) => (
                <div key={i} style={{
                  padding: '12px 16px',
                  borderBottom: '1px solid var(--border-glass)',
                  display: 'flex',
                  gap: '10px',
                  alignItems: 'flex-start',
                  cursor: 'pointer',
                  transition: 'background var(--transition-fast)',
                }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-glass)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                >
                  <span className={`activity-dot ${n.type}`} style={{ marginTop: '6px' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>{n.msg}</div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '4px' }}>{n.time}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Run Pipeline Button */}
        <button
          id="run-pipeline-btn"
          className="btn btn-primary btn-sm"
          style={{ gap: '6px' }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          Run Pipeline
        </button>

        {/* User Avatar */}
        <div style={{ position: 'relative' }}>
          <button
            id="user-avatar-btn"
            onClick={() => { setShowUserMenu(!showUserMenu); setShowNotifications(false); }}
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: 'var(--gradient-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.8rem',
              fontWeight: 700,
              color: 'white',
              transition: 'box-shadow var(--transition-fast)',
              cursor: 'pointer',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow-glow)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'none'; }}
          >
            PO
          </button>

          {showUserMenu && (
            <div
              id="user-dropdown"
              style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '8px',
                width: '200px',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-glass)',
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-lg)',
                overflow: 'hidden',
                animation: 'slideDown 0.2s ease',
                zIndex: 100,
              }}
            >
              <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-glass)' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>PublishOps Admin</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>admin@publishops.io</div>
              </div>
              {['Profile', 'Preferences', 'API Keys', 'Log Out'].map((item) => (
                <button
                  key={item}
                  style={{
                    width: '100%',
                    padding: '10px 16px',
                    textAlign: 'left',
                    fontSize: '0.82rem',
                    color: item === 'Log Out' ? 'var(--accent-rose)' : 'var(--text-secondary)',
                    transition: 'all var(--transition-fast)',
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-glass)'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                >
                  {item}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
