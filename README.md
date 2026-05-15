# Analytics Platform

A real-time analytics and reporting platform — lightweight Mixpanel/Metabase alternative built as a technical assessment for Wexa AI.

## Live Demo

- **Frontend:** https://analytics-frontend-one.vercel.app
- **Backend API:** https://analytics-backend-h41f.onrender.com
- **Health Check:** https://analytics-backend-h41f.onrender.com/api/v1/auth/health/

> Note: Backend is on Render free tier — first request may take 30s to wake up.

---

## What It Does

Companies instrument their apps by sending events via REST API. Events flow into dashboards in real-time. Alert rules trigger notifications when thresholds are exceeded. Full multi-tenant RBAC with team management.

---

## System Design

```
                        ┌─────────────────────────────────┐
                        │         Client Browser           │
                        │      Next.js 14 Frontend         │
                        │   (Vercel — analytics-frontend)  │
                        └──────────────┬──────────────────┘
                                       │
                          HTTPS + JWT cookies
                          X-Organization-ID header
                                       │
                        ┌──────────────▼──────────────────┐
                        │         Render Web Service       │
                        │    Gunicorn (2 workers, sync)    │
                        │    Django REST Framework         │
                        │                                 │
                        │  ┌─────────────────────────┐   │
                        │  │   Request Pipeline       │   │
                        │  │  CorsMiddleware          │   │
                        │  │  SessionMiddleware       │   │
                        │  │  RequestLoggingMiddleware│   │
                        │  │  OrganizationMiddleware  │   │
                        │  │         ↓               │   │
                        │  │  CookieJWTAuthentication │   │
                        │  │  APIKeyAuthentication    │   │
                        │  │         ↓               │   │
                        │  │  IsViewer/Analyst/Admin  │   │
                        │  │  /Owner Permission Class │   │
                        │  └─────────────────────────┘   │
                        └──────┬───────────────┬──────────┘
                               │               │
               ┌───────────────▼──┐    ┌───────▼──────────────┐
               │  Neon PostgreSQL  │    │   Upstash Redis       │
               │  users           │    │  Celery task queue    │
               │  organizations   │    │  Django cache         │
               │  members         │    │  Channel layer (WS)   │
               │  events          │    └───────┬──────────────┘
               │  dashboards      │            │
               │  alert_rules     │    ┌───────▼──────────────┐
               │  api_keys        │    │  Render BG Worker 1  │
               │  invites         │    │  Celery Worker        │
               └──────────────────┘    │  concurrency=2        │
                                       │  • CSV processing     │
                                       │  • WS notifications   │
                                       │  • Alert dispatch     │
                                       └───────────────────────┘
                                                │
                                       ┌────────▼──────────────┐
                                       │  Render BG Worker 2  │
                                       │  Celery Beat          │
                                       │  Every 60s:           │
                                       │  → evaluate_alerts    │
                                       │  Every 1hr:           │
                                       │  → cleanup_api_keys   │
                                       └───────────────────────┘
```

---

## Event Ingestion Flow

```
External App / Frontend
        │
        │  POST /api/v1/ingestion/events/
        │  Header: X-API-Key: ap_xxxxx
        │  Header: X-Organization-ID: uuid
        ▼
APIKeyAuthentication validates key hash (SHA-256)
        ↓
OrganizationMiddleware resolves org from header
        ↓
IsAnalyst permission check
        ↓
IngestionService.ingest_single_event()
        ↓
Event saved to PostgreSQL (time-series indexes)
        ↓
notify_dashboard_update.delay() → Redis queue
        ↓
Celery Worker → Django Channels → WebSocket push
        ↓
Frontend receives → Dashboard re-renders
```

---

## Alert Evaluation Flow

```
Celery Beat (every 60 seconds)
        ↓ pushes task to Redis
Celery Worker picks up evaluate_all_alerts
        ↓
Query all active AlertRule objects
        ↓
For each rule:
  Query events in time window
  Calculate metric (count/avg/sum)
  Compare against threshold (gt/lt/eq)
        ↓
Not triggered → continue
Triggered →
  Create AlertHistory record
  Update rule status → "triggered"
  send_alert_notifications.delay()
        ↓
  ├── email → Resend API
  ├── webhook → HTTP POST
  └── in_app → Redis Channels → WebSocket
```

---

## Authentication Flow

