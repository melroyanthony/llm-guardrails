---
name: dynamodb-patterns
description: |
  DynamoDB single-table design, GSI strategies, and DynamoDB Toolbox for TypeScript.
  Use when designing DynamoDB tables, access patterns, or integrating DynamoDB with Lambda.
  Triggers on: "DynamoDB", "single-table", "GSI", "DynamoDB Toolbox", "partition key", "access pattern".
---

# DynamoDB Patterns

Production DynamoDB for TypeScript serverless. Single-table design eliminates cross-table round trips; DynamoDB Toolbox provides type-safe entity operations with full AWS SDK v3 integration.

## Version Matrix

| Package | Version | Notes |
|---|---|---|
| dynamodb-toolbox | 1.x | Type-safe entity modeling on AWS SDK v3 |
| @aws-sdk/client-dynamodb | 3.x | Low-level DynamoDB client |
| @aws-sdk/lib-dynamodb | 3.x | DocumentClient — marshalls/unmarshalls JS types automatically |
| @aws-sdk/util-dynamodb | 3.x | marshall/unmarshall utilities for custom serialization |
| Node.js | 22 LTS | Required runtime (via nvm) |

Install:
```bash
npm install dynamodb-toolbox @aws-sdk/client-dynamodb @aws-sdk/lib-dynamodb
```

## Single-Table Design Philosophy

Relational databases normalize data to avoid duplication. DynamoDB single-table design does the opposite: denormalize all entities into one table, shaped around your access patterns.

**Why one table:**
- One DynamoDB endpoint call per operation — no joins across multiple requests
- Item collections let you fetch related entities in a single `Query`
- Consistent sub-millisecond latency at any scale
- Simpler IAM (one table ARN, one policy)
- Connection-free — no pool exhaustion under Lambda concurrency

**Design process (always in this order):**
1. List all access patterns before writing any schema
2. Build an entity chart: entity name, PK, SK, attributes, GSI keys
3. Design GSIs only for access patterns the base table cannot serve
4. Verify each access pattern maps to exactly one query

## Key Design Patterns

### PK/SK Naming Conventions

```
Base table: PK (partition key) + SK (sort key)
Item collection: all items sharing the same PK are co-located

Single value:   ENTITY_TYPE#<id>            e.g., USER#abc-123
Composite SK:   TYPE#VALUE                  e.g., CONFIG#widget-456
Timestamp SK:   TYPE#<ISO_TIMESTAMP>        e.g., STATE#2024-03-15T10:30:00.000Z
```

### Composite Sort Keys for Range Queries

Sort keys are lexicographically ordered. ISO 8601 timestamps sort chronologically:

```
SK = "STATE#2024-03-15T10:30:00.000Z"
→ Query: SK between "STATE#2024-03-01" and "STATE#2024-04-01"
→ Returns all states in March, in creation order, in a single query
```

### GSI Overloading

Reuse the same physical GSI attribute columns across entity types, storing different logical values per entity:

```
ComponentConfig: gsi1pk = "TYPE#slider",   gsi1sk = "UPDATED#2024-03-15T..."
EngineState:     gsi1pk = "ENGINE#eng-1",  gsi1sk = "STATE#v3"
Theme:           gsi1pk = "TENANT#t-99",   gsi1sk = "THEME#dark"
```

All three use `gsi1pk`/`gsi1sk` columns but project different data. One GSI serves multiple access patterns.

## DynamoDB Toolbox Setup

### Table Definition

```typescript
// libs/dynamo/src/table.ts
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient } from '@aws-sdk/lib-dynamodb';
import { Table } from 'dynamodb-toolbox';

const dynamoClient = new DynamoDBClient({
  region: process.env.AWS_REGION ?? 'us-east-1',
});

export const documentClient = DynamoDBDocumentClient.from(dynamoClient, {
  marshallOptions: {
    removeUndefinedValues: true,
    convertEmptyValues: false,
  },
});

export const MainTable = new Table({
  name: process.env.DYNAMODB_TABLE_NAME!,
  partitionKey: { name: 'pk', type: 'string' },
  sortKey: { name: 'sk', type: 'string' },
  indexes: {
    GSI1: {
      type: 'global',
      partitionKey: { name: 'gsi1pk', type: 'string' },
      sortKey: { name: 'gsi1sk', type: 'string' },
    },
    GSI2: {
      type: 'global',
      partitionKey: { name: 'gsi2pk', type: 'string' },
      sortKey: { name: 'gsi2sk', type: 'string' },
    },
  },
  documentClient,
});
```

### Entity Definitions with Typed Attributes

See `SINGLE-TABLE.md` for complete entity definitions with all GSI key mappings.

A minimal example showing the pattern:

```typescript
// libs/dynamo/src/entities/component-config.entity.ts
import { Entity, item, string, number, map } from 'dynamodb-toolbox';
import { MainTable } from '../table.js';

export const ComponentConfigEntity = new Entity({
  name: 'ComponentConfig',
  table: MainTable,
  schema: item({
    pk:            string().key().hidden(),
    sk:            string().key().hidden(),
    gsi1pk:        string().optional().hidden(),
    gsi1sk:        string().optional().hidden(),
    userId:        string(),
    componentId:   string(),
    componentType: string(),
    config:        map({}),
    version:       number().default(1),
    updatedAt:     string(),
    expiresAt:     number().optional(),
  }),
});
```

