'use client';

import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload) return null;
  return (
    <div className="custom-tooltip">
      <div className="label">{label}</div>
      {payload.map((entry, i) => (
        <div key={i} className="value" style={{ color: entry.fill || entry.color }}>
          {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
        </div>
      ))}
    </div>
  );
};

export default function BarChartComponent({
  data,
  bars = [],
  xKey = 'name',
  height = 300,
  showGrid = true,
  colors = null,
}) {
  const defaultColors = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#f43f5e'];

  return (
    <div className="chart-container" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <RechartsBarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />}
          <XAxis
            dataKey={xKey}
            stroke="var(--text-dim)"
            fontSize={11}
            tickLine={false}
            axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
          />
          <YAxis
            stroke="var(--text-dim)"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          {bars.map((bar, i) => (
            <Bar
              key={bar.key}
              dataKey={bar.key}
              name={bar.name || bar.key}
              fill={bar.color || defaultColors[i % defaultColors.length]}
              radius={[4, 4, 0, 0]}
              maxBarSize={50}
            >
              {colors && data.map((entry, index) => (
                <Cell key={index} fill={entry.color || defaultColors[index % defaultColors.length]} />
              ))}
            </Bar>
          ))}
        </RechartsBarChart>
      </ResponsiveContainer>
    </div>
  );
}
