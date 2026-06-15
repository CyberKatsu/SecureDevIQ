# Security Policy

## Overview

SecureDevIQ is a security training platform built with defense-in-depth principles. This document outlines the security architecture, best practices, and how to report vulnerabilities responsibly.

## Architecture & Security Design

### 1. Secret Management

- **API keys** (Anthropic, database credentials) are **environment variables only**
- **Never commit secrets** to version control — `.gitignore` excludes `.env` files
- **Use `.env.example`** as a template; never add real secrets to it
- Generate a strong `SECRET_KEY` for JWT signing:
  ```bash
  openssl rand -hex 32
  ```

### 2. Authentication & JWT

- **JWT tokens** use **HS256** algorithm with a strong secret key
- **Token expiry**: 24 hours (configured in `backend/app/config.py`)
- **Password hashing**: bcrypt with auto-generated salt (4.2.1 or later)
- **Stateless**: No server-side session storage needed

### 3. Database Security

- **Parameterized queries** via SQLAlchemy ORM — prevents SQL injection
- **Async connections** using asyncpg — thread-safe, non-blocking I/O
- **Connection pooling**: `pool_pre_ping=True` validates stale connections
- **No raw SQL**: All queries built via ORM; no string interpolation

### 4. API Security

- **CORS**: Restricted to frontend origins only (configurable via `CORS_ORIGINS`)
- **Authentication guards**: All sensitive routes require `get_current_user` dependency
- **Rate limiting**: Not implemented yet (recommended for production)
- **HTTPS**: Enforced in production (use reverse proxy like nginx with TLS)

### 5. Data Isolation

- **Ground truth never leaks**: Reference explanations stored in DB, never returned to frontend
- **User data isolation**: Users can only see their own submissions
- **Challenge caching**: Cached in DB to prevent redundant AI API calls and ensure consistency

### 6. OWASP Top 10 Coverage

| Category | Status | Notes |
|----------|--------|-------|
| A1: Broken Access Control | ✅ Protected | JWT guards + database-level user isolation |
| A2: Cryptographic Failure | ✅ Protected | HS256 JWT + bcrypt passwords + TLS (in prod) |
| A3: Injection | ✅ Protected | Parameterized ORM queries; no raw SQL |
| A4: Insecure Design | ✅ Designed | Ground truth isolation; no implicit trust |
| A5: Security Misconfiguration | ⚠️ Dev Only | Requires production hardening (see below) |
| A6: Vulnerable Components | ✅ Pinned | All dependencies pinned to specific versions |
| A7: Auth Failure | ✅ Mitigated | JWT + bcrypt; no weak defaults |
| A8: Software/Data Integrity | ✅ Verified | CI/CD with pytest + ruff lint checks |
| A9: Logging/Monitoring | ⚠️ Minimal | Logs go to stdout; consider ELK/Datadog in prod |
| A10: SSRF | ✅ Protected | AI API calls server-side only; no user-controlled URLs |

## Production Security Checklist

Before deploying to production:

### Environment & Secrets
- [ ] Generate a strong `SECRET_KEY`: `openssl rand -hex 32`
- [ ] Store secrets in a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- [ ] Never commit `.env` files
- [ ] Rotate `SECRET_KEY` on a schedule

### Database
- [ ] Use a managed database (AWS RDS, Heroku Postgres, etc.) with **automatic backups**
- [ ] Enable **encrypted at rest** and **encrypted in transit** (TLS)
- [ ] Use strong, unique database credentials
- [ ] Enable **VPC-only** access (no public internet exposure)
- [ ] Regular **backups** and **disaster recovery** testing

### API Server
- [ ] Deploy behind a **reverse proxy** (nginx, AWS ALB, Cloudflare)
- [ ] Enable **TLS 1.3+** with strong ciphers (A+ on SSL Labs)
- [ ] Set **security headers**: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Strict-Transport-Security`, CSP
- [ ] Enable **rate limiting** per IP/user
- [ ] Use **environment-specific configs** (dev vs. staging vs. production)
- [ ] Monitor logs and set up **alerting** for suspicious activity

### Frontend
- [ ] Enable **HTTPS only** (force upgrade)
- [ ] Set `Secure` and `HttpOnly` flags on auth cookies
- [ ] Implement **CSP headers** to prevent XSS
- [ ] Remove **debug tools** and source maps in production builds

### Monitoring & Incident Response
- [ ] Enable **CloudTrail** / **WAF** logs
- [ ] Monitor **error rates** and **latency**
- [ ] Set up **alerts** for unusual activity
- [ ] Document **incident response playbook**
- [ ] Perform **regular security audits** (quarterly or per penetration test)

### CI/CD
- [ ] Run **security linting** (bandit, semgrep) in CI/CD
- [ ] Scan **dependencies** for known vulnerabilities (dependabot, Snyk)
- [ ] Use **signed commits** and **branch protection** on `main`
- [ ] Require **code review** before merge

## Dependency Security

All dependencies are pinned to specific versions in `requirements.txt`. Updates are managed manually to ensure compatibility.

To check for vulnerable dependencies:
```bash
pip install safety
safety check
```

Or use GitHub's Dependabot for automated alerts.

## Reporting Security Issues

**Do NOT open a public issue for security vulnerabilities.**

Instead, please email your findings to the maintainer privately. Include:
- **Description**: What is the vulnerability?
- **Impact**: Who is affected? What is the risk?
- **Reproduction**: Steps to reproduce (if applicable)
- **Fix**: Suggested remediation (if you have one)

We will:
1. Acknowledge receipt within 48 hours
2. Investigate and assess severity
3. Develop a fix and test it
4. Coordinate a responsible disclosure date
5. Credit you (if desired) in the fix commit/release notes

## Security Updates

- **Patch updates** (e.g., 1.0.1) are released ASAP
- **Minor updates** (e.g., 1.1.0) follow a release schedule
- **Major updates** (e.g., 2.0.0) are planned for far-future releases

Subscribers to the repository will receive notifications of new releases.

## Further Reading

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [SQLAlchemy Best Practices](https://docs.sqlalchemy.org/en/20/)
- [Anthropic API Security](https://docs.anthropic.com/)

---

**Last Updated**: 2026-04-29
