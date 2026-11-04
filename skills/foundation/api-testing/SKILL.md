---
name: api-testing
description: |
  Generate Postman/Bruno collections with environments, pre-request scripts, and test assertions from OpenAPI specs.
  Use when creating API test collections from OpenAPI specs or setting up CI-based API testing.
  Triggers on: "Postman", "Bruno", "API testing", "collection", "OpenAPI", "pre-request script".
---

# API Testing Collections

## Overview

Generate API testing collections from the OpenAPI spec produced in Stage 2. Collections include environments (dev/staging/prod), authentication flows, pre-request scripts, test assertions, and secrets management.

## Postman Collection (v2.1 format)

Generate `solution/docs/api-testing/collection.json`:

```json
{
  "info": {
    "name": "{Project Name} API",
    "_postman_id": "{{$guid}}",
    "description": "Auto-generated from OpenAPI spec",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "auth": {
    "type": "bearer",
    "bearer": [
      {
        "key": "token",
        "value": "{{access_token}}",
        "type": "string"
      }
    ]
  },
  "variable": [
    {
      "key": "base_url",
      "value": "{{base_url}}"
    }
  ],
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Login",
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "const response = pm.response.json();",
                  "pm.test('Status is 200', () => pm.response.to.have.status(200));",
                  "pm.test('Has access token', () => pm.expect(response.access_token).to.exist);",
                  "pm.collectionVariables.set('access_token', response.access_token);",
                  "if (response.refresh_token) {",
                  "  pm.collectionVariables.set('refresh_token', response.refresh_token);",
                  "}"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {
              "mode": "raw",
              "raw": "{\"email\": \"{{test_email}}\", \"password\": \"{{test_password}}\"}"
            },
            "url": "{{base_url}}/api/v1/auth/login"
          }
        }
      ]
    },
    {
      "name": "Health",
      "item": [
        {
          "name": "Health Check",
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "pm.test('Status is 200', () => pm.response.to.have.status(200));",
                  "pm.test('Response has status field', () => {",
                  "  const body = pm.response.json();",
                  "  pm.expect(body.status).to.equal('healthy');",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "auth": {"type": "noauth"},
            "method": "GET",
            "url": "{{base_url}}/health"
          }
        }
      ]
    },
    {
      "name": "Resources",
      "description": "CRUD operations for the primary resource",
      "item": [
        {
          "name": "Create Resource",
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "pm.test('Status is 201', () => pm.response.to.have.status(201));",
                  "const body = pm.response.json();",
                  "pm.test('Has ID', () => pm.expect(body.id).to.exist);",
                  "pm.collectionVariables.set('resource_id', body.id);"
                ]
              }
            }
          ],
          "request": {
            "method": "POST",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {
              "mode": "raw",
              "raw": "{\"name\": \"Test Resource {{$timestamp}}\"}"
            },
            "url": "{{base_url}}/api/v1/resources"
          }
        },
        {
          "name": "List Resources",
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "pm.test('Status is 200', () => pm.response.to.have.status(200));",
                  "pm.test('Returns array', () => pm.expect(pm.response.json()).to.be.an('array'));"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "url": {
              "raw": "{{base_url}}/api/v1/resources?limit=20&offset=0",
              "host": ["{{base_url}}"],
              "path": ["api", "v1", "resources"],
              "query": [
                {"key": "limit", "value": "20"},
                {"key": "offset", "value": "0"}
              ]
            }
          }
        },
        {
          "name": "Get Resource",
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "pm.test('Status is 200', () => pm.response.to.have.status(200));",
                  "pm.test('Has correct ID', () => {",
                  "  pm.expect(pm.response.json().id).to.equal(parseInt(pm.collectionVariables.get('resource_id')));",
                  "});"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "url": "{{base_url}}/api/v1/resources/{{resource_id}}"
          }
        },
        {
          "name": "Update Resource",
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "pm.test('Status is 200', () => pm.response.to.have.status(200));"
                ]
              }
            }
          ],
          "request": {
            "method": "PUT",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "body": {
              "mode": "raw",
              "raw": "{\"name\": \"Updated Resource {{$timestamp}}\"}"
            },
            "url": "{{base_url}}/api/v1/resources/{{resource_id}}"
          }
        },
        {
          "name": "Delete Resource",
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "pm.test('Status is 204', () => pm.response.to.have.status(204));"
                ]
              }
            }
          ],
          "request": {
            "method": "DELETE",
            "url": "{{base_url}}/api/v1/resources/{{resource_id}}"
          }
        },
        {
          "name": "Get Deleted Resource (404)",
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "pm.test('Status is 404', () => pm.response.to.have.status(404));"
                ]
              }
            }
          ],
          "request": {
            "method": "GET",
            "url": "{{base_url}}/api/v1/resources/{{resource_id}}"
          }
        }
      ]
    }
  ]
}
```

## Environment Files

### Development (`solution/docs/api-testing/env.dev.json`)

```json
{
  "id": "dev-env",
  "name": "{Project} - Development",
  "values": [
    {"key": "base_url", "value": "http://localhost:8000", "enabled": true, "type": "default"},
    {"key": "test_email", "value": "admin@example.com", "enabled": true, "type": "default"},
    {"key": "test_password", "value": "devpassword123", "enabled": true, "type": "secret"},
    {"key": "access_token", "value": "", "enabled": true, "type": "secret"},
    {"key": "refresh_token", "value": "", "enabled": true, "type": "secret"},
    {"key": "resource_id", "value": "", "enabled": true, "type": "any"}
  ]
}
```

