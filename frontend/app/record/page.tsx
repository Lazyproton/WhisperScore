'use client';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { useMediaRecorder } from '@/hooks/useMediaRecorder';
import { useAnalysis } from '@/hooks/useAnalysis';
import { Mic2, Square, RotateCcw, Upload, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

function formatTime(s: number) {
  const m = Math.floor(s / 60);
  return `${m}:${(s % 60).toString().padStart(2, '0')}`;
}

const STATUS_MESSAGES: Record<string, string> = {
  uploading:  'Uploading recording…',
  analyzing:  'Running AI analysis pipeline… (this takes 1–3 minutes)',
  complete:   'Analysis complete! Redirecting…',
  failed:     'Analysis failed.',
};

export default function RecordPage() {
  const router = useRouter();
  const recorder = useMediaRecorder();
  const analysis = useAnalysis();

  // Redirect to results when complete
  useEffect(() => {
    if (analysis.status === 'complete' && analysis.results) {
      setTimeout(() => router.push(`/analysis/${analysis.results!.session_id}`), 800);
    }
  }, [analysis.status, analysis.results, router]);

  const handleSubmit = async () => {
    if (!recorder.videoBlob) return;
    await analysis.submitRecording(recorder.videoBlob);
  };

  const isProcessing = analysis.status && analysis.status !== 'complete' && analysis.status !== 'failed';

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      <Navbar />

      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        padding: '100px 24px 60px', maxWidth: 860, margin: '0 auto',
      }}>
        <h1 style={{ fontSize: 36, marginBottom: 8, textAlign: 'center' }}>
          Recording <span className="gradient-text">Studio</span>
        </h1>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 40, textAlign: 'center' }}>
          Speak naturally. WhisperScore will do the rest.
        </p>

        {/* Error Banner */}
        {(recorder.error || analysis.error) && (
          <div style={{
            width: '100%', padding: '14px 20px', borderRadius: 12, marginBottom: 24,
            background: 'rgba(248,113,113,0.12)', border: '1px solid rgba(248,113,113,0.3)',
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            <AlertCircle size={18} color="#f87171" />
            <span style={{ color: '#f87171', fontSize: 14 }}>
              {recorder.error ?? analysis.error}
            </span>
          </div>
        )}

        {/* Video Preview */}
        <div style={{
          width: '100%', maxWidth: 720, aspectRatio: '16/9',
          borderRadius: 20, overflow: 'hidden', position: 'relative',
          background: 'var(--bg-elevated)',
          border: recorder.state === 'recording'
            ? '2px solid rgba(248,113,113,0.6)'
            : '1px solid var(--border)',
          boxShadow: recorder.state === 'recording'
            ? '0 0 40px rgba(248,113,113,0.15)'
            : '0 8px 40px rgba(0,0,0,0.4)',
          transition: 'all 0.3s ease',
        }}>
          {/* Live camera preview */}
          {(recorder.state === 'recording' || recorder.state === 'countdown') && (
            <video
              ref={recorder.previewRef as React.RefObject<HTMLVideoElement>}
              style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }}
              autoPlay muted playsInline
            />
          )}

          {/* Recorded video playback */}
          {recorder.state === 'stopped' && recorder.videoUrl && (
            <video
              src={recorder.videoUrl}
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
              controls
            />
          )}

          {/* Idle placeholder */}
          {recorder.state === 'idle' && (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', gap: 16,
            }}>
              <div style={{
                width: 72, height: 72, borderRadius: '50%',
                background: 'rgba(79,158,248,0.1)',
                border: '1px solid rgba(79,158,248,0.2)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Mic2 size={32} color="#4f9ef8" />
              </div>
              <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Camera preview will appear here</p>
            </div>
          )}

          {/* Countdown overlay */}
          {recorder.state === 'countdown' && (
            <div style={{
              position: 'absolute', inset: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(0,0,0,0.5)',
            }}>
              <div style={{
                width: 100, height: 100, borderRadius: '50%',
                background: 'rgba(79,158,248,0.2)',
                border: '3px solid #4f9ef8',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 52, fontWeight: 800,
                fontFamily: "'Space Grotesk', sans-serif",
                color: '#4f9ef8',
              }}>
                {recorder.countdown}
              </div>
            </div>
          )}

          {/* Recording badge */}
          {recorder.state === 'recording' && (
            <div style={{
              position: 'absolute', top: 16, left: 16,
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 14px', borderRadius: 100,
              background: 'rgba(0,0,0,0.6)',
              backdropFilter: 'blur(8px)',
            }}>
              <div className="pulse-ring" style={{
                width: 10, height: 10, borderRadius: '50%',
                background: '#f87171',
              }} />
              <span style={{ color: 'white', fontSize: 13, fontWeight: 600 }}>
                REC {formatTime(recorder.elapsed)}
              </span>
            </div>
          )}
        </div>

        {/* Controls */}
        <div style={{
          display: 'flex', gap: 14, marginTop: 28,
          alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center',
        }}>
          {recorder.state === 'idle' && (
            <button className="btn-primary" onClick={recorder.startCountdown} style={{ padding: '14px 36px', fontSize: 16 }}>
              <Mic2 size={18} /> Start Recording
            </button>
          )}
          {recorder.state === 'countdown' && (
            <button className="btn-secondary" disabled style={{ padding: '14px 36px', fontSize: 16 }}>
              Get ready…
            </button>
          )}
          {recorder.state === 'recording' && (
            <button className="btn-danger" onClick={recorder.stopRecording} style={{ padding: '14px 36px', fontSize: 16 }}>
              <Square size={18} /> Stop Recording
            </button>
          )}
          {recorder.state === 'stopped' && !isProcessing && (
            <>
              <button className="btn-primary" onClick={handleSubmit} style={{ padding: '14px 36px', fontSize: 16 }}>
                <Upload size={18} /> Analyze This Recording
              </button>
              <button className="btn-secondary" onClick={recorder.resetRecording} style={{ padding: '14px 36px' }}>
                <RotateCcw size={16} /> Re-record
              </button>
            </>
          )}
        </div>

        {/* Upload / Analysis Progress */}
        {isProcessing && (
          <div style={{
            width: '100%', maxWidth: 500, marginTop: 36,
            textAlign: 'center',
          }}>
            <div className="glass" style={{ padding: '28px 32px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, marginBottom: 16 }}>
                <Loader2 size={22} color="#4f9ef8"
                  style={{ animation: 'spin 1s linear infinite' }}
                />
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                  {STATUS_MESSAGES[analysis.status ?? ''] ?? 'Processing…'}
                </span>
              </div>
              {analysis.status === 'uploading' && (
                <div style={{ width: '100%', height: 6, background: 'var(--bg-elevated)', borderRadius: 3 }}>
                  <div style={{
                    height: '100%', borderRadius: 3,
                    background: 'linear-gradient(90deg, #4f9ef8, #a78bfa)',
                    width: `${analysis.uploadProgress}%`,
                    transition: 'width 0.3s ease',
                  }} />
                </div>
              )}
              {analysis.status === 'analyzing' && (
                <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginTop: 8 }}>
                  7 AI analyzers running in parallel — Whisper, Silero, librosa, Parselmouth, MediaPipe (×2), Groq LLM
                </p>
              )}
            </div>
          </div>
        )}

        {analysis.status === 'complete' && (
          <div style={{
            marginTop: 28, display: 'flex', alignItems: 'center', gap: 10,
            color: '#4ade80', fontWeight: 600,
          }}>
            <CheckCircle size={20} /> Analysis complete! Redirecting to results…
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
