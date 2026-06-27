'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import ScoreCard from '@/components/analysis/ScoreCard';
import ScoreRadar from '@/components/analysis/ScoreRadar';
import InteractiveTimeline from '@/components/analysis/InteractiveTimeline';
import CoachingPanel from '@/components/analysis/CoachingPanel';
import type { AnalysisResults } from '@/lib/types';
import { scoreColor, formatTime } from '@/lib/types';
import { Mic2, Brain, Eye, BarChart3, Sparkles } from 'lucide-react';

// Inline demo data so the demo works 100% client-side without a backend
const DEMO: AnalysisResults = {
  session_id: 'demo',
  status: 'complete',
  duration_seconds: 220,
  scores: {
    overall: 74.2, content: 71.5, voice: 72.8, presence: 79.0,
    clarity: 74.0, organization: 68.0, persuasiveness: 72.0,
    speaking_rate: 75.0, filler_score: 65.0, pause_quality: 80.0,
    pitch_variation: 82.0, eye_contact: 76.0, posture: 68.0,
  },
  events: [
    { timestamp: 4.0,   category: 'voice',    metric: 'pace',         score: 88, severity: 'positive', title: 'Strong Opening Pace',      description: 'You started at a confident 135 WPM — clear and engaging.' },
    { timestamp: 18.5,  category: 'voice',    metric: 'fillers',      score: 55, severity: 'medium',   title: 'Filler Words Detected',    description: 'Detected "um" and "uh" here. Replace with a confident pause.' },
    { timestamp: 34.0,  category: 'presence', metric: 'eye_contact',  score: 82, severity: 'positive', title: 'Strong Eye Contact',       description: 'Great eye contact here — you appear confident and engaged.' },
    { timestamp: 43.2,  category: 'voice',    metric: 'pace',         score: 38, severity: 'high',     title: 'Speaking Too Fast',        description: 'You spoke at ~178 WPM here. Aim for 120–150 WPM for clarity.' },
    { timestamp: 58.0,  category: 'content',  metric: 'organization', score: 72, severity: 'medium',   title: 'Weak Transition',          description: 'The transition lacked a clear signpost. Use "Moving to my next point…"' },
    { timestamp: 71.5,  category: 'presence', metric: 'eye_contact',  score: 25, severity: 'high',     title: 'Lost Eye Contact',         description: 'You were looking away from the camera here.' },
    { timestamp: 83.2,  category: 'voice',    metric: 'pause',        score: 90, severity: 'positive', title: 'Effective Pause',          description: 'A 1.8s pause here — great for emphasis.' },
    { timestamp: 97.0,  category: 'content',  metric: 'evidence',     score: 42, severity: 'high',     title: 'Weak Supporting Evidence', description: 'This claim lacks data. Back it up with a statistic or example.' },
    { timestamp: 112.5, category: 'voice',    metric: 'pitch',        score: 85, severity: 'positive', title: 'Expressive Delivery',      description: 'Your pitch variation here is excellent — you sound passionate.' },
    { timestamp: 124.0, category: 'presence', metric: 'posture',      score: 55, severity: 'medium',   title: 'Uneven Shoulders',         description: 'Your shoulders appear uneven. Stand straight to project confidence.' },
    { timestamp: 138.0, category: 'content',  metric: 'clarity',      score: 78, severity: 'low',      title: 'Complex Sentence',         description: 'This sentence was long and complex. Shorter sentences improve clarity.' },
    { timestamp: 156.0, category: 'voice',    metric: 'pace',         score: 70, severity: 'low',      title: 'Slight Slowdown',          description: 'Your pace dropped to ~108 WPM. Consider picking up the tempo.' },
    { timestamp: 172.0, category: 'content',  metric: 'persuasion',   score: 88, severity: 'positive', title: 'Compelling Argument',      description: 'Excellent logical structure — highly persuasive.' },
    { timestamp: 198.0, category: 'voice',    metric: 'loudness',     score: 48, severity: 'medium',   title: 'Energy Drop Detected',     description: 'Your vocal energy dropped here. Maintain consistent projection.' },
    { timestamp: 210.5, category: 'content',  metric: 'clarity',      score: 92, severity: 'positive', title: 'Strong Conclusion',        description: 'Your conclusion is clear, memorable, and well-delivered. Great finish!' },
  ],
  coaching: {
    strengths: [
      'Strong, confident opening pace and delivery',
      'Excellent pitch variation — you sound passionate and engaged',
      'Memorable, well-structured conclusion',
    ],
    weaknesses: [
      'Speaking rate spikes above 175 WPM in two segments',
      'Eye contact breaks during key argument sections',
      'Some claims lack supporting evidence or statistics',
    ],
    tips: [
      'Practice with a metronome app set to 135 BPM to internalize ideal pace',
      'Place a sticky note with "LOOK UP" on your monitor during rehearsal',
      'For every major claim, prepare one data point or example',
      'Use pause-breath technique: inhale 1s before key points',
      'Record yourself and watch at 1.25x speed to identify filler word patterns',
    ],
    improved_excerpt: 'Rather than "um, so basically what I mean is…", try: "The core issue is straightforward. When we examine the data, three patterns emerge consistently."',
    summary: 'A solid presentation with genuine strengths in vocal expressiveness and conclusion delivery. Focus on controlling speaking pace and maintaining consistent eye contact to raise your overall score.',
    transcript: 'Good morning everyone. Um, so today I want to talk about the future of artificial intelligence and how it\'s going to, uh, basically change the way we work. The key thing to understand is that AI isn\'t replacing jobs — it\'s fundamentally transforming them.',
  },
};