### Operations

```typescript
// Put (create or overwrite)
await ComponentConfigEntity.put({
  pk: `USER#${userId}`,
  sk: `CONFIG#${componentId}`,
  gsi1pk: `TYPE#${componentType}`,
  gsi1sk: `UPDATED#${new Date().toISOString()}`,
  gsi2pk: `TENANT#${tenantId}`,
  gsi2sk: `CONFIG#${componentId}`,
  userId,
  tenantId,
  componentId,
  componentType,
  config: { min: 0, max: 100, step: 5 },
  version: 1,
  updatedAt: new Date().toISOString(),
}).go();

// Get (exact key lookup)
const { Item } = await ComponentConfigEntity.get({
  pk: `USER#${userId}`,
  sk: `CONFIG#${componentId}`,
}).go();

// Query (base table — all configs for a user, sorted by sk)
const { Items } = await ComponentConfigEntity.query(`USER#${userId}`, {
  beginsWith: 'CONFIG#',
  limit: 100,
}).go();

// Query (GSI1 — all configs of a type, sorted by update time)
const { Items } = await ComponentConfigEntity.query(`TYPE#${componentType}`, {
  index: 'GSI1',
  beginsWith: 'UPDATED#2024-03',
  limit: 200,
}).go();
```

## UI Config Use Case

Storing Angular component configurations with versioning and TTL:

- Latest version stored at `SK = CONFIG#<componentId>` (overwritten on each save)
- Version history stored at `SK = CONFIG#<componentId>#v<n>` (append-only)
- Draft configs: `expiresAt = now + 7 * 86400` (7 days from creation)
- Published configs: omit `expiresAt` so they never expire
- GSI1 enables admin queries: "show all slider configs updated this week across all users"

## Capacity Modes Decision

| Mode | Use When | Avoid When |
|---|---|---|
| On-demand | Unpredictable or spiky traffic, new projects | Steady high-throughput (costs ~7x more than provisioned at constant load) |
| Provisioned | Predictable traffic patterns, cost-sensitive | Traffic with sudden 10x bursts without warm-up |
| Provisioned + Auto-scaling | Most production workloads | Very spiky serverless (on-demand usually cheaper) |

Start with on-demand. After 30 days of CloudWatch metrics, switch to provisioned if traffic is predictable.

## Batch Operations

```typescript
import { execute, BatchWrite, TransactWrite } from 'dynamodb-toolbox';

// BatchWrite — up to 25 items per call, no ACID guarantees
const result = await execute(
  BatchWrite(
    ComponentConfigEntity.putBatch({ pk: 'USER#u1', sk: 'CONFIG#c1', /* ... */ }),
    ComponentConfigEntity.putBatch({ pk: 'USER#u1', sk: 'CONFIG#c2', /* ... */ }),
    ComponentConfigEntity.deleteBatch({ pk: 'USER#u1', sk: 'CONFIG#old' }),
  )
);

// TransactWrite — up to 100 items, all-or-nothing ACID guarantees
await execute(
  TransactWrite(
    ComponentConfigEntity.putTransaction({ pk: 'USER#u1', sk: 'CONFIG#c1', /* ... */ }),
    EngineStateEntity.updateTransaction({
      pk: 'ENGINE#eng-1',
      sk: 'STATE#v3',
      updatedAt: new Date().toISOString(),
    }),
  )
);
```

## When NOT to Use DynamoDB

| Requirement | Better Choice |
|---|---|
| Complex joins across entity types | Aurora PostgreSQL + Drizzle ORM |
| Full-text search (fuzzy, stemming, autocomplete) | OpenSearch / Elasticsearch |
| Analytics, aggregations, GROUP BY, window functions | Athena over S3, Redshift |
| Transactions spanning > 100 items | Aurora with serializable isolation |
| Ad-hoc queries during early development | PostgreSQL (DynamoDB requires upfront access pattern design) |
| < $20/month budget with relational data | SQLite (Turso) or PlanetScale |

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `ProvisionedThroughputExceededException` | Burst above provisioned capacity or hot partition | Switch to on-demand, add write sharding to PK |
| Hot partitions | Many requests hitting the same PK (e.g., `GLOBAL#settings`) | Add user/tenant ID prefix to PK for distribution |
| `ValidationException: Item size exceeds 400 KB` | Item too large | Move large payloads to S3, store S3 key in DynamoDB |
| `ConditionalCheckFailedException` | Optimistic lock version mismatch | Retry with exponential backoff, re-read and reapply |
| `TransactionConflictException` | Two concurrent transactions touching the same item | Retry after short delay, reduce transaction scope |
| `ResourceNotFoundException` | Wrong table name or region | Check `DYNAMODB_TABLE_NAME` env var and AWS region |

## See Also

- `SINGLE-TABLE.md` — Worked example: UI component config storage with full entity chart, GSI design, and sample items
- `backend-serverless-ts/SKILL.md` — Lambda handler patterns that use these entity definitions
- `infrastructure/SERVERLESS-IAC.md` — Terraform for DynamoDB table, GSIs, TTL, auto-scaling
