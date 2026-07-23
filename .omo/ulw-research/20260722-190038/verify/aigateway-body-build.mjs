// Verification: construct a valid PUT body for the AI Gateway provider_configs
// Update endpoint, validating the body against the documented schema.
//
// Source of schema: https://developers.cloudflare.com/api/resources/ai_gateway/subresources/provider_configs/
// Method: PUT /accounts/{account_id}/ai-gateway/gateways/{gateway_id}/provider_configs/{id}
// Auth: Authorization: Bearer $CLOUDFLARE_API_TOKEN
// Content-Type: application/json

// Build a body for the "Lockinlabs" alias on gateway "my-gateway" / provider "openai"
const body = {
  alias: 'Lockinlabs',
  default_config: false,             // do NOT mark as default; we want a non-default alias
  provider_slug: 'openai',
  rate_limit: 100,                   // optional
  rate_limit_period: 60,             // optional
  secret: 'sk-1234567890abcdef-rotated', // write-only plaintext; never returned in responses
};

// Strict schema check against the documented fields
const SCHEMA = {
  required: ['alias', 'default_config', 'provider_slug'],
  optional: ['rate_limit', 'rate_limit_period', 'secret', 'secret_id'],
};

function validate(body) {
  const errors = [];
  for (const f of SCHEMA.required) {
    if (!(f in body)) errors.push(`missing required field: ${f}`);
  }
  for (const k of Object.keys(body)) {
    if (!SCHEMA.required.includes(k) && !SCHEMA.optional.includes(k)) {
      errors.push(`unknown field: ${k}`);
    }
  }
  if (typeof body.alias !== 'string') errors.push('alias must be string');
  if (typeof body.default_config !== 'boolean') errors.push('default_config must be boolean');
  if (typeof body.provider_slug !== 'string') errors.push('provider_slug must be string');
  if ('rate_limit' in body && typeof body.rate_limit !== 'number') errors.push('rate_limit must be number');
  if ('rate_limit_period' in body && typeof body.rate_limit_period !== 'number') errors.push('rate_limit_period must be number');
  if ('secret' in body && typeof body.secret !== 'string') errors.push('secret must be string');
  if ('secret_id' in body && typeof body.secret_id !== 'string') errors.push('secret_id must be string');
  if ('secret' in body && 'secret_id' in body) {
    errors.push('mutually exclusive: pass either secret (plaintext) OR secret_id (reference), not both');
  }
  return errors;
}

const errors = validate(body);
console.log('=== Body under test ===');
console.log(JSON.stringify(body, null, 2));
console.log();
console.log('=== Validation result ===');
console.log(errors.length === 0 ? 'VALID ✓' : errors.join('\n'));
console.log();

// Build the full curl
const ACCOUNT_ID = '$CLOUDFLARE_ACCOUNT_ID';
const GATEWAY_ID = 'my-gateway';
const CONFIG_ID  = '00000000-0000-0000-0000-000000000000'; // from POST /provider_configs response
const TOKEN      = '$CLOUDFLARE_API_TOKEN';

const curl = `curl -X PUT "https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/ai-gateway/gateways/${GATEWAY_ID}/provider_configs/${CONFIG_ID}" \\
  -H "Authorization: Bearer ${TOKEN}" \\
  -H "Content-Type: application/json" \\
  -d '${JSON.stringify(body)}'`;

console.log('=== Equivalent curl ===');
console.log(curl);
console.log();

// Build the equivalent fetch() call
const url = `https://api.cloudflare.com/client/v4/accounts/${ACCOUNT_ID}/ai-gateway/gateways/${GATEWAY_ID}/provider_configs/${CONFIG_ID}`;
const init = {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${TOKEN}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(body),
};
console.log('=== Equivalent fetch() in a Worker ===');
console.log(`await fetch(${JSON.stringify(url)}, ${JSON.stringify(init, null, 2)});`);
console.log();

// Now also test the "default" alias case
const defaultBody = { ...body, alias: 'default', default_config: true };
const defaultErrors = validate(defaultBody);
console.log('=== Same body but alias="default", default_config=true ===');
console.log(JSON.stringify(defaultBody, null, 2));
console.log('Validation:', defaultErrors.length === 0 ? 'VALID ✓' : defaultErrors.join('\n'));
