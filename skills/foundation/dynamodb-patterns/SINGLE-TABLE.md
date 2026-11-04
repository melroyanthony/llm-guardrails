# Single-Table Design: UI Component Config Storage

Worked example for a system storing Angular component configurations, engine state, themes, and user preferences in one DynamoDB table. Use this as a reference template — adapt the entity chart to your actual access patterns.

## Step 1: Define Access Patterns

Always list access patterns before designing keys. Every GSI and every SK design decision traces back to an access pattern here.

| # | Access Pattern | Query Type | Key Used |
|---|---|---|---|
| 1 | Get component config by component ID (for a user) | Point read | PK=`USER#<userId>`, SK=`CONFIG#<componentId>` |
| 2 | List all configs for a user | Query | PK=`USER#<userId>`, SK begins_with `CONFIG#` |
| 3 | List configs for a user by component type | Query | PK=`USER#<userId>`, SK begins_with `CONFIG#<type>#` |
| 4 | List all configs of a type across all users (sorted by update time) | GSI1 query | GSI1PK=`TYPE#<componentType>`, GSI1SK begins_with `UPDATED#` |
| 5 | Get engine state by engine ID (for a user) | Point read | PK=`USER#<userId>`, SK=`ENGINE#<engineId>` |
| 6 | List all engine states for a user | Query | PK=`USER#<userId>`, SK begins_with `ENGINE#` |
| 7 | Get theme by theme ID | Point read | PK=`THEME#<themeId>`, SK=`METADATA` |
| 8 | List configs by tenant (multi-tenant admin view) | GSI2 query | GSI2PK=`TENANT#<tenantId>`, GSI2SK begins_with `CONFIG#` |
| 9 | Get user preferences | Point read | PK=`USER#<userId>`, SK=`PREFS` |
| 10 | List recently updated configs across a tenant (last 30 days) | GSI2 query | GSI2PK=`TENANT#<tenantId>`, GSI2SK begins_with `UPDATED#<year-month>` |

## Step 2: Entity Chart

| Entity | PK | SK | GSI1PK | GSI1SK | GSI2PK | GSI2SK |
|---|---|---|---|---|---|---|
| ComponentConfig | `USER#<userId>` | `CONFIG#<type>#<componentId>` | `TYPE#<componentType>` | `UPDATED#<ISO_timestamp>` | `TENANT#<tenantId>` | `CONFIG#<componentId>` |
| EngineState | `USER#<userId>` | `ENGINE#<engineId>#v<version>` | — | — | `TENANT#<tenantId>` | `ENGINE#<engineId>` |
| Theme | `THEME#<themeId>` | `METADATA` | — | — | — | — |
| UserPreference | `USER#<userId>` | `PREFS` | — | — | — | — |

## Step 3: PK/SK Design Per Entity

### ComponentConfig

```
PK:     USER#<userId>
SK:     CONFIG#<componentType>#<componentId>

Examples:
  SK = CONFIG#slider#comp-abc123
  SK = CONFIG#button#comp-xyz789
  SK = CONFIG#datepicker#comp-def456
```

Sort key structure enables three query shapes:
- `SK begins_with CONFIG#` → all configs for a user
- `SK begins_with CONFIG#slider#` → all slider configs for a user
- `SK = CONFIG#slider#comp-abc123` → exact config lookup

```
GSI1PK: TYPE#<componentType>
GSI1SK: UPDATED#<ISO_timestamp>

Example:
  GSI1PK = TYPE#slider
  GSI1SK = UPDATED#2024-03-15T10:30:00.000Z
```

GSI1 enables: "all slider configs updated after date X across all users" — useful for admin dashboards and analytics.

```
GSI2PK: TENANT#<tenantId>
GSI2SK: CONFIG#<componentId>
```

GSI2 enables: "all configs belonging to tenant X" — for multi-tenant admin views.

### EngineState

```
PK:     USER#<userId>
SK:     ENGINE#<engineId>#v<version>

Examples:
  SK = ENGINE#eng-render-v2#v001
  SK = ENGINE#eng-render-v2#v002   (newer version)

Latest state always at the highest v* suffix.
Use SK begins_with ENGINE#<engineId># to list version history.
```

Version numbers are zero-padded (`v001`, `v002`) to sort lexicographically.

### Theme

```
PK:     THEME#<themeId>
SK:     METADATA

Single item per theme. Themes are shared across users, so they live
under their own partition (not under USER#) to avoid hot partitions.
```