```
Email/Password:
  POST /auth/login/
        ↓
  authenticate(email, password)
        ↓
  Generate JWT (access=15min, refresh=7days)
        ↓
  Set HTTP-only cookies (SameSite=Lax, Secure=True)
        ↓
  Frontend: GET /organizations/ → org_id
  Frontend: GET /organizations/members/ → role
  Frontend: localStorage(org_id, role)

Google OAuth:
  /auth/login/google-oauth2/
        ↓
  Google consent screen
        ↓
  social_django pipeline:
    create/find user
    save_google_profile()
    generate JWT
    set cookies
        ↓
  redirect → /auth-callback?access=...&refresh=...
        ↓
  Frontend initSession() → /dashboard

API Key Auth:
  Header: X-API-Key: ap_xxxxx
        ↓
  SHA-256 hash → lookup by prefix + hash
        ↓
  request.organization = key.organization
  request.user_role = "analyst"
```

---

## RBAC System

```
Role Hierarchy:
  Owner → Admin → Analyst → Viewer

Permission Classes (DRF):
  IsViewer  → all authenticated org members
  IsAnalyst → analyst, admin, owner
  IsAdmin   → admin, owner only
  IsOwner   → owner only

Resolution:
  1. JWT cookie → authenticate user
  2. X-Organization-ID header → find membership
  3. membership.role → check against required role
  4. 403 if insufficient

Frontend mirrors backend:
  useRole() hook reads localStorage role
  canIngest()        → analyst+
  canManageTeam()    → admin+
  canManageApiKeys() → admin+
  UI elements shown/hidden based on role
```

---

## Database Schema

```
users
  id (UUID PK), email (unique), full_name
  is_google_auth, last_login_ip

organizations
  id (UUID PK), name, slug (unique)

organization_members
  organization_id → FK
  user_id → FK
  role (owner/admin/analyst/viewer)
  is_active

events  ← time-series optimized
  id (UUID PK)
  organization_id (indexed)
  event_type, event_name (indexed)
  source (api/csv/webhook)
  properties (JSONB)
  user_id (indexed)
  timestamp (indexed)
  Composite indexes:
    (organization, timestamp)
    (organization, event_name, timestamp)

alert_rules
  organization_id, event_name
  metric (count/avg/sum)
  condition (gt/lt/eq), threshold
  window_minutes
  status (active/triggered/muted/resolved)
  notification_channels (JSONB array)

api_keys
  key_prefix (8 chars, O(1) lookup)
  key_hash (SHA-256)
  expires_at
```

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Frontend | Next.js 14 App Router | SSR + file-based routing |
| UI | Tailwind CSS + Recharts | Fast styling + charts |
| State | TanStack Query | Server state + 5s auto-refetch |
| Backend | Django 4.2 + DRF | Batteries included |
| Auth | JWT HTTP-only cookies | XSS-safe token storage |
| Social Auth | social_django | Google OAuth2 pipeline |
| Task Queue | Celery + Redis | Async + multiprocessing |
| Scheduler | Celery Beat | Periodic alert evaluation |
| WebSockets | Django Channels | Live event stream |
| Database | PostgreSQL (Neon) | Time-series indexes |
| Cache/Broker | Redis (Upstash) | Task queue + cache + WS |
| Deployment | Render + Vercel | Free tier |
| CI/CD | GitHub Actions | Auto test + deploy on push |

---

## Key Technical Decisions

**JWT in HTTP-only cookies vs localStorage**
HTTP-only cookies prevent XSS attacks. JavaScript cannot access them. localStorage is readable by any script on the page.

**OrganizationMiddleware design**
Django middleware runs before DRF authentication. At middleware time request.user is AnonymousUser. So middleware only stores requested_org_id from the header. The permission class resolve_organization() runs after DRF authenticates.

**Celery multiprocessing vs threading**
Python GIL prevents true parallel execution in threads. Celery spawns separate OS processes each with its own Python interpreter and GIL. 4 workers = 4 cores working simultaneously. Perfect for CPU-bound CSV processing.

**SHA-256 for API key hashing**
bcrypt is slow by design — good for passwords, wrong for API keys. API keys are already long random strings (256 bits of entropy). SHA-256 is fast and collision-resistant.

**Composite indexes on events table**
Every dashboard query filters by (organization_id, timestamp) or (organization_id, event_name, timestamp). Without composite indexes PostgreSQL does full table scans. With them queries use index-only scans.

**Sync fallback for CSV**
If Celery unavailable, CSV upload falls back to synchronous processing. Graceful degradation — feature works regardless of Celery availability.

---

## API Reference

### Auth
```
POST   /api/v1/auth/register/           Register + create org
POST   /api/v1/auth/login/              Login → JWT cookies
POST   /api/v1/auth/logout/             Logout → clear cookies
POST   /api/v1/auth/token/refresh/      Refresh access token
GET    /api/v1/auth/profile/            Current user
GET    /api/v1/auth/health/             Health check
GET    /auth/login/google-oauth2/       Start Google OAuth
```

