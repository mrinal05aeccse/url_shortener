# Final Engineering Summary

Plan & rationale
- Build a minimal, testable URL shortener with analytics.
- Prioritize correctness, traceability, and simplicity for evaluation.

Artifacts
- Backend (FastAPI + SQLModel), frontend (React/Vite), integration tests, CI workflow, docs.

Risks & trade-offs
- Using SQLite for dev is simple but not suitable under heavy concurrency; production should use PostgreSQL.
- ADMIN_API_KEY is a simple guard — replace with OAuth/JWT for production.
- ClickEvent table can grow large; consider time-windowed aggregation and retention.

Validation & safety guardrails
- Integration tests that cover create -> redirect -> analytics.
- CI runs pytest.
- Secure secrets via environment variables / secret manager; never commit secrets.

Assumptions & limitations
- Default storage is SQLite (developer convenience).
- No user accounts or per-user scopes in MVP.
- No rate limiting in this commit; add Redis-backed rate limits before public rollout.