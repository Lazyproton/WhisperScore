'use client';
import type { TimelineEvent } from '@/lib/types';
import { CATEGORY_COLORS, SEVERITY_COLORS, SEVERITY_LABELS, formatTime } from '@/lib/types';
import { Mic2, Brain, Eye, Clock } from 'lucide-react';

interface EventCardProps {
  event: TimelineEvent;
  active?: boolean;
  onClick?: () => void;
}

const CAT_ICONS: Record<string, React.ReactNode> = {
  voice:    <Mic2 size={14} />,
  content:  <Brain size={14} />,
  presence: <Eye size={14} />,
};

export default function EventCard({ event, active, onClick }: EventCardProps) {
  const catColor  = CATEGORY_COLORS[event.category];
  const sevColor  = SEVERITY_COLORS[event.severity];
  const sevLabel  = SEVERITY_LABELS[event.severity];

  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', gap: 14, padding: '14px 16px',
        borderRadius: 12, cursor: onClick ? 'pointer' : 'default',
        background: active ? 'rgba(79,158,248,0.08)' : 'transparent',
        border: active ? '1px solid rgba(79,158,248,0.25)' : '1px solid transparent',
        transition: 'all 0.15s ease',
      }}
      onMouseEnter={e => {
        if (!active) (e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.03)';
      }}
      onMouseLeave={e => {
        if (!active) (e.currentTarget as HTMLDivElement).style.background = 'transparent';
      }}
    >
      {/* Severity dot */}
      <div style={{ paddingTop: 3, flexShrink: 0 }}>
        <div style={{
          width: 10, height: 10, borderRadius: '50%',
          background: sevColor,
          boxShadow: `0 0 8px ${sevColor}80`,
          marginTop: 4,
        }} />
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
          {/* Timestamp */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4,
            color: 'var(--text-muted)', fontSize: 12, flexShrink: 0,
          }}>
            <Clock size={11} /> {formatTime(event.timestamp)}
          </div>

          {/* Category badge */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '2px 8px', borderRadius: 100,
            background: `${catColor}15`, color: catColor,
            fontSize: 11, fontWeight: 600,
          }}>
            {CAT_ICONS[event.category]}
            {event.category.charAt(0).toUpperCase() + event.category.slice(1)}
          </div>

          {/* Severity badge */}
          <div style={{
            padding: '2px 8px', borderRadius: 100,
            background: `${sevColor}15`, color: sevColor,
            fontSize: 11, fontWeight: 600,
          }}>
            {sevLabel}
          </div>
        </div>

        <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 3, color: 'var(--text-primary)' }}>
          {event.title}
        </div>
        <div style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.5 }}>
          {event.description}
        </div>

        {/* Score bar */}
        {event.score != null && (
          <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 3, background: 'rgba(255,255,255,0.07)', borderRadius: 2 }}>
              <div style={{
                height: '100%', borderRadius: 2,
                width: `${event.score}%`,
                background: sevColor,
                transition: 'width 0.6s ease',
              }} />
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>
              {Math.round(event.score)}/100
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