### Staging (`solution/docs/api-testing/env.staging.json`)

```json
{
  "id": "staging-env",
  "name": "{Project} - Staging",
  "values": [
    {"key": "base_url", "value": "https://staging-api.example.com", "enabled": true, "type": "default"},
    {"key": "test_email", "value": "", "enabled": true, "type": "secret"},
    {"key": "test_password", "value": "", "enabled": true, "type": "secret"},
    {"key": "access_token", "value": "", "enabled": true, "type": "secret"},
    {"key": "refresh_token", "value": "", "enabled": true, "type": "secret"},
    {"key": "resource_id", "value": "", "enabled": true, "type": "any"}
  ]
}
```

### Production (`solution/docs/api-testing/env.prod.json`)

```json
{
  "id": "prod-env",
  "name": "{Project} - Production",
  "values": [
    {"key": "base_url", "value": "https://api.example.com", "enabled": true, "type": "default"},
    {"key": "test_email", "value": "", "enabled": true, "type": "secret"},
    {"key": "test_password", "value": "", "enabled": true, "type": "secret"},
    {"key": "access_token", "value": "", "enabled": true, "type": "secret"},
    {"key": "refresh_token", "value": "", "enabled": true, "type": "secret"},
    {"key": "resource_id", "value": "", "enabled": true, "type": "any"}
  ]
}
```

## Secrets Management

### Rules
- **NEVER** hardcode real secrets in collection or environment files
- Use `type: "secret"` for sensitive values (masked in Postman UI)
- Production environment files should have EMPTY secret values
- Real secrets are injected via:
  - Postman Vault (Postman v11+)
  - Environment variables in CI (`--env-var "key=value"`)
  - `.env` files (gitignored)

### .gitignore Entry
```
# API testing secrets
solution/docs/api-testing/env.prod.json
solution/docs/api-testing/.env
```

## Pre-Request Scripts

### Token Refresh (collection-level)
```javascript
// Auto-refresh expired tokens
const tokenExpiry = pm.collectionVariables.get('token_expiry');
if (tokenExpiry && Date.now() > parseInt(tokenExpiry)) {
  const refreshToken = pm.collectionVariables.get('refresh_token');
  if (refreshToken) {
    pm.sendRequest({
      url: pm.collectionVariables.get('base_url') + '/api/v1/auth/refresh',
      method: 'POST',
      header: {'Content-Type': 'application/json'},
      body: {mode: 'raw', raw: JSON.stringify({refresh_token: refreshToken})}
    }, (err, res) => {
      if (!err && res.code === 200) {
        const body = res.json();
        pm.collectionVariables.set('access_token', body.access_token);
        pm.collectionVariables.set('token_expiry', String(Date.now() + 14 * 60 * 1000));
      }
    });
  }
}
```

## CLI Execution (Newman)

```bash
# Run collection against dev environment
npx newman run solution/docs/api-testing/collection.json \
  -e solution/docs/api-testing/env.dev.json \
  --reporters cli,json \
  --reporter-json-export results.json

# Run in CI with secrets from environment variables
npx newman run solution/docs/api-testing/collection.json \
  -e solution/docs/api-testing/env.staging.json \
  --env-var "test_email=$TEST_EMAIL" \
  --env-var "test_password=$TEST_PASSWORD" \
  --bail

# Run specific folder only
npx newman run solution/docs/api-testing/collection.json \
  -e solution/docs/api-testing/env.dev.json \
  --folder "Resources"
```

## Bruno Alternative

For teams preferring open-source, generate Bruno collection format:

```
solution/docs/api-testing/bruno/
├── bruno.json              # Collection config
├── environments/
│   ├── dev.bru
│   ├── staging.bru
│   └── prod.bru
├── health/
│   └── health-check.bru
├── auth/
│   └── login.bru
└── resources/
    ├── create.bru
    ├── list.bru
    ├── get.bru
    ├── update.bru
    └── delete.bru
```

## Generation Process

1. Read `solution/docs/architecture/openapi.yaml`
2. For each path + method, generate a request with:
   - Correct URL, method, headers
   - Example request body from schema
   - Test assertions for expected status codes
   - Variable extraction for IDs (POST responses)
3. Order requests as a runnable flow: Auth → Create → Read → Update → Delete → Verify Delete
4. Generate environment files for dev/staging/prod
5. Mark secret fields appropriately
6. Add pre-request scripts for auth token management

## When NOT to Use
- **gRPC APIs**: Use grpcurl or Evans — Postman/Bruno have limited gRPC support
- **WebSocket testing**: Use wscat or dedicated WebSocket testing tools
- **GraphQL**: Use GraphQL Playground or Altair — Postman's GraphQL support is basic
- **Serverless Lambda integration tests**: Use `testing-serverless` skill with LocalStack

## Output Files

| File | Purpose |
|------|---------|
| `solution/docs/api-testing/collection.json` | Postman v2.1 collection |
| `solution/docs/api-testing/env.dev.json` | Development environment |
| `solution/docs/api-testing/env.staging.json` | Staging environment (empty secrets) |
| `solution/docs/api-testing/env.prod.json` | Production environment (empty secrets, gitignored) |
