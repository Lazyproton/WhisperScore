"""
WhisperScore — MediaPipe Pose Analyzer
Analyzes body posture:
  - Shoulder alignment
  - Forward/backward lean
  - Head tilt
  - Overall posture score
"""
import logging
from typing import Optional, List
from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import Event, EventSeverity, presence_event

logger = logging.getLogger(__name__)
WINDOW_SEC = 10.0
FRAME_SKIP = 5
LEAN_THRESHOLD = 0.05
SHOULDER_TILT_THRESHOLD = 0.04


class PoseAnalyzer(BaseAnalyzer):
    name = "pose"

    def analyze(self, audio_path=None, video_path=None, **kwargs) -> AnalyzerResult:
        if not video_path:
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"posture_score": 75.0},
                events=[],
                summary="No video — skipping pose analysis",
            )

        import cv2
        import mediapipe as mp
        import numpy as np

        logger.info(f"Running Pose analysis on: {video_path}")
        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        frame_idx = 0
        posture_records = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % FRAME_SKIP != 0:
                frame_idx += 1
                continue

            t = frame_idx / fps
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(rgb)

            if result.pose_landmarks:
                lm = result.pose_landmarks.landmark
                LEFT_SHOULDER = mp_pose.PoseLandmark.LEFT_SHOULDER.value
                RIGHT_SHOULDER = mp_pose.PoseLandmark.RIGHT_SHOULDER.value
                NOSE = mp_pose.PoseLandmark.NOSE.value
                LEFT_HIP = mp_pose.PoseLandmark.LEFT_HIP.value
                RIGHT_HIP = mp_pose.PoseLandmark.RIGHT_HIP.value

                ls = lm[LEFT_SHOULDER]
                rs = lm[RIGHT_SHOULDER]
                nose = lm[NOSE]
                lh = lm[LEFT_HIP]
                rh = lm[RIGHT_HIP]

                shoulder_tilt = abs(ls.y - rs.y)
                shoulder_center_x = (ls.x + rs.x) / 2
                hip_center_x = (lh.x + rh.x) / 2
                lean = abs(shoulder_center_x - hip_center_x)

                # Head tilt from nose vs shoulder center
                nose_offset = abs(nose.x - shoulder_center_x)

                posture_records.append({
                    "t": t,
                    "shoulder_tilt": shoulder_tilt,
                    "lean": lean,
                    "head_offset": nose_offset,
                    "good": shoulder_tilt < SHOULDER_TILT_THRESHOLD and lean < LEAN_THRESHOLD,
                })

            frame_idx += 1

        cap.release()
        pose.close()

        if not posture_records:
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"posture_score": 50.0},
                events=[], summary="No body detected",
            )

        good_frames = sum(1 for r in posture_records if r["good"])
        posture_score = good_frames / len(posture_records) * 100

        events: List[Event] = []
        window_frames = max(1, int(WINDOW_SEC * fps / FRAME_SKIP))

        for i in range(0, len(posture_records), window_frames):
            window = posture_records[i: i + window_frames]
            if not window:
                continue
            t_start = window[0]["t"]
            avg_tilt = sum(r["shoulder_tilt"] for r in window) / len(window)
            avg_lean = sum(r["lean"] for r in window) / len(window)

            if avg_tilt > SHOULDER_TILT_THRESHOLD:
                events.append(presence_event(
                    timestamp=t_start, metric="posture",
                    title="Uneven Shoulders",
                    description=(
                        "Your shoulders appear uneven here. "
                        "Stand or sit with squared shoulders to project confidence."
                    ),
                    severity=EventSeverity.MEDIUM, score=55,
                ))
            if avg_lean > LEAN_THRESHOLD:
                events.append(presence_event(
                    timestamp=t_start, metric="posture",
                    title="Body Lean Detected",
                    description=(
                        "You're leaning to one side. "
                        "Center your weight to appear more grounded."
                    ),
                    severity=EventSeverity.LOW, score=65,
                ))

        if posture_score > 80:
            events.insert(0, presence_event(
                timestamp=0.0, metric="posture",
                title="Excellent Posture",
                description="Your overall posture is strong throughout the presentation.",
                severity=EventSeverity.POSITIVE, score=posture_score,
            ))

        metrics = {
            "posture_score": round(posture_score, 1),
            "frames_analyzed": len(posture_records),
        }

        return AnalyzerResult(
            analyzer_name=self.name, metrics=metrics, events=events,
            summary=f"Posture score: {posture_score:.1f}/100",
        )