### UserPreference

```
PK:     USER#<userId>
SK:     PREFS

Single item per user. Simple point read. No GSI needed.
```

## Step 4: GSI Definitions (Terraform)

```hcl
resource "aws_dynamodb_table" "main" {
  name         = "ui-config-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute { name = "pk";     type = "S" }
  attribute { name = "sk";     type = "S" }
  attribute { name = "gsi1pk"; type = "S" }
  attribute { name = "gsi1sk"; type = "S" }
  attribute { name = "gsi2pk"; type = "S" }
  attribute { name = "gsi2sk"; type = "S" }

  # GSI1: component type queries, sorted by update time
  global_secondary_index {
    name            = "GSI1"
    hash_key        = "gsi1pk"
    range_key       = "gsi1sk"
    projection_type = "ALL"
  }

  # GSI2: tenant queries — projection INCLUDE saves read capacity
  global_secondary_index {
    name               = "GSI2"
    hash_key           = "gsi2pk"
    range_key          = "gsi2sk"
    projection_type    = "INCLUDE"
    non_key_attributes = ["userId", "componentType", "updatedAt", "version"]
  }

  ttl {
    attribute_name = "expiresAt"
    enabled        = true
  }

  point_in_time_recovery { enabled = true }

  tags = merge(var.common_tags, { Environment = var.environment })
}
```

GSI2 uses `INCLUDE` projection (not `ALL`) because the tenant admin view only needs a subset of attributes — this reduces read cost by ~50–70% for large items.

## Step 5: Sample Item Collections (JSON)

All items shown share the same DynamoDB table. Items with the same `pk` form an item collection.

### ComponentConfig — Slider

```json
{
  "pk":            "USER#usr-abc123",
  "sk":            "CONFIG#slider#comp-slider-001",
  "gsi1pk":        "TYPE#slider",
  "gsi1sk":        "UPDATED#2024-03-15T10:30:00.000Z",
  "gsi2pk":        "TENANT#tenant-acme",
  "gsi2sk":        "CONFIG#comp-slider-001",
  "_et":           "ComponentConfig",
  "userId":        "usr-abc123",
  "tenantId":      "tenant-acme",
  "componentId":   "comp-slider-001",
  "componentType": "slider",
  "config":        { "min": 0, "max": 100, "step": 5, "defaultValue": 50 },
  "version":       3,
  "updatedAt":     "2024-03-15T10:30:00.000Z",
  "expiresAt":     1720000000
}
```

### ComponentConfig — Button (same user, different type)

```json
{
  "pk":            "USER#usr-abc123",
  "sk":            "CONFIG#button#comp-btn-007",
  "gsi1pk":        "TYPE#button",
  "gsi1sk":        "UPDATED#2024-03-10T08:00:00.000Z",
  "gsi2pk":        "TENANT#tenant-acme",
  "gsi2sk":        "CONFIG#comp-btn-007",
  "_et":           "ComponentConfig",
  "userId":        "usr-abc123",
  "tenantId":      "tenant-acme",
  "componentId":   "comp-btn-007",
  "componentType": "button",
  "config":        { "variant": "primary", "size": "md", "rounded": true },
  "version":       1,
  "updatedAt":     "2024-03-10T08:00:00.000Z"
}
```

### EngineState — Version 2

```json
{
  "pk":        "USER#usr-abc123",
  "sk":        "ENGINE#eng-render#v002",
  "gsi2pk":    "TENANT#tenant-acme",
  "gsi2sk":    "ENGINE#eng-render",
  "_et":       "EngineState",
  "userId":    "usr-abc123",
  "tenantId":  "tenant-acme",
  "engineId":  "eng-render",
  "state":     { "mode": "light", "breakpoint": "lg", "activeComponents": ["hero", "nav", "footer"] },
  "version":   2,
  "updatedAt": "2024-03-14T12:00:00.000Z"
}
```

### Theme (standalone partition)

```json
{
  "pk":      "THEME#theme-ocean-dark",
  "sk":      "METADATA",
  "_et":     "Theme",
  "themeId": "theme-ocean-dark",
  "name":    "Ocean Dark",
  "cssVariables": {
    "--color-primary": "#006d9e",
    "--color-bg": "#0a1628",
    "--color-text": "#e8f4f8"
  },
  "isPublic":  true,
  "createdBy": "usr-admin-001",
  "createdAt": "2024-01-05T09:00:00.000Z"
}
```

