# SOP-002: Incident Response Runbook

**Namespace:** openviking  
**Status:** Active  
**Last Updated:** 2026-07-21

## Severity Classifications

| Severity | Definition | Response SLA |
|----------|-----------|--------------|
| **P1** | Production down or data loss | Page on-call immediately. 15 min to acknowledge. |
| **P2** | Degraded but functional | Create ticket within 15 min. 1 hour to investigate. |
| **P3** | Non-critical anomaly | Ticket within 4 hours. Next business day fix. |
| **P4** | Cosmetic / internal tooling | Backlog. Fix in next sprint. |

## Incident Commander Role
- Declares severity level within 5 min of triage
- Opens a dedicated Slack channel (#incident-YYYY-MM-DD)
- Assigns: one responder to investigate, one to communicate
- Escalates to engineering manager if P1 exceeds 30 min without resolution

## Investigation Workflow

### Step 1: Establish Baseline
```bash
kubectl get pods     # Pod status across all namespaces
kubectl top pods     # Resource consumption snapshot
```

### Step 2: Check Recent Changes
```bash
kubectl events                    # Cluster-level events
gcloud run services list          # Deployed service versions
git log --oneline -20             # Recent code changes
```

### Step 3: Inspect Logs
```bash
kubectl logs --tail=200           # Recent log output
kubectl logs --previous           # Logs from crashed container
kubectl describe pod <name>       # Pod events and conditions
```

### Step 4: Diagnose Latency Issues
- Check `kubectl top nodes` for CPU/memory saturation
- Review Cloud Monitoring dashboards for request latency spikes
- Verify no noisy neighbor on shared nodes
- Check network egress: `gcloud compute firewall-rules list`

### Step 5: Diagnose Crash Loops
- Inspect exit codes: `kubectl get pods -o json | jq '.items[].status.containerStatuses[] | {name, restartCount, state}'`
- Check OOMKill events: `kubectl describe pod | grep -A5 OOMKilled`
- Verify resource limits vs actual usage

## Post-Mortem Template

After resolution (within 48 hours for P1/P2):

1. **Summary:** What happened, duration, impact
2. **Timeline:** Key events with timestamps
3. **Root Cause:** The "five whys" analysis
4. **Resolution:** What fixed it
5. **Prevention:** Action items to prevent recurrence
6. **Ledger Reference:** plan_id from Track A's reasoning chain

## Escalation Matrix
- **On-Call Engineer** → **Engineering Manager** (30 min, P1)
- **Engineering Manager** → **Director of Engineering** (1 hour, P1 unresolved)
- **Director** → **VP Engineering** (2 hours, customer-facing impact)

## Key Contacts
- GCP Support: via `aissc-core-engine-self-dep` project console
- Infisical on-call: secrets rotation channel
- Terraform state: local only; no remote backend configured
