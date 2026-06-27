'use client';
import { scoreColor, scoreLabel } from '@/lib/types';

interface ScoreCardProps {
  label: string;
  score: number;
  icon?: React.ReactNode;
  accentColor?: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function ScoreCard({ label, score, icon, accentColor, size = 'md' }: ScoreCardProps) {
  const color = accentColor ?? scoreColor(score);
  const radius = size === 'lg' ? 52 : size === 'md' ? 40 : 30;
  const stroke = size === 'lg' ? 5 : 4;
  const fontSize = size === 'lg' ? 28 : size === 'md' ? 22 : 16;
  const circumference = 2 * Math.PI * radius;
  const progress = circumference - (score / 100) * circumference;

  return (
    <div className="glass" style={{
      padding: size === 'lg' ? '28px 32px' : '20px 24px',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      gap: size === 'lg' ? 16 : 12,
      transition: 'transform 0.2s, box-shadow 0.2s',
      cursor: 'default',
    }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-3px)';
        (e.currentTarget as HTMLDivElement).style.boxShadow = `0 12px 32px rgba(0,0,0,0.4)`;
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.transform = '';
        (e.currentTarget as HTMLDivElement).style.boxShadow = '';
      }}
    >
      {/* Ring */}
      <div style={{ position: 'relative', width: radius * 2 + stroke * 2, height: radius * 2 + stroke * 2 }}>
        <svg
          width={radius * 2 + stroke * 2}
          height={radius * 2 + stroke * 2}
          style={{ transform: 'rotate(-90deg)' }}
        >
          {/* Track */}
          <circle
            cx={radius + stroke} cy={radius + stroke} r={radius}
            fill="none" stroke="rgba(255,255,255,0.07)"
            strokeWidth={stroke}
          />
          {/* Progress */}
          <circle
            cx={radius + stroke} cy={radius + stroke} r={radius}
            fill="none" stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={progress}
            style={{ transition: 'stroke-dashoffset 1s ease', filter: `drop-shadow(0 0 6px ${color}80)` }}
          />
        </svg>
        {/* Center text */}
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          gap: 2,
        }}>
          {icon && <div style={{ color, opacity: 0.9 }}>{icon}</div>}
          <span style={{ fontSize, fontWeight: 800, color, fontFamily: "'Space Grotesk', sans-serif" }}>
            {Math.round(score)}
          </span>
        </div>
      </div>

      {/* Label */}
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontWeight: 600, fontSize: size === 'sm' ? 13 : 15, color: 'var(--text-primary)' }}>
          {label}
        </div>
        <div style={{ fontSize: 12, color, marginTop: 2, fontWeight: 500 }}>
          {scoreLabel(score)}
        </div>
      </div>
    </div>
  );
}
