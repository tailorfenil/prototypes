# Passwordless Authentication (Magic Link) – FastAPI

This project implements a **passwordless authentication system** using **magic email links**.  
It demonstrates how real-world systems separate **identity proof** from **session management** using the right storage technologies.

The design mirrors patterns used in production systems at companies like Notion, Slack, and Stripe.

---

## ✨ What this project does

Users authenticate without passwords:

1. User submits their email address
2. Server generates a **short-lived, single-use magic link**
3. User clicks the link
4. Server verifies the link and creates a **24-hour session**
5. Session is enforced via **HTTP-only cookies**

---

## 🧠 Core design idea

Authentication is split into **two distinct phases**:

### Phase A — Identity proof (Magic Link)
- Purpose: *Prove control of an email address*
- Stored in: **Postgres**
- Properties:
  - Durable
  - Auditable
  - One-time
  - Race-safe
- Tokens are **hashed at rest** for security

### P Session (Logged-in state)
- Purpose: *Authorize requests after login*
- Stored in: **Redis**
- Properties:
  - Fast
  - Ephemeral (TTL-based)
  - Revocable
- Enforced using **HTTP-only cookies**

⚠️ These two phases are intentionally separated and should **not** be mixed.

---

## 🏗 Architecture

Client (Browser / curl)
|
v
FastAPI Application
|
+--> Postgres (users, magic_tokens)
|
+--> Redis (sessions)


- **Postgres**: source of truth for identity events
- **Redis**: fast runtime session validation
- **Cookies**: secure transport for session identifiers

---

## 🔐 Security properties

- Magic links:
  - Single-use
  - Expire after 5 minutes
  - Cannot be replayed
- Tokens:
  - Generated using cryptographically secure randomness
  - Stored only as hashes in the database
- Sessions:
  - Stored server-side (not in JWTs)
  - Auto-expire after 24 hours
  - Invalidated on re-login
- Cookies:
  - `HttpOnly`
  - Not accessible to JavaScript
  - Protect against XSS-based session theft

---

## 🚀 How to run the project

### Prerequisites
- Docker
- Docker Compose

No local Postgres or Redis installation is required.

---

### 1️⃣ Start the system

From the project root:

```bash
docker compose up --build
```

You should see:
Uvicorn running on http://0.0.0.0:8000


### 2️⃣ Request a magic link

```bash
curl -X POST http://localhost:8000/auth/magic/request \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```

You’ll see a printed magic link:
Magic link → http://localhost:8000/auth/magic/consume?token=...

### 3️⃣ Consume the magic link

```bash
curl -i "http://localhost:8000/auth/magic/consume?token=PASTE_TOKEN"
```

This sets an authentication cookie (sid).

🔄 Possible extensions
Multi-device session support
Logout endpoint
Session metadata (IP, user-agent)
Rate limiting magic link requests
Global session revocation
Porting the same design to Go


