'use client';
import { useState } from 'react';
import type { TimelineEvent, EventCategory } from '@/lib/types';
import { CATEGORY_COLORS, formatTime } from '@/lib/types';
import EventCard from './EventCard';
import { Filter } from 'lucide-react';

interface Props {
  events: TimelineEvent[];
  duration: number;
  currentTime: number;
  onSeek: (t: number) => void;
}

const CATEGORIES: { key: EventCategory | 'all'; label: string }[] = [
  { key: 'all',     label: 'All' },
  { key: 'voice',   label: 'Voice' },
  { key: 'content', label: 'Content' },
  { key: 'presence',label: 'Presence' },
];

export default function InteractiveTimeline({ events, duration, currentTime, onSeek }: Props) {
  const [filter, setFilter] = useState<EventCategory | 'all'>('all');

  const filtered = filter === 'all' ? events : events.filter(e => e.category === filter);
  const activeIdx = filtered.reduce((best, e, i) =>
    e.timestamp <= currentTime && e.timestamp > (filtered[best]?.timestamp ?? -1) ? i : best, 0);

  return (
    <div className="glass" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        padding: '18px 20px 14px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Filter size={16} color="var(--text-muted)" />
          <span style={{ fontSize: 14, fontWeight: 600 }}>Timeline</span>
          <span style={{
            padding: '2px 8px', borderRadius: 100,
            background: 'rgba(255,255,255,0.06)',
            fontSize: 12, color: 'var(--text-muted)',
          }}>{filtered.length} events</span>
        </div>
        {/* Category filters */}
        <div style={{ display: 'flex', gap: 6 }}>
          {CATEGORIES.map(c => {
            const active = filter === c.key;
            const color = c.key === 'all' ? '#8b99b8' : CATEGORY_COLORS[c.key as EventCategory];
            return (
              <button
                key={c.key}
                onClick={() => setFilter(c.key)}
                style={{
                  padding: '4px 12px', borderRadius: 100, fontSize: 12, fontWeight: 600,
                  cursor: 'pointer', border: 'none', transition: 'all 0.15s',
                  background: active ? `${color}20` : 'transparent',
                  color: active ? color : 'var(--text-muted)',
                  outline: active ? `1px solid ${color}40` : '1px solid transparent',
                }}
              >
                {c.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Progress scrubber */}
      {duration > 0 && (
        <div style={{ padding: '10px 20px 0', position: 'relative' }}>
          <div style={{ width: '100%', height: 32, position: 'relative' }}>
            {/* Track */}
            <div style={{
              position: 'absolute', top: '50%', left: 0, right: 0,
              height: 3, background: 'rgba(255,255,255,0.07)',
              borderRadius: 2, transform: 'translateY(-50%)',
            }} />
            {/* Progress fill */}
            <div style={{
              position: 'absolute', top: '50%', left: 0,
              height: 3, background: '#4f9ef8', borderRadius: 2,
              transform: 'translateY(-50%)',
              width: `${(currentTime / duration) * 100}%`,
              transition: 'width 0.25s linear',
            }} />
            {/* Event ticks */}
            {events.map((e, i) => {
              const pct = (e.timestamp / duration) * 100;
              const colors: Record<string, string> = { positive: '#4ade80', low: '#4f9ef8', medium: '#fb923c', high: '#f87171' };
              return (
                <div
                  key={i}
                  title={`${formatTime(e.timestamp)} — ${e.title}`}
                  onClick={() => onSeek(e.timestamp)}
                  style={{
                    position: 'absolute', top: '50%', transform: 'translate(-50%, -50%)',
                    left: `${pct}%`,
                    width: 8, height: 8, borderRadius: '50%',
                    background: colors[e.severity],
                    cursor: 'pointer',
                    border: '2px solid var(--bg-base)',
                    boxShadow: `0 0 6px ${colors[e.severity]}80`,
                    zIndex: 2, transition: 'transform 0.15s',
                  }}
                  onMouseEnter={el => (el.currentTarget as HTMLDivElement).style.transform = 'translate(-50%,-50%) scale(1.5)'}
                  onMouseLeave={el => (el.currentTarget as HTMLDivElement).style.transform = 'translate(-50%,-50%) scale(1)'}
                />
              );
            })}
            {/* Playhead */}
            <div style={{
              position: 'absolute', top: '50%', transform: 'translate(-50%, -50%)',
              left: `${(currentTime / duration) * 100}%`,
              width: 14, height: 14, borderRadius: '50%',
              background: 'white',
              border: '3px solid #4f9ef8',
              boxShadow: '0 0 10px rgba(79,158,248,0.5)',
              zIndex: 3, transition: 'left 0.25s linear',
            }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      )}

      {/* Event list */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px 8px 12px' }}>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0', fontSize: 14 }}>
            No events in this category
          </div>
        ) : (
          filtered.map((event, i) => (
            <EventCard
              key={i}
              event={event}
              active={i === activeIdx && duration > 0}
              onClick={() => onSeek(event.timestamp)}
            />
          ))
        )}
      </div>
    </div>
  );
}