### UserPreference

```json
{
  "pk":       "USER#usr-abc123",
  "sk":       "PREFS",
  "_et":      "UserPreference",
  "userId":   "usr-abc123",
  "language": "en-US",
  "timezone": "America/New_York",
  "theme":    "theme-ocean-dark",
  "updatedAt": "2024-02-20T14:00:00.000Z"
}
```

### Item Collection View — `pk = USER#usr-abc123`

A single `Query(pk="USER#usr-abc123")` returns all 5 items above (plus any others):

```
sk = CONFIG#button#comp-btn-007    ← ComponentConfig
sk = CONFIG#slider#comp-slider-001 ← ComponentConfig
sk = ENGINE#eng-render#v001        ← EngineState (older)
sk = ENGINE#eng-render#v002        ← EngineState (current)
sk = PREFS                         ← UserPreference
```

## Step 6: TTL for Draft Config Expiry

Draft configs (saved but not published) auto-expire after 7 days:

```typescript
const DRAFT_TTL_SECONDS = 7 * 24 * 60 * 60; // 7 days

// On every draft save, compute expiresAt
const expiresAt = Math.floor(Date.now() / 1000) + DRAFT_TTL_SECONDS;

await ComponentConfigEntity.put({
  pk: `USER#${userId}`,
  sk: `CONFIG#${componentType}#${componentId}`,
  // ... other attributes ...
  expiresAt,   // DynamoDB auto-deletes when currentTime > expiresAt
}).go();

// On publish: update the item with expiresAt = undefined to make permanent
await ComponentConfigEntity.update({
  pk: `USER#${userId}`,
  sk: `CONFIG#${componentType}#${componentId}`,
  $remove: ['expiresAt'],
}).go();
```

DynamoDB deletes expired items within 48 hours (not exactly at expiry). Filter in application code when exact precision is required:

```typescript
const now = Math.floor(Date.now() / 1000);
const activeConfigs = items.filter((item) => !item.expiresAt || item.expiresAt > now);
```

## DynamoDB Toolbox Entity Definitions

```typescript
// libs/dynamo/src/entities/index.ts
import { Entity, item, string, number, boolean, map } from 'dynamodb-toolbox';
import { MainTable } from '../table.js';

export const ComponentConfigEntity = new Entity({
  name: 'ComponentConfig',
  table: MainTable,
  schema: item({
    pk:            string().key().hidden(),
    sk:            string().key().hidden(),
    gsi1pk:        string().optional().hidden(),
    gsi1sk:        string().optional().hidden(),
    gsi2pk:        string().optional().hidden(),
    gsi2sk:        string().optional().hidden(),
    userId:        string(),
    tenantId:      string(),
    componentId:   string(),
    componentType: string(),
    config:        map({}),
    version:       number().default(1),
    updatedAt:     string(),
    expiresAt:     number().optional(),
  }),
});

export const EngineStateEntity = new Entity({
  name: 'EngineState',
  table: MainTable,
  schema: item({
    pk:        string().key().hidden(),
    sk:        string().key().hidden(),
    gsi2pk:    string().optional().hidden(),
    gsi2sk:    string().optional().hidden(),
    userId:    string(),
    tenantId:  string(),
    engineId:  string(),
    state:     map({}),
    version:   number().default(1),
    updatedAt: string(),
  }),
});

export const ThemeEntity = new Entity({
  name: 'Theme',
  table: MainTable,
  schema: item({
    pk:           string().key().hidden(),
    sk:           string().key().hidden(),
    themeId:      string(),
    name:         string(),
    cssVariables: map({}),
    isPublic:     boolean().default(false),
    createdBy:    string(),
    createdAt:    string(),
  }),
});

export const UserPreferenceEntity = new Entity({
  name: 'UserPreference',
  table: MainTable,
  schema: item({
    pk:        string().key().hidden(),
    sk:        string().key().hidden(),
    userId:    string(),
    language:  string().optional(),
    timezone:  string().optional(),
    theme:     string().optional(),
    updatedAt: string(),
  }),
});
```

## See Also

- `SKILL.md` — DynamoDB Toolbox setup, capacity mode selection, batch operations, common errors
- `backend-serverless-ts/SKILL.md` — Lambda handlers consuming these entities
- `infrastructure/SERVERLESS-IAC.md` — Full Terraform for DynamoDB table + GSIs + auto-scaling
