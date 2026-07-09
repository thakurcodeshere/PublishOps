'use client';

import StatCard from '@/components/ui/StatCard';
import PipelineRing from '@/components/pipeline/PipelineRing';
import { pipelineStages, recentActivity, topPerformers, upcomingSchedule } from '@/lib/mockData';

const platformColors = {
  YouTube: '#FF0000',
  TikTok: '#00f2ea',
  Instagram: '#E1306C',
  'Twitter/X': '#1DA1F2',
  LinkedIn: '#0A66C2',
};

function formatViews(n) {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toString();
}

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function DashboardClient() {
  return (
    <div>
      {/* Stats Row */}
      <div className="grid grid-cols-4" style={{ marginBottom: '28px' }}>
        <StatCard label="Active Topics" value="34" trend={12.5} icon="topics" color="blue" delay={0} />
        <StatCard label="Content Buffer" value="72 hrs" trend={8.3} icon="buffer" color="emerald" delay={80} />
        <StatCard label="Today's Posts" value="11" trend={-2.1} icon="posts" color="violet" delay={160} />
        <StatCard label="Weekly Engagement" value="24.8K" trend={18.7} icon="engagement" color="rose" delay={240} />
      </div>

      {/* Pipeline Ring */}
      <div className="glass-card-static animate-in" style={{ marginBottom: '28px', padding: '20px', textAlign: 'center' }}>
        <div className="section-header" style={{ marginBottom: '8px' }}>
          <h2 className="section-title">Pipeline Status</h2>
          <span className="badge badge-processing">
            <span className="badge-dot" />
            Stage 3 Active
          </span>
        </div>
        <PipelineRing stages={pipelineStages} />
      </div>

      {/* Two Column: Schedule + Top Performers */}
      <div className="two-column" style={{ marginBottom: '28px' }}>
        {/* Upcoming Schedule */}
        <div className="glass-card-static animate-in" style={{ animationDelay: '100ms' }}>
          <div className="section-header">
            <h2 className="section-title">Upcoming Schedule</h2>
            <span className="section-action">View All →</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {upcomingSchedule.map((item, i) => (
              <div key={i} className="schedule-item">
                <div
                  className="schedule-platform-icon"
                  style={{ background: platformColors[item.platform] || '#666' }}
                >
                  {item.platform === 'YouTube' && 'YT'}
                  {item.platform === 'TikTok' && 'TT'}
                  {item.platform === 'Instagram' && 'IG'}
                  {item.platform === 'Twitter/X' && 'X'}
                  {item.platform === 'LinkedIn' && 'LI'}
                </div>
                <div className="schedule-info">
                  <div className="schedule-title">{item.title}</div>
                  <div className="schedule-meta">{item.format} · {item.platform}</div>
                </div>
                <div className="schedule-time">{item.time}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Performers */}
        <div className="glass-card-static animate-in" style={{ animationDelay: '200ms' }}>
          <div className="section-header">
            <h2 className="section-title">Top Performers</h2>
            <span className="section-action">Analytics →</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {topPerformers.map((item, i) => (
              <div key={i} className="performer-item">
                <div className={`performer-rank ${i < 3 ? 'top' : ''}`}>{i + 1}</div>
                <div className="performer-info">
                  <div className="performer-title">{item.title}</div>
                  <div className="performer-platform">{item.platform}</div>
                </div>
                <div className="performer-stat">
                  <div className="performer-views">{formatViews(item.views)}</div>
                  <div className="performer-engagement">{item.engagement}% eng</div>
                </div>
                {/* Mini sparkline */}
                <svg width="60" height="24" viewBox="0 0 60 24" style={{ flexShrink: 0 }}>
                  <polyline
                    points={item.sparkline.map((v, j) => `${j * 10},${24 - (v / Math.max(...item.sparkline)) * 20}`).join(' ')}
                    fill="none"
                    stroke="var(--accent-emerald)"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="glass-card-static animate-in" style={{ animationDelay: '300ms' }}>
        <div className="section-header">
          <h2 className="section-title">Recent Activity</h2>
          <span className="section-action">View Pipeline →</span>
        </div>
        <div className="activity-feed">
          {recentActivity.map((item) => (
            <div key={item.id} className="activity-item">
              <span className={`activity-dot ${item.type}`} />
              <span className="activity-message">{item.message}</span>
              <span className="activity-time">{timeAgo(item.timestamp)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
