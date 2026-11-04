---
name: backend-serverless-ts
description: |
  Serverless TypeScript backend patterns for AWS Lambda + API Gateway with middy middleware and Powertools.
  Use when building Lambda handlers, optimizing cold starts, or structuring serverless TypeScript projects.
  Triggers on: "Lambda", "API Gateway", "serverless", "middy", "Powertools", "cold start", "handler".
---

# Backend Serverless TypeScript

Production patterns for AWS Lambda + API Gateway with TypeScript, middy middleware, and AWS Lambda Powertools.

## Version Matrix

| Package | Version | Notes |
|---------|---------|-------|
| Node.js | 22 LTS | Via nvm — `nvm use 22` |
| TypeScript | 5.7+ | Strict mode required |
| esbuild | 0.24.x | Bundler for Lambda |
| middy | 5.x | Middleware engine |
| @aws-lambda-powertools/logger | 2.x | Structured JSON logging |
| @aws-lambda-powertools/tracer | 2.x | X-Ray tracing |
| @aws-lambda-powertools/metrics | 2.x | CloudWatch EMF |
| @aws-sdk/client-dynamodb | 3.x | Modular SDK (NOT aws-sdk v2) |
| Zod | 3.x | Runtime validation |
| nx | 21.x | Monorepo tooling |

## CRITICAL: Always Use nvm for Node.js

```bash
source ~/.nvm/nvm.sh
nvm use 22 || nvm install 22
```

## Nx Monorepo Structure (npm workspaces)

```
apps/
├── api/                    # Lambda functions
│   ├── src/
│   │   ├── functions/      # One file per Lambda handler
│   │   │   ├── get-item.ts
│   │   │   ├── create-item.ts
│   │   │   └── process-job.ts
│   │   ├── middleware/     # Custom middy middleware
│   │   │   ├── auth.ts
│   │   │   ├── validate.ts
│   │   │   └── error-handler.ts
│   │   └── lib/            # Shared helpers within api app
│   ├── project.json        # Nx project config
│   └── tsconfig.json
└── web/                    # Angular 21.x frontend
    ├── src/
    ├── project.json
    └── tsconfig.json
libs/
├── shared/                 # Shared types, utilities, constants
│   ├── src/
│   │   ├── types/
│   │   └── utils/
│   └── package.json
└── db/                     # Drizzle schema, DynamoDB entities
    ├── src/
    │   ├── drizzle/        # Aurora schema
    │   └── dynamo/         # DynamoDB Toolbox entities
    └── package.json
package.json                # Root npm workspaces config
nx.json
tsconfig.base.json
```

Root `package.json` workspaces:

```json
{
  "name": "my-app",
  "workspaces": ["apps/*", "libs/*"],
  "scripts": {
    "build:api": "nx build api",
    "build:web": "nx build web",
    "test": "nx run-many --target=test"
  }
}
```

## Lambda Handler Pattern

```typescript
// apps/api/src/functions/get-item.ts
import middy from '@middy/core';
import { APIGatewayProxyEventV2, APIGatewayProxyResultV2 } from 'aws-lambda';
import { Logger } from '@aws-lambda-powertools/logger';
import { Tracer } from '@aws-lambda-powertools/tracer';
import { Metrics, MetricUnit } from '@aws-lambda-powertools/metrics';
import { injectLambdaContext } from '@aws-lambda-powertools/logger/middleware';
import { captureLambdaHandler } from '@aws-lambda-powertools/tracer/middleware';
import { logMetrics } from '@aws-lambda-powertools/metrics/middleware';
import { authMiddleware } from '../middleware/auth.js';
import { errorHandlerMiddleware } from '../middleware/error-handler.js';

const logger = new Logger({ serviceName: 'api', logLevel: 'INFO' });
const tracer = new Tracer({ serviceName: 'api' });
const metrics = new Metrics({ namespace: 'MyApp', serviceName: 'api' });

const lambdaHandler = async (
  event: APIGatewayProxyEventV2
): Promise<APIGatewayProxyResultV2> => {
  const { id } = event.pathParameters ?? {};
  if (!id) {
    return { statusCode: 400, body: JSON.stringify({ error: 'Missing id' }) };
  }

  logger.info('Fetching item', { itemId: id });
  metrics.addMetric('ItemFetched', MetricUnit.Count, 1);

  // Business logic here
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, name: 'example' }),
  };
};

export const handler = middy(lambdaHandler)
  .use(injectLambdaContext(logger, { clearState: true }))
  .use(captureLambdaHandler(tracer))
  .use(logMetrics(metrics, { captureColdStartMetric: true }))
  .use(authMiddleware())
  .use(errorHandlerMiddleware());
```

