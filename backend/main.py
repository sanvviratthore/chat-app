import json
import sqlite3
import os
from datetime import datetime, timezone
from typing import Dict, List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# ── Database setup ─────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "chat.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            room      TEXT NOT NULL,
            username  TEXT NOT NULL,
            text      TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_message(room: str, username: str, text: str, timestamp: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO messages (room, username, text, timestamp) VALUES (?, ?, ?, ?)",
        (room, username, text, timestamp)
    )
    conn.commit()
    conn.close()

def get_history(room: str, limit: int = 50) -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT username, text, timestamp FROM messages WHERE room = ? ORDER BY id DESC LIMIT ?",
        (room, limit)
    ).fetchall()
    conn.close()
    return [
        {"type": "message", "username": r[0], "text": r[1], "timestamp": r[2], "room": room}
        for r in reversed(rows)
    ]


# ── Rooms ──────────────────────────────────────────────────────────────────────
ROOMS = [
    {"id": "general",   "name": "# general",   "description": "General discussion"},
    {"id": "tech",      "name": "# tech",       "description": "Tech talk"},
    {"id": "random",    "name": "# random",     "description": "Off-topic fun"},
]
ROOM_IDS = {r["id"] for r in ROOMS}


# ── Connection Manager ─────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        # room_id -> {username: websocket}
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}

    def get_users(self, room: str) -> List[str]:
        return list(self.rooms.get(room, {}).keys())

    def resolve_username(self, room: str, username: str) -> str:
        """Ensure username is unique in the room."""
        taken = self.get_users(room)
        if username not in taken:
            return username
        import random, string
        suffix = ''.join(random.choices(string.digits, k=3))
        return f"{username}_{suffix}"

    async def connect(self, room: str, username: str, ws: WebSocket) -> str:
        await ws.accept()
        if room not in self.rooms:
            self.rooms[room] = {}
        unique = self.resolve_username(room, username)
        self.rooms[room][unique] = ws
        return unique

    def disconnect(self, room: str, username: str):
        if room in self.rooms:
            self.rooms[room].pop(username, None)

    async def broadcast(self, room: str, message: dict, exclude: str = None):
        if room not in self.rooms:
            return
        dead = []
        for uname, ws in self.rooms[room].items():
            if uname == exclude:
                continue
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(uname)
        for uname in dead:
            self.rooms[room].pop(uname, None)

    async def send_to(self, ws: WebSocket, message: dict):
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            pass

    async def broadcast_users(self, room: str):
        users = self.get_users(room)
        await self.broadcast(room, {"type": "users", "users": users})


manager = ConnectionManager()


# ── App ────────────────────────────────────────────────────────────────────────
init_db()

app = FastAPI(title="ChatApp", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/", include_in_schema=False)
def serve_index():
    p = os.path.join(frontend_dir, "index.html")
    return FileResponse(p)

@app.get("/chat", include_in_schema=False)
def serve_chat():
    p = os.path.join(frontend_dir, "chat.html")
    return FileResponse(p)


# ── REST endpoints ─────────────────────────────────────────────────────────────
@app.get("/api/rooms")
def list_rooms():
    return ROOMS

@app.get("/api/rooms/{room}/history")
def room_history(room: str):
    if room not in ROOM_IDS:
        raise HTTPException(status_code=404, detail="Room not found.")
    return get_history(room)


# ── WebSocket ──────────────────────────────────────────────────────────────────
@app.websocket("/ws/{room}/{username}")
async def websocket_endpoint(ws: WebSocket, room: str, username: str):
    if room not in ROOM_IDS:
        await ws.close(code=4004)
        return

    # Sanitize username
    username = username.strip()[:32]
    if not username:
        await ws.close(code=4001)
        return

    unique_username = await manager.connect(room, username, ws)

    try:
        # Send message history
        history = get_history(room)
        for msg in history:
            await manager.send_to(ws, msg)

        # Announce join
        join_msg = {
            "type": "system",
            "text": f"{unique_username} joined the room",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await manager.broadcast(room, join_msg)
        await manager.send_to(ws, {
            "type": "system",
            "text": f"Welcome, {unique_username}! You're in #{room}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Broadcast updated user list
        await manager.broadcast_users(room)

        # Message loop
        while True:
            raw = await ws.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if data.get("type") != "message":
                continue

            text = str(data.get("text", "")).strip()

            # Validate
            if not text:
                continue
            if len(text) > 200:
                await manager.send_to(ws, {
                    "type": "error",
                    "text": "Message too long (max 200 characters).",
                })
                continue

            timestamp = datetime.now(timezone.utc).isoformat()
            msg = {
                "type": "message",
                "username": unique_username,
                "text": text,
                "room": room,
                "timestamp": timestamp,
            }

            # Persist
            save_message(room, unique_username, text, timestamp)

            # Broadcast to everyone including sender
            await manager.broadcast(room, msg)
            await manager.send_to(ws, msg)

    except WebSocketDisconnect:
        manager.disconnect(room, unique_username)
        leave_msg = {
            "type": "system",
            "text": f"{unique_username} left the room",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await manager.broadcast(room, leave_msg)
        await manager.broadcast_users(room)