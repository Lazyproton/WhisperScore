'use client';
import { useEffect, useRef, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import ScoreCard from '@/components/analysis/ScoreCard';
import ScoreRadar from '@/components/analysis/ScoreRadar';
import InteractiveTimeline from '@/components/analysis/InteractiveTimeline';
import VideoReplay, { type VideoReplayHandle } from '@/components/analysis/VideoReplay';
import CoachingPanel from '@/components/analysis/CoachingPanel';
import { getResults } from '@/lib/api';
import type { AnalysisResults } from '@/lib/types';
import { scoreColor, formatTime } from '@/lib/types';
import { Mic2, Eye, Brain, BarChart3, ArrowLeft, Download } from 'lucide-react';

function MetricPill({ label, value, unit }: { label: string; value?: number | null; unit?: string }) {
  if (value == null) return null;
  return (
    <div style={{
      padding: '10px 16px', borderRadius: 10,
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid var(--border)',
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "'Space Grotesk', sans-serif", color: 'var(--text-primary)' }}>
        {typeof value === 'number' ? Math.round(value) : value}
        {unit && <span style={{ fontSize: 13, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 3 }}>{unit}</span>}
      </div>
    </div>
  );
}

export default function AnalysisPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const unwrappedParams = use(params);
  const router = useRouter();
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [activeTab, setActiveTab] = useState<'overview' | 'timeline' | 'coaching'>('overview');
  const videoRef = useRef<VideoReplayHandle>(null);

  const sessionId = unwrappedParams.sessionId;
  const isDemo = sessionId === 'demo';

  useEffect(() => {
    async function load() {
      try {
        const r = await getResults(sessionId);
        setResults(r);
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    }
    if (!isDemo) load();
    else setLoading(false);
  }, [sessionId, isDemo]);

  const handleSeek = (t: number) => {
    videoRef.current?.seekTo(t);
  };

  if (loading) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Navbar />
      <div style={{ textAlign: 'center' }}>
        <div className="shimmer" style={{ width: 200, height: 20, borderRadius: 8, margin: '0 auto 12px' }} />
        <div style={{ color: 'var(--text-muted)', fontSize: 14 }}>Loading results…</div>
      </div>
    </div>
  );

  if (error) return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Navbar />
      <div style={{ textAlign: 'center', color: '#f87171' }}>
        <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>Failed to load results</div>
        <div style={{ fontSize: 14, marginBottom: 20 }}>{error}</div>
        <button className="btn-secondary" onClick={() => router.push('/record')}>
          <ArrowLeft size={16} /> Try again
        </button>
      </div>
    </div>
  );

  if (!results) return null;

  const { scores, events, coaching, duration_seconds } = results;

  const TABS = [
    { key: 'overview', label: 'Overview', icon: <BarChart3 size={15} /> },
    { key: 'timeline', label: 'Timeline', icon: <Mic2 size={15} /> },
    { key: 'coaching', label: 'Coaching', icon: <Brain size={15} /> },
  ] as const;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <Navbar />

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div style={{
        padding: '88px 24px 0',
        maxWidth: 1200, margin: '0 auto',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 6, flexWrap: 'wrap' }}>
          <button
            onClick={() => router.push('/record')}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6, fontSize: 14,
            }}
          >
            <ArrowLeft size={16} /> Back
          </button>
          {isDemo && (
            <span style={{
              padding: '3px 10px', borderRadius: 100, fontSize: 12, fontWeight: 600,
              background: 'rgba(167,139,250,0.15)', color: '#a78bfa',
              border: '1px solid rgba(167,139,250,0.2)',
            }}>Demo</span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <h1 style={{ fontSize: 32, marginBottom: 6 }}>
              Analysis <span className="gradient-text">Results</span>
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              {duration_seconds ? `${formatTime(duration_seconds)} recording · ` : ''}
              {events.length} coaching events · 7 AI analyzers
            </p>
          </div>
          {scores && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '12px 20px', borderRadius: 14,
              background: 'rgba(255,255,255,0.04)',
              border: `1px solid ${scoreColor(scores.overall)}40`,
            }}>
              <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Overall</span>
              <span style={{
                fontSize: 38, fontWeight: 900,
                fontFamily: "'Space Grotesk', sans-serif",
                color: scoreColor(scores.overall),
              }}>
                {Math.round(scores.overall)}
              </span>
              <span style={{ fontSize: 18, color: 'var(--text-muted)' }}>/100</span>
            </div>
          )}
        </div>

        {/* Tab nav */}
        <div style={{
          display: 'flex', gap: 4, marginTop: 28,
          borderBottom: '1px solid var(--border)',
        }}>
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              style={{
                display: 'flex', alignItems: 'center', gap: 7,
                padding: '10px 18px', fontSize: 14, fontWeight: 600,
                border: 'none', background: 'none', cursor: 'pointer',
                borderBottom: activeTab === t.key ? '2px solid #4f9ef8' : '2px solid transparent',
                color: activeTab === t.key ? '#4f9ef8' : 'var(--text-muted)',
                transition: 'all 0.15s',
                marginBottom: -1,
              }}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Tab Content ─────────────────────────────────────────────────── */}
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '28px 24px 60px' }}>

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && scores && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* Score cards row */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
              gap: 16,
            }}>
              <ScoreCard label="Content"  score={scores.content}  icon={<Brain size={14} />} accentColor="#a78bfa" size="md" />
              <ScoreCard label="Voice"    score={scores.voice}    icon={<Mic2 size={14} />}  accentColor="#4f9ef8" size="md" />
              <ScoreCard label="Presence" score={scores.presence} icon={<Eye size={14} />}   accentColor="#2dd4bf" size="md" />
            </div>

            {/* Radar + sub-metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              <ScoreRadar scores={scores} />

              <div className="glass" style={{ padding: '24px' }}>
                <h3 style={{ fontSize: 14, color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 16 }}>
                  Detailed Metrics
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <MetricPill label="Speaking Rate"  value={scores.speaking_rate}   unit="/100" />
                  <MetricPill label="Filler Score"   value={scores.filler_score}    unit="/100" />
                  <MetricPill label="Pause Quality"  value={scores.pause_quality}   unit="/100" />
                  <MetricPill label="Pitch Variation" value={scores.pitch_variation} unit="/100" />
                  <MetricPill label="Eye Contact"    value={scores.eye_contact}     unit="/100" />
                  <MetricPill label="Posture"        value={scores.posture}         unit="/100" />
                  <MetricPill label="Clarity"        value={scores.clarity}         unit="/100" />
                  <MetricPill label="Organization"   value={scores.organization}    unit="/100" />
                </div>
              </div>
            </div>

            {/* Top events preview */}
            {events.length > 0 && (
              <div className="glass" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                  <h3 style={{ fontSize: 15, fontWeight: 700 }}>Top Coaching Moments</h3>
                  <button
                    onClick={() => setActiveTab('timeline')}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#4f9ef8', fontSize: 13, fontWeight: 600 }}
                  >
                    See all →
                  </button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
                  {[...events]
                    .sort((a, b) => {
                      const rank = { high: 0, positive: 1, medium: 2, low: 3 };
                      return rank[a.severity] - rank[b.severity];
                    })
                    .slice(0, 5)
                    .map((e, i) => {
                      const colors: Record<string, string> = { positive: '#4ade80', low: '#4f9ef8', medium: '#fb923c', high: '#f87171' };
                      return (
                        <div key={i} style={{
                          display: 'flex', gap: 12, padding: '12px 0',
                          borderBottom: i < 4 ? '1px solid var(--border)' : 'none',
                          cursor: 'pointer',
                        }} onClick={() => { handleSeek(e.timestamp); setActiveTab('timeline'); }}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: colors[e.severity], marginTop: 6, flexShrink: 0 }} />
                          <div>
                            <div style={{ fontSize: 13, fontWeight: 600 }}>{e.title}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{formatTime(e.timestamp)} · {e.category}</div>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TIMELINE TAB */}
        {activeTab === 'timeline' && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 380px',
            gap: 20, minHeight: 600,
          }}>
            <div style={{ height: 600 }}>
              <VideoReplay
                ref={videoRef}
                videoUrl={isDemo ? null : `/uploads/${sessionId}/recording.webm`}
                events={events}
                onTimeUpdate={setCurrentTime}
              />
            </div>
            <div style={{ height: 600 }}>
              <InteractiveTimeline
                events={events}
                duration={duration_seconds ?? 0}
                currentTime={currentTime}
                onSeek={handleSeek}
              />
            </div>
          </div>
        )}

        {/* COACHING TAB */}
        {activeTab === 'coaching' && coaching && (
          <div style={{ maxWidth: 720, margin: '0 auto' }}>
            <CoachingPanel coaching={coaching} transcript={coaching.transcript} />
          </div>
        )}
        {activeTab === 'coaching' && !coaching && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '60px 0', fontSize: 15 }}>
            No coaching data available. Add a GROQ_API_KEY to enable AI coaching.
          </div>
        )}
      </div>
    </div>
  );
}
