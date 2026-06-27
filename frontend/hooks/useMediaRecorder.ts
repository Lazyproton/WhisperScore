'use client';
import { useState, useRef, useCallback } from 'react';

export type RecordingState = 'idle' | 'countdown' | 'recording' | 'stopped' | 'uploading';

interface UseMediaRecorderReturn {
  state: RecordingState;
  countdown: number;
  elapsed: number;
  videoBlob: Blob | null;
  videoUrl: string | null;
  streamRef: React.RefObject<MediaStream | null>;
  previewRef: React.RefObject<HTMLVideoElement | null>;
  startCountdown: () => void;
  stopRecording: () => void;
  resetRecording: () => void;
  error: string | null;
}

export function useMediaRecorder(): UseMediaRecorderReturn {
  const [state, setState] = useState<RecordingState>('idle');
  const [countdown, setCountdown] = useState(3);
  const [elapsed, setElapsed] = useState(0);
  const [videoBlob, setVideoBlob] = useState<Blob | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const streamRef = useRef<MediaStream | null>(null);
  const previewRef = useRef<HTMLVideoElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720, facingMode: 'user' },
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;
      if (previewRef.current) {
        previewRef.current.srcObject = stream;
        previewRef.current.muted = true;
        previewRef.current.play();
      }

      // Pick best supported MIME
      const mimeType =
        MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
          ? 'video/webm;codecs=vp9,opus'
          : MediaRecorder.isTypeSupported('video/webm')
          ? 'video/webm'
          : 'video/mp4';

      const mr = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 2_500_000 });
      mediaRecorderRef.current = mr;
      chunksRef.current = [];

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        setVideoBlob(blob);
        setVideoUrl(URL.createObjectURL(blob));
        setState('stopped');
      };

      mr.start(1000); // collect chunks every second
      setState('recording');
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed((e) => e + 1);
      }, 1000);
    } catch (err) {
      setError(
        'Could not access camera/microphone. Please allow camera access in your browser settings.',
      );
      setState('idle');
    }
  }, []);

  const startCountdown = useCallback(() => {
    setError(null);
    setState('countdown');
    setCountdown(3);
    let count = 3;
    countdownRef.current = setInterval(() => {
      count -= 1;
      setCountdown(count);
      if (count <= 0) {
        clearInterval(countdownRef.current!);
        startRecording();
      }
    }, 1000);
  }, [startRecording]);

  const stopRecording = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    if (previewRef.current) previewRef.current.srcObject = null;
  }, []);

  const resetRecording = useCallback(() => {
    setVideoBlob(null);
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    setVideoUrl(null);
    setElapsed(0);
    setCountdown(3);
    setError(null);
    setState('idle');
    chunksRef.current = [];
  }, [videoUrl]);

  return {
    state,
    countdown,
    elapsed,
    videoBlob,
    videoUrl,
    streamRef,
    previewRef,
    startCountdown,
    stopRecording,
    resetRecording,
    error,
  };
}
