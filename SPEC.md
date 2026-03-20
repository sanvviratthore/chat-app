# Feature Spec: Real-Time Group Chat

**Author:** Sanvi Rathore  
**Date:** March 2026  
**Status:** Approved — building now

---

## Problem Statement

Teams and communities need a lightweight way to communicate in real time without heavy setup. Existing solutions (Slack, Discord) are overkill for small groups. This feature delivers a minimal, self-hosted real-time chat system with multiple rooms and persistent message history.

---

## Scope

### In Scope
- Users join with a chosen username (no registration required)
- Multiple named chat rooms
- Real-time message delivery via WebSocket
- Last 50 messages loaded on room join (history persistence via SQLite)
- Online users list per room (live presence)
- System messages for join/leave events
- Clean, responsive web UI

### Out of Scope
- User authentication / accounts
- Direct messages (1:1)
- File/image sharing
- Message editing or deletion
- Push notifications
- Mobile native app

---

## Key Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Transport | WebSocket | Full-duplex, low latency, native browser support |
| Backend | FastAPI + WebSockets | Python comfort zone, async support built-in |
| Persistence | SQLite | Zero setup, sufficient for message history |
| Auth | Username only | Reduces scope, still demonstrates presence/identity |
| Frontend | Vanilla HTML/JS | No build step, fast iteration, no framework overhead |
| Rooms | Pre-defined list | Simpler than dynamic room creation for this scope |

---

## Architecture

```
Browser (HTML/JS)
    │
    │  WebSocket (ws://)
    ▼
FastAPI Backend
    │
    ├── ConnectionManager — tracks active WS connections per room
    ├── SQLite — persists messages for history on join
    └── Broadcast — fan-out messages to all room members
```

---

## API Design

| Endpoint | Type | Description |
|----------|------|-------------|
| `GET /` | HTTP | Serve login page |
| `GET /chat` | HTTP | Serve chat UI |
| `GET /api/rooms` | HTTP | List available rooms |
| `GET /api/rooms/{room}/history` | HTTP | Last 50 messages |
| `WS /ws/{room}/{username}` | WebSocket | Real-time chat connection |

---

## Message Protocol (JSON over WebSocket)

**Client → Server:**
```json
{ "type": "message", "text": "Hello!" }
```

**Server → Client:**
```json
{
  "type": "message",
  "username": "sanvi",
  "text": "Hello!",
  "room": "general",
  "timestamp": "2026-03-19T10:00:00Z"
}
```

**System events:**
```json
{ "type": "system", "text": "sanvi joined the room" }
{ "type": "users", "users": ["sanvi", "alex"] }
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Username conflicts | Append random suffix if username taken in room |
| Message flooding | 200-char limit per message, validated server-side |
| SQLite concurrency | Single-writer model acceptable for demo scale |
| Connection drops | Client auto-reconnect with exponential backoff |
