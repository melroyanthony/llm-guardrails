# RDS Proxy Deep Dive

RDS Proxy is a fully managed database proxy service that sits between your application (Lambda or ECS) and Aurora. It maintains a warm connection pool and multiplexes thousands of client connections onto a small set of actual PostgreSQL connections to the database.

## Why RDS Proxy is Required for Lambda

### The Connection Exhaustion Problem

PostgreSQL allocates a server process per connection. Lambda creates a new execution environment per concurrent invocation, and each environment opens its own database connection.

```
Aurora db.r6g.large:   max_connections ≈ 870
Aurora db.r6g.xlarge:  max_connections ≈ 1700

Lambda burst concurrency: 1000–3000+ invocations per region

Without RDS Proxy:
  500 concurrent Lambda invocations × 1 pg.Pool connection each
  = 500 connections open simultaneously
  → "FATAL: remaining connection slots are reserved for non-replication superuser connections"
  → New requests begin failing within seconds of a traffic spike
```

Aurora Serverless v2 with 2 ACU has `max_connections ≈ 300`. A moderate burst of 400 concurrent Lambdas exhausts it in under a second.

### How RDS Proxy Fixes This

```
500 concurrent Lambda invocations
        ↓
  RDS Proxy (maintains 20–50 real connections to Aurora)
        ↓
  Aurora sees ≤50 connections — well within limit

Lambda connects to Proxy endpoint (fast, persistent) rather than
opening a fresh TCP connection to PostgreSQL on every invocation.
```

RDS Proxy also provides:
- Connection queuing when all pool slots are busy (up to `connection_borrow_timeout`)
- Transparent Aurora failover without app code changes
- IAM-based auth without managing passwords in Lambda env vars

## IAM Auth vs Password Auth

### Password Auth (simpler, acceptable for most teams)

1. Credentials stored in Secrets Manager
2. RDS Proxy reads Secrets Manager directly — Lambda never sees the password
3. Lambda environment variable points to the Proxy endpoint only
4. Rotate the secret in Secrets Manager; Proxy picks it up without Lambda redeployment

### IAM Auth (preferred for zero-credential management)

Lambda uses its execution role to generate a short-lived auth token (15-minute TTL). No password is stored anywhere.

```typescript
// IAM auth token generation — refresh before pool initialization
import { Signer } from '@aws-sdk/rds-signer';
import { Pool } from 'pg';

const signer = new Signer({
  hostname: process.env.RDS_PROXY_ENDPOINT!,
  port: 5432,
  username: process.env.DB_USER!,
  region: process.env.AWS_REGION!,
});

let _pool: Pool | null = null;
let _tokenExpiry = 0;

async function getPool(): Promise<Pool> {
  const now = Date.now();
  // Refresh token 2 minutes before expiry (token TTL is 15 minutes)
  if (!_pool || now >= _tokenExpiry - 120_000) {
    const token = await signer.getAuthToken();
    _tokenExpiry = now + 15 * 60 * 1000;
    _pool = new Pool({
      host: process.env.RDS_PROXY_ENDPOINT!,
      port: 5432,
      database: process.env.DB_NAME!,
      user: process.env.DB_USER!,
      password: token,           // IAM token used as password
      max: 2,
      ssl: { rejectUnauthorized: true },
    });
  }
  return _pool;
}
```

IAM auth prerequisites:
1. RDS Proxy created with `iam_auth = "REQUIRED"` in the `auth` block
2. Lambda execution role has `rds-db:connect` permission on the proxy resource ARN
3. PostgreSQL user created with `rds_iam` role:
   ```sql
   CREATE USER myapp WITH LOGIN;
   GRANT rds_iam TO myapp;
   ```

IAM auth eliminates secret rotation complexity entirely. Prefer it for new projects.

## TLS Configuration

TLS is enforced between Lambda and RDS Proxy. `require_tls = true` on the proxy rejects plaintext connections.

```typescript
// Option A: System trust store (works on Lambda runtime — AWS CA is included)
const pool = new Pool({
  host: process.env.RDS_PROXY_ENDPOINT!,
  ssl: { rejectUnauthorized: true },
});

// Option B: Bundle the RDS CA certificate (use if system CA is unavailable)
import { readFileSync } from 'node:fs';

const pool = new Pool({
  host: process.env.RDS_PROXY_ENDPOINT!,
  ssl: {
    rejectUnauthorized: true,
    ca: readFileSync(new URL('./rds-combined-ca-bundle.pem', import.meta.url)).toString(),
  },
});
```

