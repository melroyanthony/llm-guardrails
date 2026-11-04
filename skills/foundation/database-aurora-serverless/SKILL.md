---
name: database-aurora-serverless
description: |
  Aurora Serverless v2 with Drizzle ORM for TypeScript Lambda, including RDS Proxy connection pooling.
  Use when setting up PostgreSQL for serverless TypeScript with Aurora and Drizzle ORM.
  Triggers on: "Aurora", "Drizzle", "RDS Proxy", "serverless database", "connection pooling".
---

# Database: Aurora Serverless v2 + Drizzle ORM

Production PostgreSQL for serverless TypeScript. Aurora Serverless v2 scales compute automatically; RDS Proxy prevents connection exhaustion from Lambda.

## Version Matrix

| Package | Version | Notes |
|---------|---------|-------|
| Drizzle ORM | 0.38.x | TypeScript-first ORM |
| drizzle-kit | 0.30.x | Migration CLI |
| pg | 8.x | PostgreSQL client |
| @types/pg | 8.x | Type definitions |
| Aurora PostgreSQL | 16.x | Engine version |
| RDS Proxy | — | Managed connection pooling |

## Why RDS Proxy is Required for Lambda

Lambda creates a new Node.js process per concurrent invocation. Without RDS Proxy:

```
100 concurrent Lambdas → 100 PostgreSQL connections
PostgreSQL max_connections = ~100 (on small Aurora) → connection exhaustion
Result: "too many connections" errors under load
```

With RDS Proxy:
```
100 concurrent Lambdas → RDS Proxy pool (5-10 actual connections to Aurora)
Lambda connects to Proxy (fast, lightweight) → Proxy multiplexes to DB
Result: handles thousands of Lambda invocations with fixed connection pool
```

See `RDS-PROXY.md` for full configuration.

## Drizzle Schema Setup

```typescript
// libs/db/src/drizzle/schema.ts
import {
  pgTable, text, integer, timestamp, uuid, boolean, index,
} from 'drizzle-orm/pg-core';
import { relations } from 'drizzle-orm';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  name: text('name').notNull(),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
  updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
});

export const items = pgTable('items', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: uuid('user_id').notNull().references(() => users.id, { onDelete: 'cascade' }),
  name: text('name').notNull(),
  status: text('status', { enum: ['active', 'archived'] }).notNull().default('active'),
  quantity: integer('quantity').notNull().default(0),
  createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
}, (table) => ({
  userIdIdx: index('items_user_id_idx').on(table.userId),
  statusIdx: index('items_status_idx').on(table.status),
}));

export const usersRelations = relations(users, ({ many }) => ({
  items: many(items),
}));

export const itemsRelations = relations(items, ({ one }) => ({
  user: one(users, { fields: [items.userId], references: [users.id] }),
}));
```

## Drizzle Client Connection

Connect via RDS Proxy endpoint (NOT direct Aurora endpoint from Lambda):

```typescript
// libs/db/src/drizzle/client.ts
import { drizzle } from 'drizzle-orm/node-postgres';
import { Pool } from 'pg';
import * as schema from './schema.js';

// CRITICAL: Pool outside handler — reused across warm invocations
let _db: ReturnType<typeof drizzle> | null = null;
let _pool: Pool | null = null;

// Preferred: fetch password from Secrets Manager at cold start (not env var).
// Set DB_SECRET_ARN as Lambda env var, retrieve the secret JSON at init.
import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';

let _cachedPassword: string | null = null;
const smClient = new SecretsManagerClient({});

async function getPassword(): Promise<string> {
  if (_cachedPassword) return _cachedPassword;
  const secretArn = process.env.DB_SECRET_ARN!;
  const resp = await smClient.send(new GetSecretValueCommand({ SecretId: secretArn }));
  const parsed = JSON.parse(resp.SecretString!);
  _cachedPassword = parsed.password;
  return _cachedPassword!;
}

async function getConnectionString(): Promise<string> {
  const host = process.env.DB_PROXY_ENDPOINT!;  // Matches SERVERLESS-IAC.md Terraform output
  const port = process.env.DB_PORT ?? '5432';
  const name = process.env.DB_NAME!;
  const user = process.env.DB_USER ?? 'dbadmin';
  const pass = await getPassword();
  return `postgresql://${user}:${pass}@${host}:${port}/${name}?sslmode=require`;
}

// getDb() is async — await the connection string before constructing Pool.
export async function getDb() {
  if (!_db) {
    const connStr = await getConnectionString();
    _pool = new Pool({
      connectionString: connStr,
      max: 2,               // Keep small — RDS Proxy handles the real pool
      idleTimeoutMillis: 10_000,
      connectionTimeoutMillis: 3_000,
      ssl: { rejectUnauthorized: true },
    });
    _db = drizzle(_pool, { schema });
  }
  return _db;
}
```

Pool `max: 2` per Lambda instance is intentional. RDS Proxy multiplexes connections, so per-Lambda pool should stay minimal.

## Drizzle Config (drizzle.config.ts)

```typescript
// drizzle.config.ts (root of libs/db)
import type { Config } from 'drizzle-kit';

