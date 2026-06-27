# WhisperScore — AI Public Speaking & Debate Coach

> Record → Analyze → Improve. Seven AI analyzers. Timestamp-precise coaching.

---

## What it does

WhisperScore analyzes a recorded presentation across three dimensions and pinpoints coaching feedback at exact timestamps:

| Dimension | Tools | Outputs |
|-----------|-------|---------|
| **Content** | Groq LLM (LLaMA 3) | Clarity, structure, argument strength, persuasiveness |
| **Voice** | faster-whisper · Silero VAD · librosa · Parselmouth | WPM, fillers, pauses, pitch variation, loudness |
| **Presence** | MediaPipe Face Mesh · MediaPipe Pose | Eye contact %, head pose, posture score |

---

## Architecture

```
Here_goes_nothing/
├── backend/        # FastAPI + 7 concurrent ML analyzers
│   ├── analyzers/  # Plugin-based: add new analyzers without touching existing code
│   ├── core/       # Config, FFmpeg pipeline orchestrator
│   ├── api/        # REST endpoints (upload, analyze, results, demo)
│   └── models/     # SQLAlchemy (SQLite default, PostgreSQL-ready)
│
└── frontend/       # Next.js 14 + Tailwind v4
    ├── app/        # Landing, Record, Analysis/[id], Demo pages
    ├── components/ # ScoreCard, RadarChart, InteractiveTimeline, VideoReplay, CoachingPanel
    └── hooks/      # useMediaRecorder, useAnalysis
```

---

## Prerequisites

```bash
# Required system tools
brew install ffmpeg     # Audio/video extraction (required)

# Python 3.11+
python --version

# Node.js 18+
node --version
```

---

## Quick Start

### 1. Backend

```bash
cd backend

# Install Python dependencies (first time: downloads ~2GB of ML models)
pip install -r requirements.txt

# Create your env file
cp .env.example .env
# Edit .env — add your GROQ_API_KEY for AI coaching
# Get a free key at https://console.groq.com

# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.  
Swagger docs: `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## Demo Mode

The app includes a fully pre-computed demo that works **without any backend setup**:

```
http://localhost:3000/demo
```

This shows a complete 3-minute presentation analysis with all components populated.

---

## Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sessions` | Create a new session |
| POST | `/api/sessions/{id}/upload` | Upload recording file |
| POST | `/api/sessions/{id}/analyze` | Start background analysis |
| GET | `/api/sessions/{id}` | Poll status |
| GET | `/api/sessions/{id}/results` | Fetch full results |
| GET | `/api/demo` | Pre-computed demo results |

---

## Scoring Weights

| Category | Weight | Inputs |
|----------|--------|--------|
| Content | 35% | LLM clarity, organization, logic, persuasion |
| Voice | 35% | WPM, fillers, pauses, pitch, loudness |
| Presence | 30% | Eye contact %, posture score |

---

## Adding a New Analyzer

1. Create `backend/analyzers/your_category/your_analyzer.py`
2. Subclass `BaseAnalyzer` and implement `analyze()`
3. Return an `AnalyzerResult` with `events` and `metrics`
4. Add it to `core/pipeline.py` — no other files need changing

```python
class MyAnalyzer(BaseAnalyzer):
    name = "my_analyzer"
    
    def analyze(self, audio_path=None, video_path=None, **kwargs):
        ...
        return AnalyzerResult(
            analyzer_name=self.name,
            metrics={"my_score": 85},
            events=[voice_event(timestamp=12.5, ...)],
        )
```

---

## Environment Variables

### Backend (`backend/.env`)
```
DATABASE_URL=sqlite:///./whisperscore.db
GROQ_API_KEY=your_key_here          # https://console.groq.com (free)
GROQ_MODEL=llama-3.1-8b-instant
WHISPER_MODEL_SIZE=base             # tiny/base/small/medium/large-v3
```

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Tech Stack

**Backend:** FastAPI · SQLAlchemy · faster-whisper · Silero VAD · librosa · Parselmouth · MediaPipe · Groq SDK · FFmpeg  
**Frontend:** Next.js 14 · Tailwind CSS v4 · Recharts · Framer Motion · Lucide React

---

## License

MIT
