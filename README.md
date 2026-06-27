# URL Shortener (MVP+)

A minimal but feature-rich URL shortener service with geographic analytics, data export, and comprehensive testing.

## Features

### Core (Original)
- **URL Shortening:** Create short aliases for long URLs with optional custom names
- **Auto-expiration:** Set time-to-live (TTL) for URLs to auto-expire
- **Click Tracking:** Record and aggregate click statistics
- **Redirect Tracking:** Capture IP, user-agent, and geographic data

### Enhancements (Phase 1)
- **Geographic Analytics:** View click distribution by country (ISO 2-letter codes)
- **Data Export:** Export analytics to CSV (summary, daily breakdown, raw events)
- **Input Validation:** URL format, custom alias format, TTL bounds validation
- **API Documentation:** Auto-generated OpenAPI/Swagger docs at `/api/docs`
- **CORS Support:** Cross-origin requests enabled (configurable in production)
- **Comprehensive Testing:** Unit tests, integration tests, edge case tests

---

## Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:5173
```

### 3. Test Everything

```bash
# Backend tests
cd backend
pytest -v

# Specific test files
pytest tests/test_integration.py -v  # Integration tests
pytest tests/test_unit.py -v        # Unit tests
pytest tests/test_edge_cases.py -v  # Edge cases
```

---

## API Reference

### Shorten URL

```bash
curl -X POST http://localhost:8000/api/v1/shorten \
  -H "Content-Type: application/json" \
  -d '{"target": "https://example.com", "ttl_days": 7}'
```

**Response:**
```json
{"alias": "abc123", "target": "https://example.com"}
```

### Redirect

```bash
# Automatically redirects and records click
curl -L http://localhost:8000/abc123
```

### Get URL Info (Admin)

```bash
curl "http://localhost:8000/api/v1/info/abc123?api_key=changeme"
```

**Response:**
```json
{
  "alias": "abc123",
  "target": "https://example.com",
  "clicks": 42,
  "created_at": "2024-01-01T12:00:00",
  "expires_at": "2024-01-08T12:00:00"
}
```

### Daily Analytics (Admin)

```bash
curl "http://localhost:8000/api/v1/analytics/abc123?days=7&api_key=changeme"
```

**Response:**
```json
{
  "alias": "abc123",
  "total_clicks": 42,
  "recent_days": 7,
  "daily_counts": {
    "2024-01-01": 5,
    "2024-01-02": 8,
    "2024-01-03": 29
  }
}
```

### Geographic Analytics (Admin) - NEW

```bash
curl "http://localhost:8000/api/v1/analytics/abc123/geo?api_key=changeme"
```

**Response:**
```json
{
  "alias": "abc123",
  "by_country": {
    "US": 25,
    "GB": 10,
    "DE": 5,
    "XX": 2
  },
  "total_clicks": 42
}
```

### Export Analytics (Admin) - NEW

```bash
# Export URL summary
curl "http://localhost:8000/api/v1/export/url/abc123?api_key=changeme" -o summary.csv

# Export daily breakdown
curl "http://localhost:8000/api/v1/export/analytics/abc123?api_key=changeme" -o analytics.csv

# Export raw events (with IP/UA)
curl "http://localhost:8000/api/v1/export/events/abc123?api_key=changeme" -o events.csv
```

### API Documentation

**Interactive API docs:** http://localhost:8000/api/docs
**ReDoc documentation:** http://localhost:8000/api/redoc

---

## Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./data.db        # SQLite (dev)
# DATABASE_URL=postgresql://user:pass@host/db  # PostgreSQL (prod)

# Security
ADMIN_API_KEY=changeme                  # Change in production!

# Logging
LOG_LEVEL=INFO

# Geolocation (Optional)
GEOIP_DB_PATH=./data/GeoLite2-City.mmdb

# Rate Limiting (Future)
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PROVIDER=redis               # or "memory"
REDIS_URL=redis://localhost:6379
```

---

## Architecture

### Backend Stack
- **Framework:** FastAPI (async Python web framework)
- **ORM:** SQLModel (SQLAlchemy + Pydantic)
- **Validation:** Pydantic (automatic request validation)
- **Database:** SQLite (dev), PostgreSQL (production)
- **Geolocation:** MaxMind GeoIP2 (optional, gracefully degraded)

### Frontend Stack
- **Framework:** React with TypeScript
- **Build Tool:** Vite (fast dev server)
- **Styling:** CSS (minimal)
- **API:** Fetch API with proxy configuration

### Data Model

**URL Table:**
- `id`: Unique identifier
- `alias`: Short alias (unique, indexed)
- `target`: Full URL
- `clicks`: Aggregate click counter (fast reads)
- `created_at`: Timestamp
- `expires_at`: Optional expiration
- `events`: Relationship to ClickEvent

**ClickEvent Table:**
- `id`: Unique identifier
- `url_id`: Foreign key to URL
- `timestamp`: When the click occurred
- `ip`: IP address (optional)
- `ua`: User-agent (optional)
- `country`: ISO country code (NEW)

---

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design and key decisions
- [AI_EXECUTION_LOG.md](docs/AI_EXECUTION_LOG.md) - How this project was built with AI assistance
- [SCENARIOS.md](docs/SCENARIOS.md) - Greenfield, brownfield, and ambiguous requirement scenarios
- [BROWNFIELD_EXECUTION.md](docs/BROWNFIELD_EXECUTION.md) - Geographic analytics enhancement
- [AMBIGUOUS_EXECUTION.md](docs/AMBIGUOUS_EXECUTION.md) - Data export feature implementation
- [SECURITY_CHECKLIST.md](docs/SECURITY_CHECKLIST.md) - Security assessment and recommendations
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production deployment guide
- [FINAL_SUMMARY.md](docs/FINAL_SUMMARY.md) - Overview of risks, trade-offs, validation
- [PROJECT_ASSESSMENT.md](docs/PROJECT_ASSESSMENT.md) - Complete assessment against assignment requirements