export default function DemoPage() {
  const router = useRouter();
  const [currentTime, setCurrentTime] = useState(0);
  const [activeTab, setActiveTab] = useState<'overview' | 'timeline' | 'coaching'>('overview');

  const { scores, events, coaching, duration_seconds } = DEMO;

  const TABS = [
    { key: 'overview', label: 'Overview',  icon: <BarChart3 size={15} /> },
    { key: 'timeline', label: 'Timeline',  icon: <Mic2 size={15} /> },
    { key: 'coaching', label: 'Coaching',  icon: <Brain size={15} /> },
  ] as const;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <Navbar />

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '88px 24px 60px' }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
          marginBottom: 28, flexWrap: 'wrap', gap: 20,
        }}>
          <div>
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '4px 12px', borderRadius: 100, marginBottom: 12,
              background: 'rgba(167,139,250,0.12)', border: '1px solid rgba(167,139,250,0.25)',
            }}>
              <Sparkles size={13} color="#a78bfa" />
              <span style={{ fontSize: 12, color: '#a78bfa', fontWeight: 600 }}>Pre-analyzed Demo</span>
            </div>
            <h1 style={{ fontSize: 32, marginBottom: 6 }}>
              Demo <span className="gradient-text">Analysis</span>
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              {formatTime(duration_seconds ?? 220)} recording · {events.length} events · Full AI pipeline results
            </p>
          </div>
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4,
            padding: '14px 20px', borderRadius: 14,
            background: 'rgba(255,255,255,0.03)',
            border: `1px solid ${scoreColor(scores!.overall)}40`,
          }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Overall Score</span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
              <span style={{
                fontSize: 42, fontWeight: 900,
                fontFamily: "'Space Grotesk', sans-serif",
                color: scoreColor(scores!.overall),
              }}>{Math.round(scores!.overall)}</span>
              <span style={{ fontSize: 18, color: 'var(--text-muted)' }}>/100</span>
            </div>
          </div>
        </div>

        {/* CTA banner */}
        <div style={{
          padding: '16px 20px', borderRadius: 12, marginBottom: 24,
          background: 'rgba(79,158,248,0.07)', border: '1px solid rgba(79,158,248,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
        }}>
          <span style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
            Ready to analyze your own presentation?
          </span>
          <button className="btn-primary" onClick={() => router.push('/record')} style={{ padding: '8px 20px', fontSize: 14 }}>
            <Mic2 size={15} /> Start Recording
          </button>
        </div>

        {/* Tab nav */}
        <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border)', marginBottom: 24 }}>
          {TABS.map(t => (
            <button key={t.key} onClick={() => setActiveTab(t.key)} style={{
              display: 'flex', alignItems: 'center', gap: 7,
              padding: '10px 18px', fontSize: 14, fontWeight: 600,
              border: 'none', background: 'none', cursor: 'pointer',
              borderBottom: activeTab === t.key ? '2px solid #4f9ef8' : '2px solid transparent',
              color: activeTab === t.key ? '#4f9ef8' : 'var(--text-muted)',
              transition: 'all 0.15s', marginBottom: -1,
            }}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* OVERVIEW */}
        {activeTab === 'overview' && scores && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16 }}>
              <ScoreCard label="Content"  score={scores.content}  icon={<Brain size={14} />} accentColor="#a78bfa" />
              <ScoreCard label="Voice"    score={scores.voice}    icon={<Mic2 size={14} />}  accentColor="#4f9ef8" />
              <ScoreCard label="Presence" score={scores.presence} icon={<Eye size={14} />}   accentColor="#2dd4bf" />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <ScoreRadar scores={scores} />
              <div className="glass" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: 14, color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 16 }}>Sub-scores</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {[
                    { label: 'Clarity',        value: scores.clarity ?? 74,          color: '#a78bfa' },
                    { label: 'Organization',   value: scores.organization ?? 68,      color: '#a78bfa' },
                    { label: 'Speaking Rate',  value: scores.speaking_rate ?? 75,     color: '#4f9ef8' },
                    { label: 'Filler Words',   value: scores.filler_score ?? 65,      color: '#4f9ef8' },
                    { label: 'Pause Quality',  value: scores.pause_quality ?? 80,     color: '#4f9ef8' },
                    { label: 'Eye Contact',    value: scores.eye_contact ?? 76,       color: '#2dd4bf' },
                    { label: 'Posture',        value: scores.posture ?? 68,           color: '#2dd4bf' },
                  ].map(m => (
                    <div key={m.label}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                        <span style={{ color: 'var(--text-secondary)' }}>{m.label}</span>
                        <span style={{ color: m.color, fontWeight: 600 }}>{Math.round(m.value)}</span>
                      </div>
                      <div style={{ height: 4, background: 'rgba(255,255,255,0.07)', borderRadius: 2 }}>
                        <div style={{ height: '100%', width: `${m.value}%`, background: m.color, borderRadius: 2, transition: 'width 0.8s ease' }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TIMELINE */}
        {activeTab === 'timeline' && (
          <div style={{ height: 600 }}>
            <InteractiveTimeline
              events={events}
              duration={duration_seconds ?? 220}
              currentTime={currentTime}
              onSeek={setCurrentTime}
            />
          </div>
        )}

        {/* COACHING */}
        {activeTab === 'coaching' && coaching && (
          <div style={{ maxWidth: 720, margin: '0 auto' }}>
            <CoachingPanel coaching={coaching} transcript={coaching.transcript} />
          </div>
        )}
      </div>
    </div>
  );
}
