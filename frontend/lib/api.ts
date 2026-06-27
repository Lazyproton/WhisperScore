// WhisperScore — API Client
// All backend calls go through these typed functions.

import type { AnalysisResults, SessionResponse } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

/** Create a new analysis session. */
export async function createSession(): Promise<SessionResponse> {
  return apiFetch<SessionResponse>('/api/sessions', { method: 'POST' });
}

/** Upload a recording file for a session. */
export async function uploadRecording(
  sessionId: string,
  file: File,
  onProgress?: (pct: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/api/sessions/${sessionId}/upload`);

    if (onProgress) {
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      });
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Upload failed: ${xhr.statusText}`));
    };
    xhr.onerror = () => reject(new Error('Network error during upload'));
    xhr.send(form);
  });
}

/** Trigger analysis for an uploaded session. */
export async function triggerAnalysis(sessionId: string): Promise<void> {
  await apiFetch(`/api/sessions/${sessionId}/analyze`, { method: 'POST' });
}

/** Poll session status. */
export async function getSessionStatus(sessionId: string) {
  return apiFetch<{ id: string; status: string; error_message?: string }>(
    `/api/sessions/${sessionId}`,
  );
}

/** Get full analysis results. */
export async function getResults(sessionId: string): Promise<AnalysisResults> {
  return apiFetch<AnalysisResults>(`/api/sessions/${sessionId}/results`);
}

/** Get demo analysis results (no backend ML required). */
export async function getDemoResults(): Promise<AnalysisResults> {
  return apiFetch<AnalysisResults>('/api/demo');
}
