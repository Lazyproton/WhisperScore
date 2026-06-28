import sys
from core.pipeline import pipeline

video_path = "uploads/86939615-3c72-4b58-a6f8-f6a14bdc30dc/recording.webm"
session_dir = "uploads/86939615-3c72-4b58-a6f8-f6a14bdc30dc"

print("Running pipeline...")
results = pipeline.run(video_path=video_path, session_dir=session_dir)
print("Scores:")
print(results["scores"])
print("\nMetrics:")
for cat, m in results["metrics"].items():
    print(f"  {cat}: {m}")
print("\nPipeline execution successful!")
