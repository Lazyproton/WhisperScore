from analyzers.video.gesture import GestureAnalyzer
import json
import logging

logging.basicConfig(level=logging.INFO)
video_path = "uploads/86939615-3c72-4b58-a6f8-f6a14bdc30dc/recording.webm"

gesture = GestureAnalyzer()
res = gesture.analyze(video_path=video_path)
print(json.dumps(res.metrics, indent=2))
print(json.dumps([e.to_dict() for e in res.events], indent=2))
