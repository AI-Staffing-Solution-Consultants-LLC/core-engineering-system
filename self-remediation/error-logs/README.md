# Self-Remediation Error Logs

This directory contains build and deployment failure logs exported by the Cloud Build pipeline.

## Purpose

When a Cloud Build step fails (dry-run build, unit test, deployment, or health check), the pipeline writes a markdown file here describing:

- Build ID
- Failed step / service
- Timestamp
- Error message
- Rollback action taken (if any)

These logs are uploaded to `gs://aissc-core-engine-self-dep-build-logs/errors/` as Cloud Build artifacts, making them available for autonomous analysis by self-remediation agents.

## File naming

`<service>-<unix-timestamp>.md`

## Integration

The self-remediation engine can poll the GCS bucket or read committed files in this directory to identify the exact point of failure and author fixes on the `dev` branch.
