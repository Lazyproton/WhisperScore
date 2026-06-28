import asyncio
from analyzers.video.face import FaceAnalyzer
from analyzers.video.gesture import GestureAnalyzer
from analyzers.video.grlib_plugin import GRLibAnalyzer

video_path = "uploads/86939615-3c72-4b58-a6f8-f6a14bdc30dc/recording.webm"

print("Testing FaceAnalyzer...")
face = FaceAnalyzer()
res = face.analyze(video_path=video_path)
print(res.metrics)
print([e.title for e in res.events])

print("\nTesting GestureAnalyzer...")
gesture = GestureAnalyzer()
res = gesture.analyze(video_path=video_path)
print(res.metrics)
print([e.title for e in res.events])

