'use client';

import StatCard from '@/components/ui/StatCard';
import LineChart from '@/components/charts/LineChart';
import BarChart from '@/components/charts/BarChart';
import { analyticsData } from '@/lib/mockData';

export default function AnalyticsClient() {
  const { summary, daily, byPlatform, byFormat, feedbackWeights } = analyticsData;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Analytics</h1>
        <p className="page-subtitle">Cross-platform performance metrics and engagement insights</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-5" style={{ marginBottom: '28px' }}>
        <StatCard label="Total Views" value={summary.totalViews.value} trend={summary.totalViews.trend} icon="views" color="blue" delay={0} />
        <StatCard label="Avg CTR" value={summary.avgCTR.value} trend={summary.avgCTR.trend} icon="ctr" color="cyan" delay={80} />
        <StatCard label="Total Saves" value={summary.totalSaves.value} trend={summary.totalSaves.trend} icon="saves" color="violet" delay={160} />
        <StatCard label="Engagement Rate" value={summary.engagementRate.value} trend={summary.engagementRate.trend} icon="engagement" color="emerald" delay={240} />
        <StatCard label="Follower Growth" value={summary.followerGrowth.value} trend={summary.followerGrowth.trend} icon="growth" color="amber" delay={320} />
      </div>

      {/* Performance Over Time */}
      <div className="glass-card-static animate-in" style={{ marginBottom: '28px' }}>
        <div className="section-header">
          <h2 className="section-title">Performance Over 30 Days</h2>
          <div className="btn-group">
            <button className="btn btn-ghost btn-sm" style={{ color: 'var(--accent-blue)' }}>7D</button>
            <button className="btn btn-secondary btn-sm">30D</button>
            <button className="btn btn-ghost btn-sm">90D</button>
          </div>
        </div>
        <LineChart
          data={daily.map((d) => ({ ...d, date: d.date.slice(5) }))}
          lines={[
            { key: 'views', name: 'Views', color: '#3b82f6' },
            { key: 'engagement', name: 'Engagement', color: '#8b5cf6' },
            { key: 'saves', name: 'Saves', color: '#10b981' },
          ]}
          height={350}
        />
      </div>

      {/* Two Column: By Platform + By Format */}
      <div className="two-column" style={{ marginBottom: '28px' }}>
        <div className="glass-card-static animate-in" style={{ animationDelay: '100ms' }}>
          <h2 className="section-title" style={{ marginBottom: '16px' }}>Performance by Platform</h2>
          <BarChart
            data={byPlatform}
            bars={[{ key: 'views', name: 'Views' }]}
            xKey="platform"
            colors={true}
            height={280}
          />
        </div>
        <div className="glass-card-static animate-in" style={{ animationDelay: '200ms' }}>
          <h2 className="section-title" style={{ marginBottom: '16px' }}>Performance by Format</h2>
          <BarChart
            data={byFormat}
            bars={[
              { key: 'views', name: 'Views', color: '#3b82f6' },
              { key: 'engagement', name: 'Engagement', color: '#8b5cf6' },
            ]}
            xKey="format"
            height={280}
          />
        </div>
      </div>

      {/* Feedback Loop */}
      <div className="glass-card-static animate-in" style={{ animationDelay: '300ms' }}>
        <div className="section-header">
          <h2 className="section-title">🔄 Feedback Loop — Weight Adjustments Over Time</h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Auto-optimizing scoring weights based on performance data</span>
        </div>
        <LineChart
          data={feedbackWeights}
          lines={[
            { key: 'velocity', name: 'Velocity', color: '#3b82f6' },
            { key: 'evergreen', name: 'Evergreen', color: '#10b981' },
            { key: 'fit', name: 'Platform Fit', color: '#8b5cf6' },
            { key: 'saturation', name: 'Saturation', color: '#f59e0b' },
          ]}
          xKey="week"
          height={260}
        />
        <div style={{
          marginTop: '16px',
          padding: '14px 16px',
          background: 'rgba(59, 130, 246, 0.05)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid rgba(59, 130, 246, 0.1)',
          fontSize: '0.82rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.5,
        }}>
          <strong style={{ color: 'var(--accent-blue)' }}>Insight:</strong> Platform Fit weight has increased from 0.25 → 0.31 over 6 weeks, indicating the algorithm is learning that format-specific optimization drives higher engagement. Saturation penalty is decreasing as our content uniqueness improves.
        </div>
      </div>
    </div>
  );
}
