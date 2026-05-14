# Analytics Platform

Real-Time Analytics & Reporting Platform built with Django REST Framework, Celery, Redis, WebSockets, and PostgreSQL.

## Architecture

```
Internet → Nginx → Daphne (ASGI)
                      ├── HTTP → Django REST Framework
                      └── WebSocket → Django Channels

Background:
Django → Redis (broker) → Celery Workers (processing)
                       → Celery Beat (scheduled tasks)

Storage:
PostgreSQL (primary data)
Redis (cache + channel layer + broker)
```

## Stack

- **Backend**: Django 4.2 + Django REST Framework
- **Auth**: JWT (15min access / 7day refresh) + Google OAuth2
- **Task Queue**: Celery + Redis (workers + beat scheduler)
- **WebSockets**: Django Channels + Daphne
- **Database**: PostgreSQL 15
- **Cache**: Redis
- **Deploy**: Docker + Docker Compose

## Quick Start

```bash
# 1. Clone and setup
git clone <repo>
cd analytics_platform

# 2. Copy env file and fill in credentials
cp backend/.env.example backend/.env

# 3. Start all services
docker-compose up --build

# 4. Run migrations (first time)
docker-compose exec backend python manage.py migrate

# 5. Create superuser
docker-compose exec backend python manage.py createsuperuser
```

## API Endpoints

### Auth
- `POST /api/v1/auth/register/` — Register
- `POST /api/v1/auth/login/` — Login (sets HTTP-only refresh cookie)
- `POST /api/v1/auth/logout/` — Logout (blacklists token)
- `POST /api/v1/auth/token/refresh/` — Refresh access token
- `GET  /api/v1/auth/me/` — Current user

### Organizations
- `POST /api/v1/organizations/` — Create org
- `GET  /api/v1/organizations/` — List my orgs
- `POST /api/v1/organizations/{id}/invite/` — Invite member

### Data Ingestion
- `POST /api/v1/ingestion/{org_id}/events/` — Single event
- `POST /api/v1/ingestion/{org_id}/events/batch/` — Batch events
- `POST /api/v1/ingestion/{org_id}/events/csv/` — CSV upload
- `GET  /api/v1/ingestion/{org_id}/analytics/` — Analytics metrics

### Dashboards
- `POST /api/v1/dashboards/{org_id}/dashboards/` — Create dashboard
- `GET  /api/v1/dashboards/{org_id}/dashboards/` — List dashboards
- `POST /api/v1/dashboards/{org_id}/dashboards/{id}/share/` — Make public

### Alerts
- `POST /api/v1/alerts/{org_id}/alerts/` — Create alert rule
- `POST /api/v1/alerts/{org_id}/alerts/{id}/mute/` — Mute alert

### WebSocket
```
ws://localhost:8000/ws/organizations/{org_id}/dashboard/?token=<access_token>
```

## Running Tests

```bash
docker-compose exec backend pytest tests/ -v
```

## Load Testing

```bash
docker-compose exec backend locust -f locustfile.py --host=http://localhost:8000
```

## Environment Variables

See `backend/.env.example` for all required variables.

## Security

- JWT with 15min access token + 7day HTTP-only refresh cookie
- Token rotation and blacklisting on logout
- Google OAuth2 integration
- Organization-level data isolation at DB query layer
- RBAC: Owner → Admin → Analyst → Viewer
- Rate limiting on ingestion endpoints
- IP logging on login