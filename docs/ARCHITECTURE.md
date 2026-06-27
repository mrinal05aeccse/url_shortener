# Architecture Overview

Components:
- Backend: FastAPI + SQLModel (sqlite for dev; configurable DATABASE_URL for prod). Exposes:
  - POST /api/v1/shorten  -> create short URL
  - GET /{alias}          -> redirect + record click event
  - GET /api/v1/info/{alias} (admin) -> metadata
  - GET /api/v1/analytics/{alias} (admin) -> aggregated analytics

- Database: SQLModel (SQLAlchemy). For production use PostgreSQL with Alembic migrations.

- Analytics: ClickEvent table (per-click rows) + an aggregate clicks field on URL.

- Frontend: React + Vite minimal app to create and open short URLs.

- CI: GitHub Actions running tests.

Key decisions:
- SQLModel chosen for simple models + migration compatibility with Alembic.
- Clicks both aggregated (URL.clicks) and event-tracked (ClickEvent) to support both fast counters and detailed analytics.
- Admin endpoints protected by ADMIN_API_KEY (dev-only). Replace with proper auth for prod.

Execution approach:
- Developer-led, AI-assisted generation of code, tests, docs.
- Traceability maintained via branch feature/initial-scaffold and commit messages.

Control flow:
- Client -> POST /api/v1/shorten -> create URL -> return alias
- Visitor -> GET /{alias} -> lookup + record ClickEvent -> increment aggregate -> redirect
- Admin -> GET /api/v1/analytics/{alias}?api_key=... -> aggregate ClickEvents by day