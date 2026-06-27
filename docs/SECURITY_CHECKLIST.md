# Security Checklist

Comprehensive security assessment and checklist for the URL Shortener MVP.

---

## 1. Authentication & Authorization

### Current Implementation
- ✓ Simple API key (`ADMIN_API_KEY`) for admin endpoints
- ✓ API key passed via query parameter (low-risk for internal use)

### Issues Identified
- ⚠️ **Single global API key** - Not suitable for multi-tenant or user-facing APIs
- ⚠️ **No user authentication** - No way to identify or audit individual users
- ⚠️ **No role-based access control (RBAC)** - All admins have same permissions

### Recommendations

**Immediate (MVP):**
- [x] Document API key as dev-only; warn against production use
- [ ] Rotate API key regularly
- [ ] Store API key in environment variable (already done)
- [ ] Never commit API key to version control

**Short-term (Before public launch):**
- [ ] Implement OAuth2 with Bearer token in Authorization header
- [ ] Support API key + application pairs for programmatic access
- [ ] Add user authentication with JWT tokens
- [ ] Implement role-based access control (viewer, editor, admin)

**Production Requirements:**
```python
# Example: OAuth2 with JWT
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    token = credentials.credentials
    # Verify JWT signature and expiration
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    return payload
```

---

## 2. Input Validation & Injection Prevention

### Current Implementation
- ✓ Pydantic BaseModel validates HTTP request bodies
- ✓ SQLAlchemy ORM (via SQLModel) parameterizes all queries
- ✓ URL validation using AnyUrl type
- ✓ Custom alias validation with regex

### Assessed Risks

#### SQL Injection
- **Risk Level:** LOW (SQLAlchemy ORM prevents SQL injection)
- **Mitigation:** All queries use parameterized statements; no raw SQL
- **Test:** Verify with malicious payload: `alias'; DROP TABLE url;--`

#### XSS (Cross-Site Scripting)
- **Risk Level:** LOW (API-only, no HTML rendering)
- **Notes:** Frontend handles HTML escaping; verify with test

#### URL Validation
- **Risk Level:** MEDIUM
- **Current:** AnyUrl validates format; accepts http/https
- **Gap:** Doesn't prevent redirects to phishing sites
- **Mitigation:** Could add URL reputation check (future)

#### Alias Injection
- **Risk Level:** LOW
- **Current:** Regex validation: `^[a-zA-Z0-9_-]{3,20}$`
- **Safe:** No special characters allowed

### Recommendations

- [x] Add input length limits (custom_alias: 20 char max)
- [ ] Add URL reputation scoring (Google Safe Browsing API)
- [ ] Rate limit unique shortening attempts per IP
- [ ] Log suspicious patterns (many failures, unusual URLs)

---

## 3. Data Protection

### Current Implementation
- ✓ API key required for analytics endpoints
- ✓ Sensitive data (IPs, user-agents) optional
- ✓ No authentication required for redirect (expected)

### Assessed Risks

#### Sensitive Data Exposure
- **Risk Level:** MEDIUM
- **Data Exposed:** IP addresses, user-agents in analytics
- **Who Can Access:** Admins with API key
- **Mitigation:** 
  - [ ] Document data retention policy
  - [ ] Implement data anonymization (hash IPs)
  - [ ] Add encryption at rest (database)

#### Data Retention
- **Risk Level:** MEDIUM  
- **Issue:** ClickEvent table grows unbounded
- **Mitigation:**
  - [ ] Implement data archival (move old events to cold storage)
  - [ ] Auto-delete events older than 2 years
  - [ ] Add retention policy to documentation

#### In Transit
- **Risk Level:** MEDIUM
- **Current:** No HTTPS enforcement in code
- **Mitigation:**
  - [ ] Use HTTPS in production (nginx/Caddy config)
  - [ ] Add HSTS header
  - [ ] Add secure cookie flags

### Recommendations