## ESM Configuration

Lambda Node.js 22 supports ESM natively. Use ESM for smaller bundles and better tree shaking.

```json
// tsconfig.json (per app)
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "target": "ES2022",
    "outDir": "dist"
  }
}
```

```json
// package.json (apps/api)
{
  "type": "module"
}
```

## esbuild Config for Lambda Bundles

```typescript
// apps/api/esbuild.config.ts
import { build } from 'esbuild';

await build({
  entryPoints: ['src/functions/*.ts'],
  bundle: true,
  platform: 'node',
  target: 'node22',
  format: 'esm',
  outdir: 'dist',
  // Bundle everything including AWS SDK v3 — Lambda runtime only includes SDK v2 which we don't use.
  treeShaking: true,
  minify: true,
  sourcemap: true,
  // Split per function for smaller cold start
  splitting: true,
  chunkNames: 'chunks/[name]-[hash]',
});
```

## API Gateway Integration

**HTTP API (prefer)**: Lower cost, faster, simpler. Use for REST workloads.
**REST API**: Use only when needing WAF, usage plans, edge-optimized, or request transformation.

```typescript
// HTTP API event type
import { APIGatewayProxyEventV2, APIGatewayProxyResultV2 } from 'aws-lambda';

// REST API event type
import { APIGatewayProxyEvent, APIGatewayProxyResult } from 'aws-lambda';
```

CORS on HTTP API (preferred — configure at API level, not Lambda):

```hcl
# Terraform
resource "aws_apigatewayv2_api" "main" {
  name          = "my-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_headers = ["Content-Type", "Authorization"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_origins = ["https://app.example.com"]
    max_age       = 300
  }
}
```

## IAM Least Privilege Per Function

Each Lambda gets its own execution role. Never share roles across functions.

```hcl
# Minimum role — add only what the function needs
resource "aws_iam_role_policy" "get_item" {
  name   = "get-item-policy"
  role   = aws_iam_role.get_item.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem"]
      Resource = aws_dynamodb_table.items.arn
    }]
  })
}
```

## Environment Management

Never hardcode config. Use SSM Parameter Store for non-secrets, Secrets Manager for credentials.

```typescript
// lib/config.ts — loaded once outside handler (module scope)
import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm';

const ssmClient = new SSMClient({});

// Cache outside handler for warm invocations
let cachedConfig: AppConfig | null = null;

export async function getConfig(): Promise<AppConfig> {
  if (cachedConfig) return cachedConfig;
  const { Parameter } = await ssmClient.send(
    new GetParameterCommand({ Name: '/myapp/config', WithDecryption: true })
  );
  cachedConfig = JSON.parse(Parameter!.Value!);
  return cachedConfig;
}
```

Reference SSM path via environment variable set in Lambda config:
`CONFIG_PARAM_PATH=/myapp/prod/config`

## When NOT to Use This Stack

- Express.js monoliths with shared state — use ECS instead
- Processes running longer than 15 minutes — use ECS or Batch
- WebSocket servers — use API Gateway WebSocket API + Lambda (different pattern)
- Simple static sites — use S3 + CloudFront
- Sub-10ms latency requirements — Lambda cold starts may violate SLA

## See Also

- `database-aurora-serverless` — Drizzle ORM + RDS Proxy connection patterns
- `dynamodb-patterns` — Single-table design, DynamoDB Toolbox
- `sqs-async-jobs` — SQS triggers, DLQ, idempotency
- `testing-serverless` — Vitest, DynamoDB Local, LocalStack
- `COLD-START.md` — Bundle optimization, provisioned concurrency
- `MIDDLEWARE.md` — Complete middy middleware catalog
