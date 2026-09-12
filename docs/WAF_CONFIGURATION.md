# WAF Configuration Guide

**Date:** 2026-09-11
**Objective:** Define the Web Application Firewall (WAF) rules required for the MedFlow Guardian production edge. 

By default, Render utilizes Cloudflare for edge routing, which includes standard DDoS protection. However, if deployed on AWS or an Enterprise Cloudflare tier, the following specific WAF rules must be enforced.

## 1. Allowed Geographies
- **Rule**: Block all traffic originating outside of authorized operational regions (e.g., allow `US`, `CA` only if MedFlow operates exclusively in North America).
- **Justification**: Healthcare data sovereignty and reduction of generalized botnet noise.

## 2. Rate Limiting (Edge Level)
While the application utilizes `slowapi` for endpoint-specific limits, volumetric attacks must be caught at the edge.
- **Rule**: Limit general API requests (`/api/*`) to 300 requests per minute per IP.
- **Rule**: Limit static asset requests to 2000 requests per minute per IP.

## 3. Upload Abuse Prevention
- **Rule**: Block any HTTP `POST` to `/api/documents` where `Content-Length` > 10485760 (10MB).
- **Justification**: Protects the backend FastAPI process from memory exhaustion before the request even reaches Python.

## 4. IP Allowlisting for Admin
- **Rule**: The `/api/admin/*` endpoints must strictly enforce IP Allowlisting (e.g., Corporate VPN IP range).
- **Justification**: Admin portals represent the highest risk surface area.

## 5. TLS Configuration
- **Minimum TLS Version**: TLS 1.3 preferred; TLS 1.2 minimum.
- **HSTS**: `max-age=31536000; includeSubDomains; preload` (Enabled in FastAPI, but WAF should enforce redirect).
