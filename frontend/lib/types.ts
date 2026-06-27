// WhisperScore — TypeScript Types
// Mirrors backend Pydantic schemas exactly.

export type SessionStatus =
  | 'pending'
  | 'uploading'
  | 'analyzing'
  | 'complete'
  | 'failed';

export type EventCategory = 'voice' | 'content' | 'presence';
export type EventSeverity = 'low' | 'medium' | 'high' | 'positive';

export interface TimelineEvent {
  timestamp: number;          // seconds from start
  category: EventCategory;
  metric: string;             // e.g. "pace", "eye_contact"
  score?: number | null;
  severity: EventSeverity;
  title: string;
  description: string;
  extra?: Record<string, unknown>;
}

export interface ScoreBreakdown {
  overall: number;
  content: number;
  voice: number;
  presence: number;
  // Sub-scores
  clarity?: number;
  organization?: number;
  persuasiveness?: number;
  speaking_rate?: number;
  filler_score?: number;
  pause_quality?: number;
  pitch_variation?: number;
  eye_contact?: number;
  posture?: number;
}

export interface CoachingResult {
  strengths: string[];
  weaknesses: string[];
  tips: string[];
  improved_excerpt?: string;
  summary?: string;
  transcript?: string;
}

export interface AnalysisResults {
  session_id: string;
  status: SessionStatus;
  duration_seconds?: number;
  scores?: ScoreBreakdown;
  events: TimelineEvent[];
  coaching?: CoachingResult;
}

export interface SessionResponse {
  id: string;
  status: SessionStatus;
  created_at: string;
}

// ─── UI-only types ────────────────────────────────────────────────────────────

export interface RadarDataPoint {
  subject: string;
  score: number;
  fullMark: number;
}

export const CATEGORY_COLORS: Record<EventCategory, string> = {
  voice:    '#4f9ef8',
  content:  '#a78bfa',
  presence: '#2dd4bf',
};

export const SEVERITY_COLORS: Record<EventSeverity, string> = {
  positive: '#4ade80',
  low:      '#4f9ef8',
  medium:   '#fb923c',
  high:     '#f87171',
};

export const SEVERITY_LABELS: Record<EventSeverity, string> = {
  positive: 'Great',
  low:      'Minor',
  medium:   'Moderate',
  high:     'Critical',
};

export function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function scoreColor(score: number): string {
  if (score >= 80) return '#4ade80';
  if (score >= 65) return '#4f9ef8';
  if (score >= 50) return '#fb923c';
  return '#f87171';
}

export function scoreLabel(score: number): string {
  if (score >= 85) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 55) return 'Fair';
  if (score >= 40) return 'Needs Work';
  return 'Poor';
}