```python
# Add to main.py for HTTPS enforcement
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com"])

# Add security headers
from fastapi import Response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

---

## 4. API Security

### Current Implementation
- ✓ API key validation on admin endpoints
- ✓ Basic CORS configuration
- ✓ OpenAPI documentation enabled

### Assessed Risks

#### Rate Limiting
- **Risk Level:** HIGH
- **Issue:** No rate limiting; vulnerable to DDoS
- **Mitigation:** Rate limiting stubs in place; needs implementation

#### CORS Bypass
- **Risk Level:** MEDIUM
- **Current:** `allow_origins=["*"]` (allows all)
- **Mitigation:**
  - [ ] Restrict to specific domains in production
  - [ ] Document CORS configuration

#### Information Disclosure
- **Risk Level:** LOW
- **Current:** Swagger docs at `/api/docs` (public)
- **Mitigation:**
  - [ ] Disable docs in production unless behind auth
  - [ ] Or restrict docs to internal network

### Recommendations

```python
# Restrict CORS to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Hide sensitive docs in production
docs_url = "/api/docs" if DEBUG else None
app = FastAPI(..., docs_url=docs_url)
```

---

## 5. Cryptography & Secrets

### Current Implementation
- ✓ Secrets via environment variables
- ✓ No hardcoded credentials in code

### Assessed Risks

#### API Key Storage
- **Risk Level:** HIGH if compromised
- **Current:** Stored in .env file (not version controlled)
- **Mitigation:**
  - [x] Never commit .env to git
  - [ ] Use secret manager (AWS Secrets Manager, Vault)
  - [ ] Rotate keys regularly
  - [ ] Audit key usage

#### Database Connection String
- **Risk Level:** HIGH if exposed
- **Current:** DATABASE_URL in environment
- **Mitigation:**
  - [x] Environment variable (already done)
  - [ ] Use connection pooling in production
  - [ ] Monitor failed connection attempts

### Recommendations

```yaml
# .gitignore (ensure .env is excluded)
.env
.env.local
data/*.db
secrets/
```

Secrets management in production:
```python
# Use AWS Secrets Manager
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Usage
api_key = get_secret('url-shortener/admin-api-key')
```

---

## 6. Auditing & Logging

### Current Implementation
- ⚠️ Minimal logging

### Assessed Risks

#### Missing Audit Trail
- **Risk Level:** MEDIUM
- **Issue:** No logging of who did what
- **Mitigation:**
  - [ ] Log all admin API calls with timestamp and API key
  - [ ] Log failed authentication attempts
  - [ ] Log data exports

#### Security Events Not Tracked
- **Risk Level:** MEDIUM
- **Mitigation:**
  - [ ] Log rate limit breaches
  - [ ] Log suspicious patterns (e.g., URL phishing attempts)
  - [ ] Send alerts for critical events

### Recommendations

```python
import logging

logger = logging.getLogger(__name__)

@app.get("/api/v1/info/{alias}")
def info(alias: str, api_key: Optional[str] = None):
    if api_key != ADMIN_API_KEY:
        logger.warning(f"Unauthorized info request for {alias}: {api_key}")
        raise HTTPException(status_code=401, detail="unauthorized")
    
    logger.info(f"Admin accessed info for {alias}")
    # ... rest of function
```

---

## 7. Dependencies & Vulnerabilities

### Current Implementation
- ✓ All dependencies pinned in requirements.txt
- ✓ Using well-maintained libraries (FastAPI, SQLModel, Pydantic)

### Assessed Risks

#### Dependency Vulnerabilities
- **Risk Level:** MEDIUM
- **Mitigation:**
  - [ ] Run `pip-audit` or `safety check` regularly
  - [ ] Update dependencies monthly
  - [ ] Monitor GitHub Security Advisories

#### Supply Chain Attacks
- **Risk Level:** LOW (but growing)
- **Mitigation:**
  - [ ] Use hash verification for critical dependencies
  - [ ] Review dependency source code for high-risk packages
  - [ ] Use private PyPI mirror for enterprise

### Recommendations

```bash
# Check for known vulnerabilities
pip install pip-audit
pip-audit

# Or use safety
pip install safety
safety check

# In CI/CD
.github/workflows/security.yml
```

---

## 8. Infrastructure & Deployment

### Current Implementation
- Docker Compose for dev
- SQLite for dev database

### Assessed Risks

#### Development vs Production
- **Risk Level:** HIGH if dev config used in prod
- **Mitigation:**
  - [x] Document production requirements
  - [ ] Use separate .env files per environment
  - [ ] Automate environment validation on startup

#### Database Security
- **Risk Level:** HIGH
- **Current:** SQLite (file-based; no network isolation)
- **Production:** Use PostgreSQL with:
  - [ ] Strong password (25+ character random)
  - [ ] Network isolation (VPC/security groups)
  - [ ] Encrypted connections (SSL/TLS)
  - [ ] Regular backups (encrypted, off-site)
  - [ ] Read replicas for availability

### Recommendations

Production deployment checklist:
- [ ] Use HTTPS everywhere
- [ ] Run behind reverse proxy (nginx/Caddy)
- [ ] Enable WAF (Web Application Firewall)
- [ ] Use CDN for static files
- [ ] Implement DDoS protection
- [ ] Set up monitoring and alerting
- [ ] Regular security scanning

---

## 9. Compliance & Privacy

### Current Implementation
- ⚠️ No privacy policy

### Assessed Risks

#### GDPR/CCPA Compliance
- **Risk Level:** HIGH if in-scope
- **Issue:** Collecting IPs without clear consent
- **Mitigation:**
  - [ ] Add privacy policy
  - [ ] Implement right-to-erasure (delete all data for a URL)
  - [ ] Add data export functionality (already implemented!)
  - [ ] Document data retention policy

#### User Consent
- **Risk Level:** MEDIUM
- **Issue:** No consent mechanism for data collection
- **Mitigation:**
  - [ ] Add cookie consent banner (if frontend)
  - [ ] Provide opt-out for analytics
  - [ ] Document data usage clearly

---

## 10. Testing & Validation

### Current Implementation
- ✓ Integration tests
- ✓ Unit tests
- ✓ Edge case tests

### Security Testing

Recommended additional tests:
- [ ] **Penetration testing:** Attempt SQL injection, XSS, CSRF
- [ ] **Fuzzing:** Test with random/malformed inputs
- [ ] **Load testing:** Verify rate limiting effectiveness
- [ ] **Security scanning:** SAST (static analysis) and DAST (dynamic)

### Tools to Add

```yaml
# Pre-commit hooks
pre-commit install

# .pre-commit-config.yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.4
    hooks:
      - id: bandit
```

---

## Security Improvement Roadmap

### Phase 1: MVP → Beta (Immediate)
- [ ] Implement rate limiting
- [ ] Add HTTPS enforcement
- [ ] Document security model
- [ ] Rotate default API key
- [ ] Add audit logging
- [ ] Run security tests

### Phase 2: Beta → Production
- [ ] Implement OAuth2/JWT authentication
- [ ] Add IP reputation checks
- [ ] Encrypt sensitive data at rest
- [ ] Implement data retention policy
- [ ] Add GDPR compliance features
- [ ] Third-party security audit

### Phase 3: Production → Hardened
- [ ] WAF and DDoS protection
- [ ] Advanced threat detection
- [ ] SIEM integration
- [ ] Red team exercise
- [ ] Bug bounty program

---

## Security Contacts & Resources

### Internal
- Security Team: [contact]
- Incident Response: [contact]

### External Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
- [GDPR Compliance](https://gdpr-info.eu/)

