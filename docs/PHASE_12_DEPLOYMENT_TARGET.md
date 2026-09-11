# Phase 12 Deployment Target Decision

**Date:** 2026-09-11
**Objective:** Establish the actual production deployment architecture.

## Decision: Render (PaaS)
The MedFlow Guardian architecture relies on a stateless FastAPI backend and three Vite-built frontends, backed by Supabase PostgreSQL and Supabase Storage. The simplest, most defensible production architecture compatible with this stack is **Render**, configured via Infrastructure-as-Code (`render.yaml`).

### Why Render?
- **Zero-Ops Native Environments:** Supports Python web services and static sites natively.
- **TLS Termination:** Handled automatically by Render's edge proxy.
- **DDoS/Edge Protection:** Backed by Cloudflare (Render's default edge), providing basic WAF, DDoS protection, and rate limiting against volumetric attacks.
- **Secret Management:** Native environment groups.
- **Observability:** Centralized logging natively.

*(Note: AWS ECS/Fargate or Google Cloud Run are also valid, but require significantly more Terraform/IAM overhead. Render provides enterprise-grade boundaries without K8s/IAM complexity.)*

## Deployment Architecture

### 1. Edge & WAF (IMPLEMENTED VIA CLOUDFLARE/RENDER EDGE)
- All traffic passes through Render's Cloudflare-backed edge proxy.
- TLS is terminated here.
- Unsafe requests (e.g., volumetric DDoS, known bad IPs) are dropped before reaching the application.

### 2. Frontends (REQUIRED FOR DEPLOYMENT)
- **patient-app**, **doctor-portal**, and **admin-portal** deployed as Render Static Sites.
- Configured with `VITE_API_BASE_URL` pointing to the production backend URL.
- No backend secrets bundled.

### 3. Backend (REQUIRED FOR DEPLOYMENT)
- Deployed as a Render Web Service (Python environment).
- Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Native health checks hitting `/health`.
- Connected to Supabase via pooled `DATABASE_URL`.

### 4. Database & Storage (IMPLEMENTED NOW)
- Supabase PostgreSQL and Supabase Storage are already configured.
- **Connection pooling:** Enabled via Supabase PgBouncer (using port 6543 pooler string).

### 5. Environments (REQUIRED FOR DEPLOYMENT)
- `medflow.yaml` will define a Staging environment and a Production environment to ensure complete separation of duties.