export default {
  schema: './src/drizzle/schema.ts',
  out: './migrations',
  dialect: 'postgresql',
  dbCredentials: {
    // Use direct Aurora endpoint for migrations (NOT Proxy — Proxy doesn't support DDL)
    url: process.env.DATABASE_URL!,
  },
  verbose: true,
  strict: true,
} satisfies Config;
```

## Migration Workflow

```bash
# 1. Generate migration from schema changes
npx drizzle-kit generate

# 2. Review generated SQL in migrations/
cat migrations/0001_*.sql

# 3. Apply to development database
npx drizzle-kit migrate

# 4. Apply to production (via CI/CD pipeline)
DATABASE_URL=$PROD_URL npx drizzle-kit migrate

# 5. Verify applied migrations
npx drizzle-kit status
```

CRITICAL: Run migrations against the Aurora writer endpoint directly, NOT through RDS Proxy (Proxy may terminate long DDL transactions).

## Query Patterns

### Basic CRUD

```typescript
import { getDb } from '../client.js';
import { items, users } from '../schema.js';
import { eq, and, desc } from 'drizzle-orm';

// Select with join
export async function getUserItems(userId: string) {
  const db = await getDb();
  return db.query.items.findMany({
    where: eq(items.userId, userId),
    orderBy: [desc(items.createdAt)],
    limit: 50,
  });
}

// Insert
export async function createItem(data: typeof items.$inferInsert) {
  const db = await getDb();
  const [created] = await db.insert(items).values(data).returning();
  return created;
}

// Update
export async function archiveItem(id: string, userId: string) {
  const db = await getDb();
  const [updated] = await db
    .update(items)
    .set({ status: 'archived', updatedAt: new Date() })
    .where(and(eq(items.id, id), eq(items.userId, userId)))
    .returning();
  return updated;
}
```

### Transactions

```typescript
export async function transferItems(
  fromUserId: string,
  toUserId: string,
  itemIds: string[]
) {
  const db = await getDb();
  return db.transaction(async (tx) => {
    // Verify ownership
    const owned = await tx
      .select()
      .from(items)
      .where(and(eq(items.userId, fromUserId)))
      .for('update');  // Row-level lock

    await tx
      .update(items)
      .set({ userId: toUserId })
      .where(eq(items.userId, fromUserId));

    return owned;
  });
}
```

### Prepared Statements

```typescript
// Prepared statements — compiled once, executed many times
import { placeholder } from 'drizzle-orm';

const prepared = db
  .select()
  .from(items)
  .where(eq(items.id, placeholder('id')))
  .prepare('get_item_by_id');

// Execute
const result = await prepared.execute({ id: 'some-uuid' });
```

## Aurora Serverless v2 Configuration

```hcl
resource "aws_rds_cluster" "main" {
  cluster_identifier      = "myapp-aurora"
  engine                  = "aurora-postgresql"
  engine_version          = "16.4"
  engine_mode             = "provisioned"  # v2 uses "provisioned" not "serverless"
  database_name           = "myapp"
  master_username         = "myapp_admin"
  manage_master_user_password = true       # Stores in Secrets Manager automatically

  serverlessv2_scaling_configuration {
    min_capacity = 0.5    # Minimum 0.5 ACU (~1GB RAM)
    max_capacity = 8      # Maximum 8 ACU (~16GB RAM) — adjust per load
  }

  # CRITICAL: Do NOT enable auto-pause in production
  # auto_pause = false (default for v2)

  backup_retention_period = 7
  deletion_protection     = true
  skip_final_snapshot     = false
}
```

ACU sizing: 1 ACU = 2GB RAM + proportional CPU. Start at 0.5-2 min, 8-16 max. Review CloudWatch ACU metrics after launch.

## Connection String via Secrets Manager

Lambda retrieves the password from Secrets Manager at cold start:

```typescript
import { SecretsManagerClient, GetSecretValueCommand } from '@aws-sdk/client-secrets-manager';

const secretsClient = new SecretsManagerClient({});
let cachedSecret: { username: string; password: string } | null = null;

async function getDbSecret() {
  if (cachedSecret) return cachedSecret;
  const { SecretString } = await secretsClient.send(
    new GetSecretValueCommand({ SecretId: process.env.DB_SECRET_ARN! })
  );
  cachedSecret = JSON.parse(SecretString!);
  return cachedSecret;
}
```

## When NOT to Use Aurora Serverless

- Simple key-value lookups → use DynamoDB (lower latency, no connection overhead)
- Budget <$10/month → use SQLite (Turso/LiteFS) or Neon serverless Postgres
- Read-heavy analytics → add Aurora read replica or use Athena
- Full-text search → combine with OpenSearch

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `too many connections` | RDS Proxy not configured | Add RDS Proxy, reduce pool max |
| `SSL SYSCALL error: EOF` | SSL not configured | Add `ssl: { rejectUnauthorized: true }` |
| `Connection timeout` | Lambda not in VPC or wrong security group | Check VPC config, SG inbound 5432 |
| `Migration failed mid-way` | Long DDL on small ACU | Scale up ACU before migration, use transactions |
| `ACU scaling delay` | Aurora scaling to handle traffic spike | Increase min_capacity or add provisioned instance |

## See Also

- `RDS-PROXY.md` — Connection pooling deep dive, Terraform config
- `backend-serverless-ts` — Lambda handler and connection initialization patterns
- `testing-serverless` — Drizzle test patterns with pg containers