### Events
```
POST   /api/v1/ingestion/events/            Single event
POST   /api/v1/ingestion/events/batch/      Batch (max 100)
GET    /api/v1/ingestion/events/stream/     Last 100 events
POST   /api/v1/ingestion/csv/              CSV upload (async)
GET    /api/v1/ingestion/tasks/<id>/        Task status
```

### API Keys (Admin+)
```
GET    /api/v1/ingestion/api-keys/              List keys
POST   /api/v1/ingestion/api-keys/              Generate key
DELETE /api/v1/ingestion/api-keys/<id>/revoke/  Revoke key
```

### Dashboards
```
GET    /api/v1/dashboards/              List
POST   /api/v1/dashboards/              Create
GET    /api/v1/dashboards/<id>/         Detail + widgets
PATCH  /api/v1/dashboards/<id>/         Update
DELETE /api/v1/dashboards/<id>/         Delete
```

### Alerts
```
GET    /api/v1/alerts/rules/                List rules
POST   /api/v1/alerts/rules/                Create rule
POST   /api/v1/alerts/rules/<id>/mute/      Mute
GET    /api/v1/alerts/history/              History
```

### Organizations
```
GET    /api/v1/organizations/                               Org details
GET    /api/v1/organizations/members/                       Members
POST   /api/v1/organizations/members/invite/                Invite
POST   /api/v1/organizations/members/invite/<token>/accept/ Accept
PATCH  /api/v1/organizations/members/<user_id>/role/        Update role
```

---

## RBAC Permissions

| Feature | Viewer | Analyst | Admin | Owner |
|---|---|---|---|---|
| View dashboards/events/alerts | ✅ | ✅ | ✅ | ✅ |
| Ingest events | ❌ | ✅ | ✅ | ✅ |
| Create dashboards | ❌ | ✅ | ✅ | ✅ |
| Create alert rules | ❌ | ✅ | ✅ | ✅ |
| Manage API keys | ❌ | ❌ | ✅ | ✅ |
| Invite members | ❌ | ❌ | ✅ | ✅ |
| Assign owner role | ❌ | ❌ | ❌ | ✅ |

---

## Local Setup

### Prerequisites
- Docker + Docker Compose
- Node.js 18+
- Neon account (free PostgreSQL)

### 1. Clone
```bash
git clone https://github.com/hemanthdorepalli/analytics-platform
cd analytics-platform
```

### 2. Environment
```bash
cp .env.example .env
```


### 3. Start backend
```bash
docker-compose up --build
```

Services started:
- `web` — Gunicorn on :8000
- `websocket` — Daphne on :8001
- `celery_worker` — 4 concurrent workers
- `celery_beat` — scheduler
- `redis` — local broker

### 4. Start frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Deployment Architecture

```
GitHub (main branch)
        ↓ push triggers
GitHub Actions CI/CD
  test-backend  → Django checks + pytest
  test-frontend → TypeScript + Next build
        ↓ tests pass
  deploy-backend  → Render deploy hook
  deploy-frontend → Vercel CLI
        │                    │
        ▼                    ▼
┌──────────────┐    ┌─────────────────┐
│    Render    │    │     Vercel      │
│ Web Service  │    │ Next.js 14      │
│ (Gunicorn)   │    │ Edge Network    │
│ BG Worker 1  │    └─────────────────┘
│ (Celery)     │
│ BG Worker 2  │
│ (Beat)       │
└──────┬───────┘
       ├──► Neon PostgreSQL
       └──► Upstash Redis
```

---

## Project Structure

```
analytics_platform/
├── backend/
│   ├── app/
│   │   ├── authentication/   # JWT, Google OAuth, API key auth
│   │   ├── organizations/    # Multi-tenancy, RBAC, invites
│   │   ├── ingestion/        # Events, API keys, CSV upload
│   │   ├── dashboards/       # Dashboards, widgets, queries
│   │   ├── alerts/           # Alert rules, evaluation, history
│   │   └── websockets/       # Django Channels consumers
│   ├── core/
│   │   ├── middleware.py     # Request logging, org resolution
│   │   ├── permissions.py    # RBAC permission classes
│   │   └── exceptions.py     # Centralized error handling
│   └── config/
│       ├── settings/         # base, development, production
│       ├── celery.py         # Celery + Beat schedule
│       └── urls.py           # URL routing
└── frontend/
    ├── app/                  # Next.js 14 App Router pages
    ├── components/           # UI, charts, layout
    ├── lib/                  # API client, auth, queries, types
    └── hooks/                # useRole RBAC hook
```

---

## Author

**Hemanth Dorepalli**
Full Stack Developer
hemanthd09166@gmail.com
GitHub: https://github.com/hemanthdorepalli