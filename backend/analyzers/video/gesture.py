import logging
import math
import os
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple

from analyzers.base import BaseAnalyzer, AnalyzerResult
from analyzers.timeline.events import EventSeverity, presence_event

logger = logging.getLogger(__name__)

# RTMPose WholeBody Keypoint Indices (COCO 17 for body)
L_SHOULDER = 5
R_SHOULDER = 6
L_ELBOW = 7
R_ELBOW = 8
L_WRIST = 9
R_WRIST = 10

# Thresholds
WINDOW_SEC = 8.0
FRAME_SKIP = 4
CONFIDENCE_THRESH = 0.4
FIDGET_WRIST_THRESH = 0.025
HIDDEN_THRESH = 0.60

class GestureAnalyzer(BaseAnalyzer):
    name = "gesture"

    def analyze(self, audio_path=None, video_path=None, **kwargs) -> AnalyzerResult:
        if not video_path or not os.path.exists(video_path):
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"gesture_score": 0.0},
                events=[],
                summary="No video provided.",
                success=False
            )

        try:
            from rtmlib import Wholebody
        except ImportError:
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"gesture_score": 0.0},
                events=[],
                summary="rtmlib not installed.",
                success=False
            )

        logger.info(f"[{self.name}] Running RTMPose analysis on: {video_path}")
        wb = Wholebody(to_openpose=False, backend='onnxruntime', device='cpu')
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        frame_idx = 0
        frame_data: List[Dict] = []
        prev_wrist_l = None
        prev_wrist_r = None
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % FRAME_SKIP != 0:
                frame_idx += 1
                continue
                
            t = frame_idx / fps
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            keypoints, scores = wb(rgb)
            
            if keypoints is not None and len(keypoints) > 0:
                # Take the primary person (assumes single speaker)
                kpts = keypoints[0]
                sc = scores[0]
                
                wl = kpts[L_WRIST] if sc[L_WRIST] > CONFIDENCE_THRESH else None
                wr = kpts[R_WRIST] if sc[R_WRIST] > CONFIDENCE_THRESH else None
                
                # Normalize points
                if wl is not None: wl = (wl[0]/width, wl[1]/height)
                if wr is not None: wr = (wr[0]/width, wr[1]/height)
                
                # Calculate wrist displacement (fidgeting)
                disp_l = math.hypot(wl[0] - prev_wrist_l[0], wl[1] - prev_wrist_l[1]) if wl and prev_wrist_l else 0
                disp_r = math.hypot(wr[0] - prev_wrist_r[0], wr[1] - prev_wrist_r[1]) if wr and prev_wrist_r else 0
                wrist_disp = (disp_l + disp_r) / 2.0
                
                prev_wrist_l = wl
                prev_wrist_r = wr
                
                hands_visible = wl is not None or wr is not None
                
                # Crossed arms heuristic (wrists are swapped relative to shoulders)
                sl = kpts[L_SHOULDER]
                sr = kpts[R_SHOULDER]
                crossed = False
                if wl and wr and sc[L_SHOULDER] > CONFIDENCE_THRESH and sc[R_SHOULDER] > CONFIDENCE_THRESH:
                    # In pixel coords, right shoulder is usually lower x than left shoulder.
                    # If left wrist x is less than right wrist x, they are crossed
                    if wl[0] < wr[0]: 
                        crossed = True
                        
                frame_data.append({
                    "t": t,
                    "visible": hands_visible,
                    "wrist_disp": wrist_disp,
                    "crossed": crossed
                })
            else:
                prev_wrist_l = None
                prev_wrist_r = None
                frame_data.append({
                    "t": t,
                    "visible": False,
                    "wrist_disp": 0.0,
                    "crossed": False
                })
                
            frame_idx += 1
            
        cap.release()
        
        if not frame_data:
            return AnalyzerResult(
                analyzer_name=self.name,
                metrics={"gesture_score": 50.0},
                events=[],
                summary="No poses detected."
            )

        # Session Metrics
        total = len(frame_data)
        vis_frames = [f for f in frame_data if f["visible"]]
        vis_pct = len(vis_frames) / total * 100
        avg_wrist_disp = float(np.mean([f["wrist_disp"] for f in vis_frames])) if vis_frames else 0.0
        
        gesture_score = 50.0
        gesture_score += min(40, vis_pct * 0.4)
        if avg_wrist_disp > FIDGET_WRIST_THRESH:
            gesture_score -= 10
            
        gesture_score = round(min(100, max(0, gesture_score)), 1)
        
        # Events
        events = []
        win_n = max(1, int(WINDOW_SEC * fps / FRAME_SKIP))
        
        for i in range(0, total, win_n):
            win = frame_data[i: i + win_n]
            if not win:
                continue
                
            t0 = win[0]["t"]
            w_vis = sum(1 for f in win if f["visible"]) / len(win)
            
            if w_vis < (1 - HIDDEN_THRESH):
                events.append(presence_event(
                    timestamp=t0,
                    metric="Gestures",
                    score=50,
                    severity=EventSeverity.MEDIUM,
                    title="Hands Not Visible",
                    description="Hands were mostly out of frame. Keeping hands visible adds energy."
                ))
                continue
                
            w_disp = float(np.mean([f["wrist_disp"] for f in win if f["visible"]] or [0]))
            if w_disp > FIDGET_WRIST_THRESH:
                events.append(presence_event(
                    timestamp=t0,
                    metric="Gestures",
                    score=45,
                    severity=EventSeverity.MEDIUM,
                    title="Excessive Movement",
                    description="High wrist movement variance detected. This can be distracting."
                ))
                
            w_crossed = sum(1 for f in win if f["crossed"]) / len(win)
            if w_crossed > 0.5:
                events.append(presence_event(
                    timestamp=t0,
                    metric="Posture",
                    score=30,
                    severity=EventSeverity.HIGH,
                    title="Closed Posture",
                    description="Crossed arms detected. This signals closed-off body language."
                ))

        return AnalyzerResult(
            analyzer_name=self.name,
            metrics={
                "gesture_score": gesture_score,
                "hands_visible_pct": round(vis_pct, 1),
                "avg_wrist_disp": round(avg_wrist_disp, 4)
            },
            events=events,
            summary=f"Gesture score: {gesture_score}/100 | Hands visible: {vis_pct:.1f}%"
        )
