import logging
import math
import os
import sys
import numpy as np
import cv2
from typing import List, Dict, Optional

from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import EventSeverity, presence_event

logger = logging.getLogger(__name__)

# Add OpenSeeFace vendor directory to sys.path
vendor_path = os.path.join(os.path.dirname(__file__), "openseeface", "vendor")
if vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

try:
    from tracker import Tracker
except ImportError as e:
    logger.error(f"Failed to import OpenSeeFace tracker: {e}")
    Tracker = None

# Thresholds
YAW_TOLERANCE = 25.0
PITCH_TOLERANCE = 20.0
BLINK_THRESHOLD = 0.30
WINDOW_SEC = 8.0
FRAME_SKIP = 3

class FaceAnalyzer(BaseAnalyzer):
    name = "face"

    def analyze(self, audio_path=None, video_path=None, **kwargs) -> AnalyzerResult:
        if not video_path or not os.path.exists(video_path):
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"eye_contact_percentage": 0.0},
                events=[],
                summary="No video provided.",
                success=False
            )

        if Tracker is None:
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"eye_contact_percentage": 0.0},
                events=[],
                summary="OpenSeeFace Tracker not available.",
                success=False
            )

        logger.info(f"[{self.name}] Running OpenSeeFace analysis on: {video_path}")
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        model_dir = os.path.join(vendor_path, "models")
        tracker = Tracker(
            width, height,
            threshold=0.6,
            max_threads=1,
            max_faces=1,
            discard_after=10,
            scan_every=3,
            silent=True,
            model_type=3,
            model_dir=model_dir,
            no_gaze=False,
            detection_threshold=0.6,
            use_retinaface=0,
            max_feature_updates=900,
            static_model=False,
            feature_level=2
        )

        frame_idx = 0
        frame_data: List[Dict] = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % FRAME_SKIP != 0:
                frame_idx += 1
                continue

            t = frame_idx / fps
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            faces = tracker.predict(rgb)
            
            if len(faces) > 0:
                face = faces[0]
                yaw, pitch, roll = face.euler
                
                # Eye blink (0.0 to 1.0, > 0.3 usually means open)
                eye_l_open = face.eye_blink[1] if face.eye_blink else 1.0
                eye_r_open = face.eye_blink[0] if face.eye_blink else 1.0
                blink = eye_l_open < BLINK_THRESHOLD and eye_r_open < BLINK_THRESHOLD
                
                # Eye contact (head pose + gaze)
                looking = abs(yaw) <= YAW_TOLERANCE and abs(pitch) <= PITCH_TOLERANCE
                
                # Mouth openness
                mouth_open = face.current_features.get("mouth_open", 0.0) if face.current_features else 0.0

                frame_data.append({
                    "t": t,
                    "looking": looking,
                    "blink": blink,
                    "yaw": yaw,
                    "pitch": pitch,
                    "mouth_open": mouth_open
                })
            else:
                frame_data.append({
                    "t": t, "looking": False, "blink": False,
                    "yaw": 0.0, "pitch": 0.0, "mouth_open": 0.0
                })
                
            frame_idx += 1
            
        cap.release()
        
        if not frame_data:
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"eye_contact_percentage": 0.0},
                events=[],
                summary="No frames analyzed."
            )

        # Aggregate Metrics
        total = len(frame_data)
        looking_n = sum(1 for f in frame_data if f["looking"])
        eye_contact_pct = (looking_n / total) * 100

        blinks, in_blink = 0, False
        for f in frame_data:
            if f["blink"] and not in_blink:
                blinks += 1
                in_blink = True
            elif not f["blink"]:
                in_blink = False
                
        duration_min = max(0.1, (frame_idx / fps) / 60.0)
        blink_rate_bpm = blinks / duration_min

        # Generate Events
        events = []
        
        window_size = int((WINDOW_SEC * fps) / FRAME_SKIP)
        for i in range(0, total, window_size):
            chunk = frame_data[i : i + window_size]
            if not chunk:
                continue
                
            chunk_looking = sum(1 for f in chunk if f["looking"])
            chunk_pct = chunk_looking / len(chunk)
            t_start = chunk[0]["t"]
            
            if chunk_pct < 0.4:
                events.append(presence_event(
                    timestamp=t_start,
                    metric="Eye Contact",
                    score=chunk_pct * 100,
                    severity=EventSeverity.HIGH,
                    title="Lost Eye Contact",
                    description="You looked away from the audience for an extended period."
                ))
            elif chunk_pct > 0.85:
                events.append(presence_event(
                    timestamp=t_start,
                    metric="Eye Contact",
                    score=chunk_pct * 100,
                    severity=EventSeverity.POSITIVE,
                    title="Strong Engagement",
                    description="Excellent sustained eye contact with the audience."
                ))
                
        if blink_rate_bpm > 35:
            events.append(presence_event(
                timestamp=0.0,
                metric="Blink Rate",
                score=blink_rate_bpm,
                severity=EventSeverity.MEDIUM,
                title="Excessive Blinking",
                description=f"Blink rate was very high ({blink_rate_bpm:.1f} bpm), indicating possible nervousness."
            ))

        return AnalyzerResult(
            analyzer_name=self.name,
            metrics={
                "eye_contact_percentage": eye_contact_pct,
                "blink_rate_bpm": blink_rate_bpm
            },
            events=events,
            summary=f"Face Analysis complete: {eye_contact_pct:.1f}% eye contact, {blink_rate_bpm:.1f} blinks/min"
        )
