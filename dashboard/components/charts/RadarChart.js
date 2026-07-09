'use client';

import {
  Radar,
  RadarChart as RechartsRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

export default function RadarChartComponent({ data, height = 280 }) {
  return (
    <div className="chart-container" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsRadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
          <PolarGrid stroke="rgba(255,255,255,0.08)" />
          <PolarAngleAxis
            dataKey="axis"
            tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={{ fill: 'var(--text-dim)', fontSize: 10 }}
            axisLine={false}
          />
          <Radar
            name="Score"
            dataKey="value"
            stroke="#3b82f6"
            fill="url(#radarGrad)"
            fillOpacity={0.3}
            strokeWidth={2}
          />
          <defs>
            <linearGradient id="radarGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.5} />
              <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.2} />
            </linearGradient>
          </defs>
          <Tooltip
            contentStyle={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-glass)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8rem',
              color: 'var(--text-primary)',
            }}
          />
        </RechartsRadarChart>
      </ResponsiveContainer>
    </div>
  );
}
