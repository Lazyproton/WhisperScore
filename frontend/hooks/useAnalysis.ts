'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import type { AnalysisResults, SessionStatus } from '@/lib/types';
import { createSession, uploadRecording, triggerAnalysis, getSessionStatus, getResults } from '@/lib/api';

interface UseAnalysisReturn {
  sessionId: string | null;
  status: SessionStatus | null;
  results: AnalysisResults | null;
  uploadProgress: number;
  error: string | null;
  submitRecording: (blob: Blob, filename?: string) => Promise<void>;
}

const POLL_INTERVAL_MS = 2000;

export function useAnalysis(): UseAnalysisReturn {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<SessionStatus | null>(null);
  const [results, setResults] = useState<AnalysisResults | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) clearInterval(pollRef.current);
  }, []);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const submitRecording = useCallback(async (blob: Blob, filename = 'recording.webm') => {
    setError(null);
    setUploadProgress(0);
    try {
      // 1. Create session
      const session = await createSession();
      setSessionId(session.id);
      setStatus('uploading');

      // 2. Upload file
      const file = new File([blob], filename, { type: blob.type });
      await uploadRecording(session.id, file, setUploadProgress);

      // 3. Trigger analysis
      await triggerAnalysis(session.id);
      setStatus('analyzing');

      // 4. Poll until complete or failed
      pollRef.current = setInterval(async () => {
        try {
          const s = await getSessionStatus(session.id);
          setStatus(s.status as SessionStatus);

          if (s.status === 'complete') {
            stopPolling();
            const r = await getResults(session.id);
            setResults(r);
          } else if (s.status === 'failed') {
            stopPolling();
            setError(s.error_message ?? 'Analysis failed. Please try again.');
          }
        } catch {
          // Transient network error — keep polling
        }
      }, POLL_INTERVAL_MS);
    } catch (err) {
      setError((err as Error).message ?? 'An unexpected error occurred.');
      setStatus(null);
    }
  }, [stopPolling]);

  return { sessionId, status, results, uploadProgress, error, submitRecording };
}
