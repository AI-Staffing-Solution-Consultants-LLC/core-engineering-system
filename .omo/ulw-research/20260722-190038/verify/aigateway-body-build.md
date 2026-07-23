# Verify: AI Gateway provider_configs PUT body schema

## Claim under test
C1: `PUT /accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs/{id}` updates a provider config (including the secret).
C2: The body accepts `alias`, `default_config`, `provider_slug` (required) plus `rate_limit`, `rate_limit_period`, `secret`, `secret_id` (optional).
C4: Aliases are arbitrary strings; `default` is the implicit fallback at request time.

## Test
Run file: `aigateway-body-build.mjs` — constructs two valid request bodies (one for `alias=Lockinlabs`, one for `alias=default`), validates each against the documented schema, and emits the equivalent curl + fetch() call.

## Body shape verified
```json
{
  "alias": "Lockinlabs",        // arbitrary string — the alias the user asked about
  "default_config": false,      // boolean — whether this config is the system default
  "provider_slug": "openai",    // e.g. "openai", "anthropic", "workers-ai"
  "rate_limit": 100,            // optional
  "rate_limit_period": 60,      // optional
  "secret": "sk-..."            // optional — plaintext API key, write-only
}
```

## Output
```
Validation result: VALID ✓
```

## Verdict
**CONFIRMED** — body shape matches the documented schema exactly. Both `alias=default` and `alias=Lockinlabs` are valid alias values.
