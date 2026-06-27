'use client';
import { useRef, useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import type { TimelineEvent } from '@/lib/types';
import { SEVERITY_COLORS, formatTime } from '@/lib/types';
import { Play, Pause, SkipBack, Volume2, Maximize2 } from 'lucide-react';

interface Props {
  videoUrl: string | null;
  events: TimelineEvent[];
  onTimeUpdate?: (t: number) => void;
}

export interface VideoReplayHandle {
  seekTo: (t: number) => void;
}

const VideoReplay = forwardRef<VideoReplayHandle, Props>(
  ({ videoUrl, events, onTimeUpdate }, ref) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [playing, setPlaying]   = useState(false);
    const [current, setCurrent]   = useState(0);
    const [duration, setDuration] = useState(0);
    const [volume, setVolume]     = useState(1);
    const [nearEvent, setNearEvent] = useState<TimelineEvent | null>(null);

    useImperativeHandle(ref, () => ({
      seekTo(t: number) {
        if (videoRef.current) {
          videoRef.current.currentTime = t;
          videoRef.current.play().catch(() => {});
          setPlaying(true);
        } else {
          setCurrent(t);
          onTimeUpdate?.(t);
        }
      },
    }));

    const handleTimeUpdate = useCallback(() => {
      const v = videoRef.current;
      if (!v) return;
      setCurrent(v.currentTime);
      onTimeUpdate?.(v.currentTime);

      // Find closest upcoming event within ±1.5s
      const near = events.find(
        e => Math.abs(e.timestamp - v.currentTime) < 1.5
      ) ?? null;
      setNearEvent(near);
    }, [events, onTimeUpdate]);

    useEffect(() => {
      const v = videoRef.current;
      if (!v) return;
      v.addEventListener('timeupdate', handleTimeUpdate);
      v.addEventListener('loadedmetadata', () => setDuration(v.duration));
      v.addEventListener('play', () => setPlaying(true));
      v.addEventListener('pause', () => setPlaying(false));
      v.addEventListener('ended', () => setPlaying(false));
      return () => {
        v.removeEventListener('timeupdate', handleTimeUpdate);
      };
    }, [handleTimeUpdate]);

    const togglePlay = () => {
      const v = videoRef.current;
      if (!v) return;
      playing ? v.pause() : v.play();
    };

    const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
      const t = parseFloat(e.target.value);
      if (videoRef.current) {
        videoRef.current.currentTime = t;
      } else {
        setCurrent(t);
        onTimeUpdate?.(t);
      }
    };

    const handleVolume = (e: React.ChangeEvent<HTMLInputElement>) => {
      const v = parseFloat(e.target.value);
      setVolume(v);
      if (videoRef.current) videoRef.current.volume = v;
    };

    const handleFullscreen = () => videoRef.current?.requestFullscreen?.();

    const sevColor = nearEvent ? SEVERITY_COLORS[nearEvent.severity] : null;

    return (
      <div className="glass" style={{ overflow: 'hidden', borderRadius: 16 }}>
        {/* Video */}
        <div style={{ position: 'relative', background: '#000', aspectRatio: '16/9' }}>
          {videoUrl ? (
            <video
              ref={videoRef}
              src={videoUrl}
              style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }}
              preload="auto"
            />
          ) : (
            <div style={{
              width: '100%', height: '100%', display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              color: 'var(--text-muted)', fontSize: 14, minHeight: 200,
            }}>
              No video — showing demo data
            </div>
          )}

          {/* Event popup overlay */}
          {nearEvent && sevColor && (
            <div style={{
              position: 'absolute', bottom: 16, left: '50%', transform: 'translateX(-50%)',
              padding: '8px 16px', borderRadius: 10,
              background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)',
              border: `1px solid ${sevColor}50`,
              display: 'flex', alignItems: 'center', gap: 10,
              maxWidth: '90%', animation: 'fadeUp 0.3s ease',
            }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: sevColor, flexShrink: 0 }} />
              <span style={{ color: 'white', fontSize: 13, fontWeight: 600 }}>
                {nearEvent.title}
              </span>
            </div>
          )}
        </div>

        {/* Controls */}
        <div style={{ padding: '12px 16px', background: 'rgba(0,0,0,0.3)' }}>
          {/* Seek bar */}
          <div style={{ marginBottom: 10 }}>
            <input
              type="range" min={0} max={duration || 1} step={0.1} value={current}
              onChange={handleSeek}
              style={{ width: '100%' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
              <span>{formatTime(current)}</span><span>{formatTime(duration)}</span>
            </div>
          </div>

          {/* Buttons row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              onClick={() => { if (videoRef.current) videoRef.current.currentTime = 0; }}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)', padding: 4 }}
            >
              <SkipBack size={18} />
            </button>
            <button
              onClick={togglePlay}
              style={{
                width: 38, height: 38, borderRadius: '50%', border: 'none', cursor: 'pointer',
                background: 'linear-gradient(135deg, #4f9ef8, #a78bfa)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 4px 14px rgba(79,158,248,0.35)',
              }}
            >
              {playing ? <Pause size={16} color="white" /> : <Play size={16} color="white" fill="white" />}
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1 }}>
              <Volume2 size={15} color="var(--text-muted)" />
              <input
                type="range" min={0} max={1} step={0.05} value={volume}
                onChange={handleVolume}
                style={{ width: 80 }}
              />
            </div>
            <button
              onClick={handleFullscreen}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)', padding: 4 }}
            >
              <Maximize2 size={16} />
            </button>
          </div>
        </div>
      </div>
    );
  }
);

VideoReplay.displayName = 'VideoReplay';
export default VideoReplay;
