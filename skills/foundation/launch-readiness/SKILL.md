---
name: launch-readiness
description: |
  Pre-launch checklists, staged rollout procedures, rollback plans, and operational readiness
  verification. Covers the gap between "PR merged" and "in production."
  Use when preparing a release for production or planning a staged rollout.
  Triggers on: launch, deploy, go-live, production ready, rollback, runbook, staged rollout.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Launch Readiness

## Principle

A merged PR is not a launched product. Launch readiness means the system can be deployed, monitored, rolled back, and operated — not just that it passes tests.

## Pre-Launch Checklist

### Infrastructure
- [ ] Health endpoints verified (`/health`, `/ready`, `/live`)
- [ ] Monitoring configured (response time, error rate, resource usage)
- [ ] Alerting rules set (on-call notified for p95 > threshold, error rate > 1%)
- [ ] Log aggregation working (structured logs, searchable)
- [ ] Database migrations tested and reversible
- [ ] Secrets in secret manager (not env vars, not config files)
- [ ] TLS/SSL configured for all external endpoints
- [ ] CDN configured for static assets (if applicable)

### Application
- [ ] All environment variables documented
- [ ] Configuration differs between staging and production (not shared)
- [ ] Rate limiting enabled on public endpoints
- [ ] CORS configured with specific origins (not `*`)
- [ ] Error responses don't leak stack traces or internal details
- [ ] Graceful shutdown handles in-flight requests

### Operations
- [ ] Runbook documented (common failure scenarios + resolution)
- [ ] Rollback procedure tested (not just documented)
- [ ] Incident response plan identified (who to page, escalation path)
- [ ] On-call rotation established (if applicable)
- [ ] Capacity planning done (expected load, auto-scaling rules)

## Staged Rollout

### Phase 1: Canary (1-5% traffic)
```
Duration: 15-30 minutes
Monitor: Error rate, response time, resource usage
Rollback trigger: Error rate > 2x baseline OR p95 > 3x baseline
Proceed if: All metrics within 10% of baseline
```

### Phase 2: Gradual (25% → 50% → 100%)
```
Duration: 15 minutes per step
Monitor: Same as Phase 1 + business metrics (conversion, completion rate)
Rollback trigger: Any metric > 2x baseline
Proceed if: Stable for full duration at each step
```

### Phase 3: Full Rollout (100%)
```
Duration: Monitor for 1 hour
Action: Remove canary infrastructure
Document: Deployment notes in changelog
```

## Rollback Procedures

### Application Rollback
```bash
# Blue/Green: Switch traffic back to previous version
aws ecs update-service --service app --task-definition app:PREVIOUS_VERSION

# Lambda: Repoint alias to previous version
aws lambda update-alias --name live --function-version PREVIOUS_VERSION

# Kubernetes: Undo rollout
kubectl rollout undo deployment/app
```

### Database Rollback
```bash
# Reversible migration (preferred)
alembic downgrade -1

# Point-in-time recovery (last resort)
aws rds restore-db-instance-to-point-in-time \
  --target-db-instance-identifier app-db-restored \
  --restore-time 2026-04-11T12:00:00Z
```

### Configuration Rollback
```bash
# Feature flag: Disable the feature immediately
curl -X PATCH https://flags.example.com/api/flags/new-feature \
  -d '{"enabled": false}'
```

## Rollback Decision Matrix

| Signal | Severity | Action |
|---|---|---|
| Error rate > 5x baseline | Critical | Immediate rollback, page on-call |
| p95 latency > 3x baseline | High | Rollback within 5 minutes |
| Partial functionality broken | Medium | Disable via feature flag, investigate |
| Cosmetic issue only | Low | Fix forward in next deployment |

## Runbook Template

```markdown
## Runbook: [Service Name]

### Service Overview
- Purpose: [one sentence]
- Dependencies: [database, cache, external APIs]
- Health check: [URL]

### Common Issues

#### Issue: Database connection timeout
- Symptoms: 503 errors, health check failing
- Root cause: Connection pool exhausted or DB unreachable
- Resolution:
  1. Check DB status: `aws rds describe-db-instances`
  2. Check connection count: `SELECT count(*) FROM pg_stat_activity`
  3. If pool exhausted: restart application pods
  4. If DB unreachable: check security groups and VPC connectivity

#### Issue: High memory usage
- Symptoms: OOM kills, pod restarts
- Resolution:
  1. Check current memory: `kubectl top pods`
  2. If leak: restart affected pods, investigate in staging
  3. If insufficient: increase memory limits in deployment spec
```

## After merge or deploy

A merged PR is not a healthy production change. For the area that changed:

- Watch error rate, latency, logs, and the key user flow. Compare each to the pre-deploy baseline.
- On a clear user-facing regression: roll back first (see the decision matrix), investigate second, and tag the owning human.
- Leave a short incident note: what happened, impact, cause, fix, follow-ups.

Do not claim the deploy is healthy without that comparison. Do not run a production deploy from this skill.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "We'll add monitoring after launch" | You won't know it's broken until users tell you — hours later. Monitor from day one. |
| "Rollback is just redeploying the old version" | Rollback includes database state, cache state, and in-flight requests. Test the full procedure. |
| "Staged rollout is overkill for a small app" | Small apps serve real users. A 5-minute canary costs nothing and catches everything. |
| "We don't need a runbook — we know the system" | You won't remember at 3 AM during an incident. Write it down. |
