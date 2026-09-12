# MedFlow Guardian Production Architecture

## Overview
MedFlow Guardian uses a decoupled architecture designed for high availability, security, and strict data-flow governance.

## Components

1. **Frontend (SPAs)**
   - **Patient App**, **Doctor Portal**, **Admin Portal**.
   - Hosted on a CDN (e.g., Vercel, Cloudflare Pages, or AWS CloudFront).
   - All builds strip `console.log` and debugger statements.

2. **Backend API (FastAPI)**
   - Hosted on a scalable PaaS or Container orchestration (e.g., AWS ECS, Render, or Google Cloud Run).
   - Placed behind a Reverse Proxy/WAF (Web Application Firewall).
   - Enforces strict CORS, CSP, HSTS, and X-Frame-Options headers.

3. **Database (Supabase PostgreSQL)**
   - Managed PostgreSQL instance.
   - Connection Pooling via PgBouncer.
   - TLS required for all connections.

4. **Storage (Supabase Storage)**
   - Private AWS S3-compatible buckets.
   - Files are stored with UUID names under `patient/{patient_id}/`.
   - Direct public access is disabled. All downloads proxy through the Backend API's Central Authorization Engine.

## Security Boundaries
- **Network Level**: The database only accepts connections from the Backend API IP range.
- **Application Level**: The Central Authorization Engine strictly gates all routes based on the active `ConsentState` and user roles.
- **Data Level**: Passwords are hashed using bcrypt. Access logs are immutable (append-only).
