'use client';

import { useState } from 'react';

export default function HeatmapCalendar({ data, title = 'Posting Heatmap' }) {
  const [hoveredCell, setHoveredCell] = useState(null);
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const hours = Array.from({ length: 24 }, (_, i) => i);

  const maxCount = Math.max(...data.map((d) => d.count), 1);

  const getColor = (count) => {
    if (count === 0) return 'rgba(255,255,255,0.02)';
    const intensity = count / maxCount;
    if (intensity < 0.25) return 'rgba(59, 130, 246, 0.15)';
    if (intensity < 0.5) return 'rgba(59, 130, 246, 0.3)';
    if (intensity < 0.75) return 'rgba(59, 130, 246, 0.55)';
    return 'rgba(59, 130, 246, 0.85)';
  };

  const getCell = (day, hour) => data.find((d) => d.day === day && d.hour === hour);

  return (
    <div style={{ position: 'relative' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '40px repeat(24, 1fr)',
        gap: '2px',
        fontSize: '0.65rem',
      }}>
        {/* Header row */}
        <div />
        {hours.map((h) => (
          <div key={h} style={{
            textAlign: 'center',
            color: 'var(--text-dim)',
            padding: '4px 0',
            fontWeight: 500,
          }}>
            {h % 3 === 0 ? `${h}:00` : ''}
          </div>
        ))}

        {/* Data rows */}
        {days.map((day) => (
          <>
            <div key={`label-${day}`} className="heatmap-label" style={{ justifyContent: 'flex-end', paddingRight: '6px' }}>
              {day}
            </div>
            {hours.map((hour) => {
              const cell = getCell(day, hour);
              const count = cell ? cell.count : 0;
              const isHovered = hoveredCell && hoveredCell.day === day && hoveredCell.hour === hour;
              return (
                <div
                  key={`${day}-${hour}`}
                  className="heatmap-cell"
                  style={{
                    background: getColor(count),
                    height: '24px',
                    borderRadius: '3px',
                    border: isHovered ? '1px solid var(--accent-blue)' : '1px solid transparent',
                    position: 'relative',
                  }}
                  onMouseEnter={() => setHoveredCell({ day, hour, count })}
                  onMouseLeave={() => setHoveredCell(null)}
                />
              );
            })}
          </>
        ))}
      </div>

      {/* Tooltip */}
      {hoveredCell && (
        <div
          style={{
            position: 'fixed',
            zIndex: 1000,
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-glass)',
            borderRadius: 'var(--radius-sm)',
            padding: '8px 12px',
            boxShadow: 'var(--shadow-lg)',
            pointerEvents: 'none',
            fontSize: '0.8rem',
            top: '50%',
            left: '50%',
          }}
        >
          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
            {hoveredCell.day} at {hoveredCell.hour}:00
          </div>
          <div style={{ color: 'var(--text-secondary)', marginTop: '2px' }}>
            {hoveredCell.count} posts scheduled
          </div>
        </div>
      )}

      {/* Legend */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        marginTop: '12px',
        justifyContent: 'flex-end',
        fontSize: '0.7rem',
        color: 'var(--text-dim)',
      }}>
        <span>Less</span>
        {[0, 0.25, 0.5, 0.75, 1].map((intensity, i) => (
          <div
            key={i}
            style={{
              width: '14px',
              height: '14px',
              borderRadius: '3px',
              background: intensity === 0
                ? 'rgba(255,255,255,0.02)'
                : `rgba(59, 130, 246, ${intensity * 0.85})`,
            }}
          />
        ))}
        <span>More</span>
      </div>
    </div>
  );
}
