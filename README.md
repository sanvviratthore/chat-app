# Chatly -> Real-Time Group Chat

A real-time group chat app built with FastAPI WebSockets and vanilla JS.

## Live Demo

https://chat-app-2-th9p.onrender.com/

---

## Features

- Real-time messaging via WebSocket
- 3 chat rooms: general, tech, random
- Message history (last 50 messages on join)
- Live online users list with presence
- Auto-reconnect with exponential backoff
- Username uniqueness per room
- No sign-up needed just pick a name and join
- XSS-safe all user content via `textContent`

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Backend | FastAPI + WebSockets | Async, Python-native WebSocket support |
| Database | SQLite | Zero setup, message history persistence |
| Frontend | Vanilla HTML/JS | No build step, fast iteration |
| State | In-memory ConnectionManager | Sufficient for single-instance demo |

## Setup

```bash
cd chat-app
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

Visit http://localhost:8000

## Project Structure

```
chat-app/
├── backend/
│   ├── main.py          # FastAPI app, WebSocket handler, ConnectionManager
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Join page
│   └── chat.html        # Chat UI
├── SPEC.md              # Feature spec (written before building)
├── POST_SHIP.md         # Post-ship reflection
└── README.md
```

## Deployment

### Render
1. New Web Service → connect repo
2. Root Directory: `backend`
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
