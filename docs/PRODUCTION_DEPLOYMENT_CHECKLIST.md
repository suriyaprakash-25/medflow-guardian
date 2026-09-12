# Production Deployment Checklist

**Date:** 2026-09-11

## INFRASTRUCTURE
- [ ] Domain configured
- [ ] TLS certificate active
- [ ] WAF rules applied (Cloudflare/Edge)
- [ ] Backend deployed (Render Web Service)
- [ ] Frontends deployed (Render Static Sites)
- [ ] Supabase PostgreSQL provisioned and pooled connection URL acquired
- [ ] Supabase Storage buckets provisioned (private)

## SECURITY
- [ ] `SECRET_KEY` generated and injected into environment
- [ ] `ENCRYPTION_KEY` generated and injected into environment
- [ ] `SUPABASE_SERVICE_ROLE_KEY` injected into environment
- [ ] MFA enabled for initial Admin accounts
- [ ] CORS domains restricted to production frontend URLs
- [ ] CSP and Security Headers verified
- [ ] Database network restrictions applied (if supported by plan)

## OBSERVABILITY
- [ ] Centralized logging ingest configured
- [ ] Alerting rules (Tier 1/2) configured in monitoring platform
- [ ] `/ready` health check passing from external prober

## RECOVERY
- [ ] Point-in-Time Recovery (PITR) confirmed active in Supabase
- [ ] Staging restore drill successfully completed
- [ ] Incident Response Runbook accessible to operations team

## TESTING
- [ ] CI unit and integration tests passed
- [ ] Golden workflow verified in production (Upload -> Consent -> Download)
- [ ] Penetration test remediations applied