---

## Testing

### Test Coverage

```bash
# Run all tests
pytest backend/tests/ -v

# With coverage report
pytest backend/tests/ --cov=backend.app --cov-report=html
```

### Test Categories

1. **Integration Tests** (`test_integration.py`)
   - End-to-end workflows: shorten → redirect → analytics
   - Authorization and error handling

2. **Unit Tests** (`test_unit.py`)
   - Alias generation randomness
   - Geolocation fallback behavior
   - Model validation
   - Export CSV generation

3. **Edge Case Tests** (`test_edge_cases.py`)
   - Expired URL handling
   - Duplicate alias conflicts
   - Invalid input validation
   - Concurrent clicks
   - Date range filtering

---

## Known Limitations

### Current (MVP)
- Single global API key (not suitable for user-facing APIs)
- SQLite for dev only (single connection, poor concurrency)
- No rate limiting (vulnerable to abuse)
- No pagination (assumes <100MB datasets)
- Geolocation requires manual GeoIP DB setup

### By Design
- No user authentication (internal service)
- No URL content validation (could shorten phishing links)
- No custom redirect path prefixes (always `/{alias}`)
- No QR codes or custom branding

---

## Production Readiness

### Before Going Live

- [ ] Replace API key auth with OAuth2/JWT
- [ ] Switch to PostgreSQL database
- [ ] Implement rate limiting (Redis-backed)
- [ ] Enable HTTPS (Let's Encrypt certificate)
- [ ] Configure CORS for specific domains
- [ ] Set up monitoring and alerting
- [ ] Create GDPR-compliant privacy policy
- [ ] Run security audit and penetration testing
- [ ] Document runbook and incident procedures

See [SECURITY_CHECKLIST.md](docs/SECURITY_CHECKLIST.md) and [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed checklists.

---

## Future Enhancements

1. **Advanced Analytics**
   - Referrer tracking (which sites link to short URLs)
   - Device/OS breakdown
   - Time-series visualization

2. **User Management**
   - Multi-tenant support
   - Per-user rate limits
   - Team/organization features

3. **Link Management**
   - Bulk operations (create, delete, expire)
   - Link categorization and tagging
   - Custom URL prefixes per user

4. **Performance**
   - Caching layer (Redis) for hot links
   - CDN integration
   - Async geolocation lookups

5. **Integrations**
   - Webhooks (send event notifications)
   - Slack/email alerts for high-traffic URLs
   - Third-party analytics sync

---

## Development

### Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app and endpoints
│   │   ├── models.py            # SQLModel definitions
│   │   ├── database.py          # Database initialization
│   │   ├── utils.py             # Utility functions
│   │   ├── geo.py               # Geolocation utility (NEW)
│   │   ├── export.py            # CSV export utilities (NEW)
│   │   └── ratelimit.py         # Rate limiting stubs (NEW)
│   ├── tests/
│   │   ├── test_integration.py  # Integration tests
│   │   ├── test_unit.py         # Unit tests (NEW)
│   │   └── test_edge_cases.py   # Edge case tests (NEW)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── ShortenForm.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── index.html               # (NEW - was missing)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── AI_EXECUTION_LOG.md      # (NEW)
│   ├── BROWNFIELD_EXECUTION.md  # (NEW)
│   ├── AMBIGUOUS_EXECUTION.md   # (NEW)
│   ├── SECURITY_CHECKLIST.md    # (NEW)
│   ├── DEPLOYMENT.md            # (NEW)
│   ├── PROJECT_ASSESSMENT.md    # (NEW)
│   ├── SCENARIOS.md
│   └── FINAL_SUMMARY.md
├── docker-compose.yml
└── README.md                     # (This file - updated)
```

### Code Style

- Black for formatting: `black backend/`
- isort for import sorting: `isort backend/`
- Flake8 for linting: `flake8 backend/`
- Type hints on all functions
- Comprehensive docstrings

---

## Support & Debugging

### Check Service Status

```bash
# Backend
curl http://localhost:8000/api/docs

# Database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM url;"

# Frontend
http://localhost:5173
```

### Common Issues

**Q: "ModuleNotFoundError: No module named 'backend'"**
```bash
# Solution: Run from project root, not backend/
cd /path/to/project
python -m pytest backend/tests/
```

**Q: "Address already in use: ('0.0.0.0', 8000)"**
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9
# Or use different port
uvicorn app.main:app --port 8001
```

**Q: Geolocation returns "XX" for all IPs**
```bash
# Download GeoIP database
wget https://dev.maxmind.com/geoip/geoip2/geolite2/
# Or set GEOIP_DB_PATH environment variable
```

---

## Contributing

This project demonstrates AI-assisted engineering practices. See [AI_EXECUTION_LOG.md](docs/AI_EXECUTION_LOG.md) for how this project was built with LLM assistance while maintaining engineer ownership and quality standards.

---

## License

MIT License - See LICENSE file

---

## Changelog

### Phase 1 (Current)
- [x] Core URL shortening
- [x] Click tracking and analytics
- [x] Geographic analytics (NEW)
- [x] Data export to CSV (NEW)
- [x] Comprehensive testing (NEW)
- [x] Input validation (NEW)
- [x] API documentation (NEW)
- [x] Security assessment (NEW)
- [x] Deployment guide (NEW)

### Phase 2 (Planned)
- [ ] Rate limiting
- [ ] OAuth2 authentication
- [ ] PostgreSQL in production
- [ ] Monitoring/alerting
- [ ] Admin dashboard
