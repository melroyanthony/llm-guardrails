# Cold Start Optimization for Lambda TypeScript

Target: **<100ms cold start** for Node.js 22 Lambda functions.

## Why Cold Starts Happen

Lambda freezes execution environments between invocations. When a new environment initializes:
1. Runtime bootstrap (~20-40ms for Node.js 22)
2. Function package download + unzip (depends on bundle size)
3. Module evaluation (your `import` statements at top level)
4. Handler initialization code (SDK clients, DB connections)

You control steps 2-4.

## Bundle Size Reduction

### Rule: Target <5MB per function zip, ideally <1MB

```typescript
// esbuild.config.ts
import { build } from 'esbuild';
import { readdirSync } from 'node:fs';
import { join } from 'node:path';

const functions = readdirSync('./src/functions')
  .filter((f) => f.endsWith('.ts'))
  .map((f) => `./src/functions/${f}`);

await build({
  entryPoints: functions,
  bundle: true,
  platform: 'node',
  target: 'node22',
  format: 'esm',
  outdir: 'dist/functions',
  // Bundle AWS SDK v3 — do NOT externalize. Lambda runtime only includes SDK v2.
  treeShaking: true,
  minify: process.env.NODE_ENV === 'production',
  sourcemap: 'linked',        // Separate .map files, not inline
  splitting: true,            // Shared code in chunks/
  chunkNames: 'chunks/[hash]',
  metafile: true,             // Output metafile.json for bundle analysis
});
```

Analyze bundle with: `npx esbuild-analyzer metafile.json`

### What to Bundle

Bundle everything including AWS SDK v3 — the Lambda Node.js 22 runtime only includes AWS SDK v2, which this stack does not use. Do NOT rely on `node_modules` being present in the runtime environment.

## ESM vs CJS for Lambda

**Use ESM** with Node.js 22. Reasons:
- Better tree shaking (static `import` analysis)
- No `require()` wrapper overhead
- Top-level `await` support

**CJS downsides for Lambda:**
- `require()` is synchronous but blocks module evaluation
- Bundlers struggle to tree-shake `require()` in third-party libs
- Larger bundles from poor dead-code elimination

**ESM caveat:** Some older packages only ship CJS. esbuild handles the interop automatically. Check with:
```bash
node --input-type=module -e "import('your-package')" 2>&1
```

## SDK v3 Modular Imports — Examples

**WRONG (SDK v2 — never use):**
```typescript
import AWS from 'aws-sdk';            // Imports entire 8MB SDK
const dynamo = new AWS.DynamoDB();
```

**WRONG (SDK v3 but full client import):**
```typescript
import { DynamoDB } from '@aws-sdk/client-dynamodb'; // OK but check sub-paths
```

**RIGHT (SDK v3 modular — one client per function need):**
```typescript
// Only import the client you need
import { DynamoDBClient, GetItemCommand } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, GetCommand } from '@aws-sdk/lib-dynamodb';
import { NodeHttpHandler } from '@smithy/node-http-handler';
import { Agent } from 'node:https';

// Initialize OUTSIDE handler — reused across warm invocations
const ddbClient = new DynamoDBClient({
  requestHandler: new NodeHttpHandler({
    requestTimeout: 3000,
    httpsAgent: new Agent({ keepAlive: true, maxSockets: 25 }),
  }),
});
const docClient = DynamoDBDocumentClient.from(ddbClient);
```

Per-function client imports reduce bundle size by 60-80% vs importing a shared client module.

## Lazy Imports

For code paths that are rarely executed (e.g., admin-only operations), use dynamic imports:

```typescript
// Top of file — always loaded (keep minimal)
import { DynamoDBClient } from '@aws-sdk/client-dynamodb';

const handler = async (event: APIGatewayProxyEventV2) => {
  if (event.headers['x-admin-token']) {
    // Loaded only when admin path is hit — not on every cold start
    const { generateReport } = await import('../lib/reporting.js');
    return generateReport(event);
  }
  // Normal fast path
};
```

## Connection Reuse (HTTP Keep-Alive)

Lambda creates a new Node.js process per cold start. Without keep-alive, each SDK call opens a new HTTPS connection.

```typescript
// Set globally before any SDK client instantiation
import { NodeHttpHandler } from '@smithy/node-http-handler';
import { Agent } from 'node:https';

const keepAliveAgent = new Agent({ keepAlive: true, maxSockets: 50 });

// Apply to DynamoDB
const ddbClient = new DynamoDBClient({
  requestHandler: new NodeHttpHandler({ httpsAgent: keepAliveAgent }),
});

// Apply to SQS
const sqsClient = new SQSClient({
  requestHandler: new NodeHttpHandler({ httpsAgent: keepAliveAgent }),
});
```

Alternative — set environment variable in Lambda config (applies to all SDK calls):

> **Note:** `AWS_NODEJS_CONNECTION_REUSE_ENABLED=1` was required for AWS SDK v2.
> SDK v3 enables HTTP keep-alive by default — no environment variable needed.

## Initialization Outside Handler

```typescript
// CORRECT — runs once per cold start, reused on warm invocations
const ddbClient = new DynamoDBClient({});
const docClient = DynamoDBDocumentClient.from(ddbClient);
let cachedConfig: Config | null = null;

export const handler = async (event: APIGatewayProxyEventV2) => {
  // Config fetched once, reused on warm invocations
  const config = cachedConfig ?? (cachedConfig = await fetchConfig());
  // Handler logic
};

// WRONG — re-initialized on every invocation
export const handler = async (event: APIGatewayProxyEventV2) => {
  const ddbClient = new DynamoDBClient({});  // New client every time
};
```

## Provisioned Concurrency — When to Use

Use provisioned concurrency when:
- p99 latency SLA is strict (e.g., payment flows, auth endpoints)
- Traffic spikes cause > 5% of requests to be cold starts
- Function has >500ms init time due to heavy dependencies

```hcl
resource "aws_lambda_provisioned_concurrency_config" "auth" {
  function_name                  = aws_lambda_function.auth.function_name
  qualifier                      = aws_lambda_alias.auth_live.name
  provisioned_concurrent_executions = 5
}
```

Cost: ~$0.015/hour per provisioned concurrency unit. Use Application Auto Scaling to scale based on schedule or utilization.

**Do NOT use provisioned concurrency as a first resort.** Optimize bundle size and init code first.

## Benchmarking Cold Starts

Use AWS X-Ray to measure init duration:

```bash
aws xray get-service-graph --start-time <epoch> --end-time <epoch>
```

Or check CloudWatch Logs Insights:
```
filter @type = "REPORT"
| stats avg(@initDuration), max(@initDuration), count() by bin(5m)
```

Target metrics:
| Metric | Target |
|--------|--------|
| Bundle size | <1MB (zip) |
| Init duration | <100ms |
| p50 cold start | <200ms total |
| p99 cold start | <500ms total |