Download the combined CA bundle from:
`https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem`

Include the `.pem` file in your Lambda deployment package and reference it via a relative path.

## Connection Limits

### Calculating Target Max Connections

```
Aurora max_connections (PostgreSQL 16 default formula):
  1 ACU  ≈  75 connections  (conservative guidance for sizing proxy)
  2 ACU  ≈ 150 connections
  4 ACU  ≈ 300 connections
  8 ACU  ≈ 600 connections

Target max connections = Aurora ACU × 75
RDS Proxy max_connections_percent = 80
  → Proxy will use up to 80% of Aurora's max_connections

Example at 4 ACU:
  Target = 4 × 75 = 300
  Proxy ceiling = 300 × 0.80 = 240 connections to Aurora
```

Per-Lambda pool `max` should stay at 1–2. RDS Proxy handles the real pooling.

### Timeout Tuning

| Parameter | Default | Recommendation |
|---|---|---|
| `connection_borrow_timeout` | 120s | 10–30s for APIs (fail fast, return error) |
| `idle_client_timeout` | 1800s | 900–1800s (30 min is fine for Lambda) |
| `max_connections_percent` | 100 | 80 (leave headroom for direct admin access) |
| `max_idle_connections_percent` | 50 | 25–50 |

## Terraform Resources

### Core Proxy Configuration

```hcl
resource "aws_db_proxy" "main" {
  name                   = "${var.app_name}-proxy"
  debug_logging          = false
  engine_family          = "POSTGRESQL"
  idle_client_timeout    = 1800
  require_tls            = true
  role_arn               = aws_iam_role.rds_proxy.arn
  vpc_security_group_ids = [aws_security_group.rds_proxy.id]
  vpc_subnet_ids         = var.private_subnet_ids

  auth {
    auth_scheme = "SECRETS"
    iam_auth    = "DISABLED"         # Change to "REQUIRED" for IAM auth
    secret_arn  = aws_secretsmanager_secret.db_credentials.arn
  }

  tags = var.common_tags
}

resource "aws_db_proxy_default_target_group" "main" {
  db_proxy_name = aws_db_proxy.main.name

  connection_pool_config {
    connection_borrow_timeout    = 30
    max_connections_percent      = 80
    max_idle_connections_percent = 50
    # Omit session_pinning_filters to allow full connection multiplexing.
    # Add ["EXCLUDE_VARIABLE_SETS"] only if app uses SET commands.
  }
}

resource "aws_db_proxy_target" "main" {
  db_proxy_name         = aws_db_proxy.main.name
  target_group_name     = aws_db_proxy_default_target_group.main.name
  db_cluster_identifier = aws_rds_cluster.main.cluster_identifier
}

# Optional: reader endpoint for read-heavy patterns
resource "aws_db_proxy_endpoint" "reader" {
  db_proxy_name          = aws_db_proxy.main.name
  db_proxy_endpoint_name = "${var.app_name}-proxy-reader"
  vpc_subnet_ids         = var.private_subnet_ids
  vpc_security_group_ids = [aws_security_group.rds_proxy.id]
  target_role            = "READ_ONLY"
}
```

### IAM Role for the Proxy

```hcl
resource "aws_iam_role" "rds_proxy" {
  name = "${var.app_name}-rds-proxy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "rds.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "rds_proxy_secrets" {
  name = "rds-proxy-secrets-access"
  role = aws_iam_role.rds_proxy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.db_credentials.arn
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = aws_kms_key.secrets.arn
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
}
```

## Multi-AZ Failover Behavior

RDS Proxy handles Aurora failover transparently. The proxy endpoint DNS does not change. Application code requires no updates for failover support.

Failover sequence:
1. Aurora writer instance fails or is patched
2. Aurora promotes a read replica to writer (~20–60 seconds for Aurora v2)
3. RDS Proxy detects the new writer endpoint via internal health checks
4. In-flight transactions against the old writer receive a connection error
5. New requests route to the new writer automatically

Lambda handlers must implement retry logic for the brief failover window:

