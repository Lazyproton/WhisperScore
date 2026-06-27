'use client';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, Tooltip,
} from 'recharts';
import type { ScoreBreakdown } from '@/lib/types';

interface Props { scores: ScoreBreakdown; }

export default function ScoreRadar({ scores }: Props) {
  const data = [
    { subject: 'Content',  score: Math.round(scores.content),  fullMark: 100 },
    { subject: 'Voice',    score: Math.round(scores.voice),    fullMark: 100 },
    { subject: 'Presence', score: Math.round(scores.presence), fullMark: 100 },
    { subject: 'Clarity',  score: Math.round(scores.clarity ?? 70),  fullMark: 100 },
    { subject: 'Pace',     score: Math.round(scores.speaking_rate ?? 70), fullMark: 100 },
  ];

  return (
    <div className="glass" style={{ padding: '24px 16px', height: 320, position: 'relative' }}>
      <h3 style={{ fontSize: 14, color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 8, paddingLeft: 8 }}>
        Score Breakdown
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data} cx="50%" cy="50%" outerRadius={90}>
          <PolarGrid stroke="rgba(255,255,255,0.08)" />
          <PolarAngleAxis
            dataKey="subject"
            tick={{ fill: '#8b99b8', fontSize: 12, fontWeight: 500 }}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke="#4f9ef8"
            fill="#4f9ef8"
            fillOpacity={0.18}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 10,
              color: 'var(--text-primary)',
              fontSize: 13,
            }}
            formatter={(v) => [`${Number(v)}/100`, 'Score']}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
