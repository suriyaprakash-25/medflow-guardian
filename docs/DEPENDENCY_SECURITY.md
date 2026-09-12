# Dependency Security

**Date:** 2026-09-11

## 1. Python Dependencies (Backend)
The backend dependencies are defined in `requirements.txt`.
- **Status**: Pinned versions are utilized for major dependencies (e.g., `fastapi>=0.111.0`, `slowapi==0.1.10`, `cryptography>=42.0.0`).
- **Audit Requirement**: Before production release, run `pip-audit` or `safety check` in the CI pipeline to catch CVEs.
- **Accepted Risks**: None currently documented.

## 2. Node Dependencies (Frontends)
The frontend applications (`patient-app`, `doctor-portal`, `admin-portal`) use `npm`.
- **Status**: `package.json` and `package-lock.json` are maintained.
- **Audit Requirement**: Run `npm audit` during the GitHub Actions build process. Fail the build on `CRITICAL` findings.
- **Accepted Risks**: Development dependencies (e.g., Vite plugins) with vulnerabilities that do not affect the compiled static bundle may be marked as accepted risk.

## 3. Container Base Images
If deployed via Docker in the future (currently using Render native Python environments):
- **Rule**: Use official Python slim images (e.g., `python:3.11-slim`).
- **Rule**: Do not run as `root`. Create a dedicated `medflow` user.

## 4. Remediation SLA
- **CRITICAL**: Remediate within 48 hours.
- **HIGH**: Remediate within 7 days.
- **MEDIUM/LOW**: Review during regular sprint planning.
