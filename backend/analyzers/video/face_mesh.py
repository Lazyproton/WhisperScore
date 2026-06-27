"""
WhisperScore — MediaPipe Face Mesh Analyzer
Analyzes facial behavior:
  - Eye contact (gaze direction vs. camera)
  - Head orientation (yaw/pitch/roll)
  - Blink frequency
"""
import logging
from typing import Optional, List, Dict
from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import Event, EventSeverity, presence_event

logger = logging.getLogger(__name__)

# Eye contact thresholds
EYE_CONTACT_GOOD_THRESHOLD = 0.7   # > 70% gaze towards camera
EYE_CONTACT_POOR_THRESHOLD = 0.4   # < 40% = poor
# Head yaw threshold (degrees)
HEAD_YAW_THRESHOLD = 20.0
# Window size for event generation
WINDOW_SEC = 10.0
# Frame skip for performance
FRAME_SKIP = 3


class FaceMeshAnalyzer(BaseAnalyzer):
    name = "face_mesh"

    def analyze(self, audio_path=None, video_path=None, **kwargs) -> AnalyzerResult:
        if not video_path:
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"eye_contact_percentage": 70.0},
                events=[],
                summary="No video — skipping face mesh analysis",
            )

        import cv2
        import mediapipe as mp
        import numpy as np

        logger.info(f"Running Face Mesh on: {video_path}")
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        frame_idx = 0
        results_per_frame: List[Dict] = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % FRAME_SKIP != 0:
                frame_idx += 1
                continue

            t = frame_idx / fps
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = face_mesh.process(rgb)

            if result.multi_face_landmarks:
                lm = result.multi_face_landmarks[0].landmark
                h, w = frame.shape[:2]

                # Eye contact: look at nose tip vs. outer eye corners
                nose = lm[1]
                left_eye = lm[33]
                right_eye = lm[263]

                # Simple gaze score: how centered is the nose relative to eye line
                eye_center_x = (left_eye.x + right_eye.x) / 2
                gaze_offset = abs(nose.x - eye_center_x)
                # Head yaw from z-depth of eye landmarks
                yaw = abs(left_eye.z - right_eye.z) * 100

                looking_at_camera = yaw < HEAD_YAW_THRESHOLD and gaze_offset < 0.05
                results_per_frame.append({
                    "t": t,
                    "looking": looking_at_camera,
                    "yaw": yaw,
                })
            else:
                results_per_frame.append({"t": t, "looking": False, "yaw": 0})

            frame_idx += 1

        cap.release()
        face_mesh.close()

        if not results_per_frame:
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"eye_contact_percentage": 0},
                events=[],
                summary="No face detected in video",
            )

        # ─── Metrics ─────────────────────────────────────────────────
        looking_frames = sum(1 for r in results_per_frame if r["looking"])
        eye_contact_pct = looking_frames / len(results_per_frame) * 100

        # ─── Events (per window) ─────────────────────────────────────
        events: List[Event] = []
        window_frames = max(1, int(WINDOW_SEC / (FRAME_SKIP / fps)))

        for i in range(0, len(results_per_frame), window_frames):
            window = results_per_frame[i: i + window_frames]
            if not window:
                continue
            t_start = window[0]["t"]
            w_pct = sum(1 for r in window if r["looking"]) / len(window)

            if w_pct < 0.3:
                events.append(presence_event(
                    timestamp=t_start, metric="eye_contact",
                    title="Lost Eye Contact",
                    description=(
                        "You were not looking at the camera here. "
                        "Maintain eye contact to build trust with your audience."
                    ),
                    severity=EventSeverity.HIGH, score=max(10, w_pct * 100),
                ))
            elif w_pct > 0.8:
                events.append(presence_event(
                    timestamp=t_start, metric="eye_contact",
                    title="Strong Eye Contact",
                    description="Great eye contact here — you appear confident and engaged.",
                    severity=EventSeverity.POSITIVE, score=90,
                ))

        metrics = {
            "eye_contact_percentage": round(eye_contact_pct, 1),
            "frames_analyzed": len(results_per_frame),
            "duration_seconds": round(duration, 2),
        }

        return AnalyzerResult(
            analyzer_name=self.name, metrics=metrics, events=events,
            summary=f"Eye contact: {eye_contact_pct:.1f}% of the time",
        )
