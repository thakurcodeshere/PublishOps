'use client';

import { useState } from 'react';
import HeatmapCalendar from '@/components/charts/HeatmapCalendar';
import Badge from '@/components/ui/Badge';
import { scheduledPosts, heatmapData } from '@/lib/mockData';

const platformColors = {
  YouTube: '#FF0000',
  TikTok: '#00f2ea',
  Instagram: '#E1306C',
  'Twitter/X': '#1DA1F2',
  LinkedIn: '#0A66C2',
};

const platformShort = {
  YouTube: 'YT',
  TikTok: 'TT',
  Instagram: 'IG',
  'Twitter/X': 'X',
  LinkedIn: 'LI',
};

export default function SchedulerClient() {
  const [selectedWeek, setSelectedWeek] = useState(0);

  // Build calendar days
  const today = new Date('2026-06-16');
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay() + 1 + (selectedWeek * 7));

  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(startOfWeek);
    d.setDate(startOfWeek.getDate() + i);
    return d;
  });

  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  const getPostsForDay = (date) => {
    return scheduledPosts.filter((p) => {
      const pd = new Date(p.scheduledFor);
      return pd.toDateString() === date.toDateString();
    });
  };

  const queueCounts = {
    queued: scheduledPosts.filter((p) => p.status === 'queued').length,
    pending: scheduledPosts.filter((p) => p.status === 'pending').length,
    completed: 64,
    failed: 1,
  };

  const formatTime = (iso) => {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (iso) => {
    const d = new Date(iso);
    const now = new Date('2026-06-16T12:00:00Z');
    const isToday = d.toDateString() === now.toDateString();
    const tomorrow = new Date(now);
    tomorrow.setDate(now.getDate() + 1);
    const isTomorrow = d.toDateString() === tomorrow.toDateString();
    if (isToday) return `Today ${formatTime(iso)}`;
    if (isTomorrow) return `Tomorrow ${formatTime(iso)}`;
    return `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })} ${formatTime(iso)}`;
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Upload Scheduler</h1>
        <p className="page-subtitle">Optimize posting times and manage your content queue</p>
      </div>

      {/* Queue Status */}
      <div className="queue-status" style={{ marginBottom: '28px' }}>
        <div className="queue-status-item animate-in" style={{ animationDelay: '0ms' }}>
          <div className="queue-status-value" style={{ color: 'var(--accent-blue)' }}>{queueCounts.queued}</div>
          <div className="queue-status-label">Queued</div>
        </div>
        <div className="queue-status-item animate-in" style={{ animationDelay: '80ms' }}>
          <div className="queue-status-value" style={{ color: 'var(--accent-amber)' }}>{queueCounts.pending}</div>
          <div className="queue-status-label">Pending</div>
        </div>
        <div className="queue-status-item animate-in" style={{ animationDelay: '160ms' }}>
          <div className="queue-status-value" style={{ color: 'var(--accent-emerald)' }}>{queueCounts.completed}</div>
          <div className="queue-status-label">Completed</div>
        </div>
        <div className="queue-status-item animate-in" style={{ animationDelay: '240ms' }}>
          <div className="queue-status-value" style={{ color: 'var(--accent-rose)' }}>{queueCounts.failed}</div>
          <div className="queue-status-label">Failed</div>
        </div>
      </div>

      {/* Heatmap */}
      <div className="glass-card-static animate-in" style={{ marginBottom: '28px' }}>
        <div className="section-header">
          <h2 className="section-title">Optimal Posting Windows</h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Based on historical engagement data</span>
        </div>
        <HeatmapCalendar data={heatmapData} />
      </div>

      {/* Weekly Calendar */}
      <div className="glass-card-static animate-in" style={{ marginBottom: '28px', animationDelay: '100ms' }}>
        <div className="section-header">
          <h2 className="section-title">Weekly Schedule</h2>
          <div className="btn-group">
            <button
              id="prev-week-btn"
              className="btn btn-ghost btn-sm"
              onClick={() => setSelectedWeek(selectedWeek - 1)}
            >
              ← Prev
            </button>
            <button
              id="current-week-btn"
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedWeek(0)}
            >
              This Week
            </button>
            <button
              id="next-week-btn"
              className="btn btn-ghost btn-sm"
              onClick={() => setSelectedWeek(selectedWeek + 1)}
            >
              Next →
            </button>
          </div>
        </div>

        <div className="calendar-grid">
          {dayNames.map((day) => (
            <div key={day} className="calendar-day-header">{day}</div>
          ))}
          {weekDays.map((date) => {
            const posts = getPostsForDay(date);
            const isToday = date.toDateString() === today.toDateString();
            return (
              <div key={date.toISOString()} className={`calendar-day ${isToday ? 'today' : ''}`}>
                <div className="calendar-day-number">{date.getDate()}</div>
                {posts.map((post) => (
                  <div
                    key={post.id}
                    className="calendar-event"
                    style={{ background: platformColors[post.platform] || '#666' }}
                    title={post.title}
                  >
                    {formatTime(post.scheduledFor)} {platformShort[post.platform]}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>

      {/* Upcoming Posts List */}
      <div className="glass-card-static animate-in" style={{ animationDelay: '200ms' }}>
        <div className="section-header">
          <h2 className="section-title">All Scheduled Posts</h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>{scheduledPosts.length} items</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {scheduledPosts.map((post) => (
            <div key={post.id} className="schedule-item">
              <div
                className="schedule-platform-icon"
                style={{ background: platformColors[post.platform] }}
              >
                {platformShort[post.platform]}
              </div>
              <div className="schedule-info">
                <div className="schedule-title">{post.title}</div>
                <div className="schedule-meta">{post.format}</div>
              </div>
              <Badge status={post.status} />
              <div className="schedule-time">{formatDate(post.scheduledFor)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
