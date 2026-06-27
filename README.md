# URL Shortener (MVP)

This repository contains a minimal URL shortener backend (FastAPI + SQLModel) and a small React/Vite frontend.

Quick setup (local)

1. Backend (recommended with Python virtualenv)
   cd backend
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt
   # Create DB + tables (the app calls init_db at startup automatically)
   uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

2. Shorten a URL (example)
   curl -X POST "http://localhost:8000/api/v1/shorten" -H "Content-Type: application/json" -d '{"target":"https://example.com"}'

3. Frontend (dev)
   cd frontend
   npm install
   npm run dev
   # The frontend expects the backend at /api/v1 when proxied in production. During dev, set the API base as needed.

Environment
- DATABASE_URL: SQLAlchemy URL (default: sqlite:///./data.db)
- ADMIN_API_KEY: API key for info/analytics endpoints (default in dev: changeme). Change before production.

Notes
- This is an MVP scaffold. For production:
  - Use PostgreSQL or other RDBMS and run Alembic migrations.
  - Use Redis or other durable storage for rate limiting.
  - Protect admin endpoints with stronger auth.
  - Add background workers for heavy work and batching.