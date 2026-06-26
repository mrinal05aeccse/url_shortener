# URL Shortener - Minimal Prototype

This repository contains a minimal FastAPI-based URL shortener prototype.

Components:
- FastAPI backend (backend/app)
- PostgreSQL (docker-compose)

Quickstart (requires Docker):

1. Start services:

   docker-compose up --build

2. Create a short URL (example):

   curl -X POST "http://localhost:8000/api/v1/shorten" -H "Content-Type: application/json" -d '{"target":"https://example.com"}'

3. Open the returned alias in your browser:

   http://localhost:8000/{alias}

Admin info endpoint:

   GET /api/v1/info/{alias}?api_key=changeme

Run tests (locally, without Docker):

   cd backend
   pip install -r requirements.txt
   pytest


Notes:
- This is a minimal scaffold to demonstrate core flows. It is intentionally simple and suitable for iterative improvements (analytics, LangGraph integration, React frontend, Redis rate-limiting, migrations).