```typescript
const RETRYABLE_MESSAGES = [
  'Connection terminated unexpectedly',
  'connection reset by server',
  'terminating connection due to administrator command',
];

async function withRetry<T>(fn: () => Promise<T>, attempts = 3): Promise<T> {
  for (let i = 1; i <= attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      const isRetryable =
        err instanceof Error &&
        RETRYABLE_MESSAGES.some((msg) => err.message.includes(msg));

      if (isRetryable && i < attempts) {
        // Exponential backoff: 200ms, 400ms
        await new Promise((r) => setTimeout(r, i * 200));
        continue;
      }
      throw err;
    }
  }
  throw new Error('Unreachable');
}
```

## CloudWatch Monitoring

Key metrics in the `AWS/RDS` namespace with dimension `ProxyName`:

| Metric | Alert Threshold | Meaning |
|---|---|---|
| `DatabaseConnections` | > 80% of Aurora max_connections | Pool near exhaustion |
| `AvailabilityPercentage` | < 99.9 | Proxy degraded |
| `QueryDuration` P99 | > 500ms | Proxy adding latency |
| `MaxConnectionsPercent` | > 85 | Scale up ACU or reduce Lambda concurrency |

```hcl
resource "aws_cloudwatch_metric_alarm" "proxy_connections_high" {
  alarm_name          = "${var.app_name}-rds-proxy-connections-high"
  namespace           = "AWS/RDS"
  metric_name         = "DatabaseConnections"
  dimensions          = { ProxyName = aws_db_proxy.main.name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  threshold           = 200   # Tune to 80% of (ACU * 75)
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "proxy_availability" {
  alarm_name          = "${var.app_name}-rds-proxy-availability"
  namespace           = "AWS/RDS"
  metric_name         = "AvailabilityPercentage"
  dimensions          = { ProxyName = aws_db_proxy.main.name }
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 2
  threshold           = 99.9
  comparison_operator = "LessThanThreshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

Additional metrics to monitor:
- `QueryRequests` — request throughput through the proxy
- `MaxConnectionsPercent` — current pool utilization percentage
- `ClientConnections` — active Lambda-to-proxy connections

## Drizzle ORM Connecting Through RDS Proxy

```typescript
// libs/db/src/client.ts
import { drizzle } from 'drizzle-orm/node-postgres';
import { Pool } from 'pg';
import * as schema from './schema.js';

// Singleton pool — reused across warm Lambda invocations
let _db: ReturnType<typeof drizzle<typeof schema>> | null = null;

export function getDb() {
  if (_db) return _db;

  const pool = new Pool({
    // Always use the Proxy endpoint from Lambda — never the Aurora cluster endpoint
    host: process.env.RDS_PROXY_ENDPOINT!,
    port: 5432,
    database: process.env.DB_NAME!,
    user: process.env.DB_USER!,
    password: process.env.DB_PASSWORD!,   // Or use IAM token pattern above
    // Keep pool small per Lambda instance — Proxy is the real pool
    max: 2,
    idleTimeoutMillis: 10_000,
    connectionTimeoutMillis: 5_000,
    ssl: { rejectUnauthorized: true },
  });

  _db = drizzle(pool, { schema, logger: process.env.NODE_ENV !== 'production' });
  return _db;
}
```

Migration note: Run `drizzle-kit migrate` against the Aurora writer endpoint directly, not through RDS Proxy. Proxy may terminate long-running DDL transactions.

## Session Pinning Warning

Connection multiplexing only works when the session is stateless. The proxy pins a connection to a single client for the session duration if the client uses:

- `SET` statements (e.g., `SET LOCAL search_path`)
- Temporary tables
- Advisory locks
- Prepared transactions or non-standard isolation levels

Pinning reduces multiplexing efficiency and can exhaust the pool under load. Avoid these patterns in Lambda handlers. Use `session_pinning_filters = ["EXCLUDE_VARIABLE_SETS"]` if `SET` usage is unavoidable.

## See Also

- `SKILL.md` — Aurora Serverless v2 cluster setup, Drizzle schema, migration workflow
- `backend-serverless-ts/SKILL.md` — Lambda handler patterns, cold start optimization
- `infrastructure/SERVERLESS-IAC.md` — Full VPC + RDS + Proxy Terraform module
