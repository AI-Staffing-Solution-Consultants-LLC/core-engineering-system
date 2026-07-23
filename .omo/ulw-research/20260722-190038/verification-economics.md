# Verification Economics

| claim | risk | error cost | verification cost | path | outcome | residual risk |
|---|---|---|---|---|---|---|
| C5/C6: webhook HMAC-SHA256 via crypto.subtle.verify | high | signature bypass → arbitrary webhook acceptance | low (one script, 2 sec) | ran Node.js script with 4 paths (legit, tampered, wrong-secret, replay) | CONFIRMED | None — pattern matches Web Crypto spec |
| C1/C2/C4: PUT body schema for provider_configs/{id} | high | wrong body → 400 from API or silently dropped rotation | low (one script, 2 sec) | ran JSON schema validator against documented fields | CONFIRMED | Mutually exclusive `secret` vs `secret_id` not in spec — derived from convention + Alchemy example |
