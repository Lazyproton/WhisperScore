'use client';
import type { CoachingResult } from '@/lib/types';
import { ThumbsUp, AlertTriangle, Lightbulb, FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

interface Props { coaching: CoachingResult; transcript?: string; }

function Section({
  icon, title, color, items, expand = false,
}: {
  icon: React.ReactNode; title: string; color: string;
  items: string[]; expand?: boolean;
}) {
  const [open, setOpen] = useState(!expand || items.length <= 3);
  const visible = open ? items : items.slice(0, 3);

  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: `${color}18`, border: `1px solid ${color}30`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color,
        }}>
          {icon}
        </div>
        <span style={{ fontWeight: 600, fontSize: 14 }}>{title}</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {visible.map((item, i) => (
          <div key={i} style={{
            display: 'flex', gap: 10, padding: '10px 14px',
            background: `${color}08`, borderRadius: 10,
            border: `1px solid ${color}15`,
          }}>
            <span style={{ color, flexShrink: 0, marginTop: 1, fontSize: 16 }}>•</span>
            <span style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.55 }}>{item}</span>
          </div>
        ))}
      </div>
      {items.length > 3 && (
        <button
          onClick={() => setOpen(o => !o)}
          style={{
            marginTop: 8, background: 'none', border: 'none',
            cursor: 'pointer', color: 'var(--text-muted)',
            fontSize: 13, display: 'flex', alignItems: 'center', gap: 4,
          }}
        >
          {open ? <><ChevronUp size={14} /> Show less</> : <><ChevronDown size={14} /> Show {items.length - 3} more</>}
        </button>
      )}
    </div>
  );
}

export default function CoachingPanel({ coaching, transcript }: Props) {
  const [showTranscript, setShowTranscript] = useState(false);

  return (
    <div className="glass" style={{ padding: '24px', height: '100%', overflowY: 'auto' }}>
      <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20 }}>
        🎯 AI Coaching Report
      </h3>

      {/* Summary */}
      {coaching.summary && (
        <div style={{
          padding: '14px 16px', borderRadius: 12, marginBottom: 24,
          background: 'rgba(79,158,248,0.08)',
          border: '1px solid rgba(79,158,248,0.2)',
          color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.6,
        }}>
          {coaching.summary}
        </div>
      )}

      {/* Strengths */}
      {coaching.strengths.length > 0 && (
        <Section
          icon={<ThumbsUp size={14} />}
          title="Strengths"
          color="#4ade80"
          items={coaching.strengths}
        />
      )}

      {/* Weaknesses */}
      {coaching.weaknesses.length > 0 && (
        <Section
          icon={<AlertTriangle size={14} />}
          title="Areas to Improve"
          color="#fb923c"
          items={coaching.weaknesses}
        />
      )}

      {/* Tips */}
      {coaching.tips.length > 0 && (
        <Section
          icon={<Lightbulb size={14} />}
          title="Actionable Tips"
          color="#4f9ef8"
          items={coaching.tips}
          expand
        />
      )}

      {/* Improved Excerpt */}
      {coaching.improved_excerpt && (
        <div style={{ marginBottom: 24 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
          }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8,
              background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#a78bfa',
            }}>
              <FileText size={14} />
            </div>
            <span style={{ fontWeight: 600, fontSize: 14 }}>AI-Rewritten Excerpt</span>
          </div>
          <div style={{
            padding: '14px 16px', borderRadius: 10,
            background: 'rgba(167,139,250,0.06)',
            border: '1px solid rgba(167,139,250,0.18)',
            color: 'var(--text-secondary)', fontSize: 13,
            lineHeight: 1.65, fontStyle: 'italic',
          }}>
            "{coaching.improved_excerpt}"
          </div>
        </div>
      )}

      {/* Transcript accordion */}
      {transcript && (
        <div>
          <button
            onClick={() => setShowTranscript(o => !o)}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border)',
              borderRadius: 10, padding: '10px 14px',
              cursor: 'pointer', color: 'var(--text-secondary)', fontSize: 13, fontWeight: 600,
            }}
          >
            <span>Full Transcript</span>
            {showTranscript ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {showTranscript && (
            <div style={{
              marginTop: 8, padding: '14px 16px',
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid var(--border)', borderRadius: 10,
              color: 'var(--text-secondary)', fontSize: 13,
              lineHeight: 1.7, maxHeight: 300, overflowY: 'auto',
            }}>
              {transcript}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
