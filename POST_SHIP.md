# Post-Ship Note: Real-Time Group Chat

**Shipped:** March 2026  
**Time taken:** ~6 hours (within the 72-hour window)

---

## What I Built

A real-time group chat application with:
- WebSocket-based messaging with sub-100ms delivery
- 3 chat rooms (general, tech, random)
- Message history (last 50 messages loaded on join)
- Live online users list with presence updates
- Username uniqueness enforcement per room
- Auto-reconnect with exponential backoff
- Clean dark UI with grouped messages and avatar colors

---

## What I Would Improve

**1. Authentication**  
Username-only identity is fine for a demo but weak in production. I'd add JWT-based auth so users have persistent identities and can't impersonate others.

**2. Redis for connection state**  
The ConnectionManager is in-memory, which means it doesn't work across multiple server instances. Swapping to Redis pub/sub would make this horizontally scalable.

**3. Message pagination**  
Currently loads last 50 messages on join. A proper "load more" with cursor-based pagination would handle rooms with long history.

**4. Rate limiting on WebSocket messages**  
I added a 200-char limit but no per-user message rate limit. A bad actor could flood the room. I'd add a server-side token bucket per connection.

**5. Room persistence**  
Rooms are currently hardcoded. Dynamic room creation with a room discovery API would make this more useful.

---

## What Took Longer Than Expected

- **WebSocket reconnect logic** — getting exponential backoff right while avoiding duplicate connections took more iteration than expected.
- **Message grouping UI** — deciding when to group consecutive messages from the same user (and resetting on system messages) had a few edge cases.

---

## What I Learned

- FastAPI's WebSocket support is excellent — the async model maps cleanly to broadcast patterns.
- Browser WebSocket auto-reconnect isn't built in — you have to implement it yourself carefully.
- In-memory state for a chat server is fine at small scale but needs careful thought for production (server restarts lose all active connections).

---

## Known Limitations

- No authentication — usernames can conflict (mitigated by auto-suffix)
- In-memory state resets on server restart
- SQLite not suitable for high write throughput at scale
- No end-to-end encryption
