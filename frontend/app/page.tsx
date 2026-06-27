'use client';

import Link from 'next/link';
import Navbar from '@/components/Navbar';
import { Mic2, Eye, Brain, Zap, TrendingUp, Clock, Star } from 'lucide-react';

const FEATURES = [
  {
    icon: <Brain size={22} />, color: '#a78bfa',
    title: 'AI Content Analysis',
    desc: 'Groq LLM evaluates your clarity, structure, argument quality, and persuasiveness — then rewrites your weakest paragraph.',
  },
  {
    icon: <Mic2 size={22} />, color: '#4f9ef8',
    title: 'Voice Coaching',
    desc: 'Whisper + Parselmouth detect filler words, speaking rate spikes, monotone delivery, and vocal tension with millisecond precision.',
  },
  {
    icon: <Eye size={22} />, color: '#2dd4bf',
    title: 'Presence & Body Language',
    desc: 'MediaPipe tracks eye contact percentage, head pose, and posture alignment across every frame of your recording.',
  },
  {
    icon: <Clock size={22} />, color: '#fb923c',
    title: 'Timestamp-Precise Events',
    desc: 'Every insight is pinned to an exact moment. Click a coaching card and the video seeks straight to that moment.',
  },
  {
    icon: <TrendingUp size={22} />, color: '#4ade80',
    title: 'Weighted Scoring',
    desc: 'Four score dimensions — Overall, Content, Voice, Presence — with radar visualization and sub-metric breakdowns.',
  },
  {
    icon: <Zap size={22} />, color: '#f472b6',
    title: 'Modular by Design',
    desc: 'New analyzers drop in without touching existing code. Add debate scoring, accent detection, or slide sync later.',
  },
];

const STATS = [
  { value: '7', label: 'AI Analyzers' },
  { value: '4', label: 'Score Dimensions' },
  { value: '<3min', label: 'Analysis Time' },
  { value: '100%', label: 'Private & Local' },
];

export default function HomePage() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <Navbar />

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section style={{
        minHeight: '100vh',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        padding: '120px 24px 80px',
        position: 'relative', overflow: 'hidden',
        textAlign: 'center',
      }}>
        {/* Background glow blobs */}
        <div style={{
          position: 'absolute', width: 700, height: 700,
          borderRadius: '50%', top: '-200px', left: '50%',
          transform: 'translateX(-50%)',
          background: 'radial-gradient(circle, rgba(79,158,248,0.08) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute', width: 400, height: 400,
          borderRadius: '50%', bottom: '10%', right: '5%',
          background: 'radial-gradient(circle, rgba(167,139,250,0.07) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />

        {/* Badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          padding: '6px 16px', borderRadius: 100,
          background: 'rgba(79,158,248,0.1)',
          border: '1px solid rgba(79,158,248,0.2)',
          marginBottom: 28,
          animation: 'fadeUp 0.6s ease forwards',
        }}>
          <Star size={14} color="#4f9ef8" fill="#4f9ef8" />
          <span style={{ fontSize: 13, color: '#4f9ef8', fontWeight: 600 }}>
            AI-Powered · Timestamp-Precise · Private
          </span>
        </div>

        <h1 style={{
          fontSize: 'clamp(48px, 7vw, 80px)',
          lineHeight: 1.05,
          marginBottom: 24,
          animation: 'fadeUp 0.7s ease 0.1s both',
        }}>
          Become a Better Speaker<br />
          <span className="gradient-text">With Every Recording</span>
        </h1>

        <p style={{
          fontSize: 'clamp(16px, 2vw, 20px)',
          color: 'var(--text-secondary)',
          maxWidth: 600,
          lineHeight: 1.7,
          marginBottom: 44,
          animation: 'fadeUp 0.7s ease 0.2s both',
        }}>
          WhisperScore analyzes your entire presentation — content, voice delivery,
          and body language — then pins coaching to the exact timestamps where you can improve.
        </p>

        <div style={{
          display: 'flex', gap: 14, flexWrap: 'wrap', justifyContent: 'center',
          animation: 'fadeUp 0.7s ease 0.3s both',
        }}>
          <Link href="/record" className="btn-primary" style={{ fontSize: 16, padding: '14px 36px' }}>
            <Mic2 size={18} />
            Start Recording — Free
          </Link>
          <Link href="/demo" className="btn-secondary" style={{ fontSize: 16, padding: '14px 36px' }}>
            View Demo Analysis
          </Link>
        </div>

        {/* Stats strip */}
        <div style={{
          display: 'flex', gap: 48, marginTop: 80, flexWrap: 'wrap', justifyContent: 'center',
          animation: 'fadeUp 0.7s ease 0.4s both',
        }}>
          {STATS.map(s => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div style={{
                fontSize: 36, fontWeight: 800,
                fontFamily: "'Space Grotesk', sans-serif",
                background: 'linear-gradient(135deg, #4f9ef8, #a78bfa)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              }}>{s.value}</div>
              <div style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 2 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ────────────────────────────────────────────────────── */}
      <section style={{ padding: '80px 24px 120px', maxWidth: 1100, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <h2 style={{ fontSize: 40, marginBottom: 14 }}>
            Seven AI analyzers.<br />
            <span className="gradient-text">One unified score.</span>
          </h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 17, maxWidth: 500, margin: '0 auto' }}>
            Each analyzer runs concurrently and pins events to your exact timestamp.
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: 20,
        }}>
          {FEATURES.map((f) => (
            <div key={f.title} className="glass" style={{
              padding: '28px 28px 32px',
              transition: 'transform 0.2s, box-shadow 0.2s',
              cursor: 'default',
            }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-4px)';
                (e.currentTarget as HTMLDivElement).style.boxShadow = `0 12px 40px rgba(0,0,0,0.4)`;
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLDivElement).style.transform = '';
                (e.currentTarget as HTMLDivElement).style.boxShadow = '';
              }}
            >
              <div style={{
                width: 48, height: 48, borderRadius: 12,
                background: `${f.color}18`,
                border: `1px solid ${f.color}30`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: f.color, marginBottom: 18,
              }}>
                {f.icon}
              </div>
              <h3 style={{ fontSize: 18, marginBottom: 10, fontWeight: 600 }}>{f.title}</h3>
              <p style={{ color: 'var(--text-secondary)', lineHeight: 1.65, fontSize: 14 }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA Banner ──────────────────────────────────────────────────── */}
      <section style={{ padding: '0 24px 100px' }}>
        <div style={{
          maxWidth: 800, margin: '0 auto', textAlign: 'center',
          background: 'linear-gradient(135deg, rgba(79,158,248,0.1) 0%, rgba(167,139,250,0.1) 100%)',
          border: '1px solid rgba(79,158,248,0.2)',
          borderRadius: 24, padding: '60px 40px',
        }}>
          <h2 style={{ fontSize: 36, marginBottom: 16 }}>
            Ready to see your blind spots?
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 32, fontSize: 16 }}>
            Record a 1-minute talk and get your full AI analysis in under 3 minutes.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link href="/record" className="btn-primary" style={{ fontSize: 16, padding: '14px 36px' }}>
              <Mic2 size={18} /> Start Now — It's Free
            </Link>
            <Link href="/demo" className="btn-secondary" style={{ fontSize: 16 }}>
              Try the Demo First
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{
        textAlign: 'center', padding: '24px',
        color: 'var(--text-muted)', fontSize: 13,
        borderTop: '1px solid var(--border)',
      }}>
        WhisperScore — Built with faster-whisper, MediaPipe, librosa, Parselmouth, Silero VAD & Groq
      </footer>
    </div>
  );
}
