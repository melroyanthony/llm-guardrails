---
name: testing-serverless
description: |
  Testing patterns for serverless TypeScript: Lambda unit tests, DynamoDB Local, and LocalStack integration.
  Use when writing tests for Lambda handlers, DynamoDB operations, or serverless integrations.
  Triggers on: "test Lambda", "DynamoDB Local", "LocalStack", "serverless test", "Vitest", "Drizzle test".
---

# Testing Serverless TypeScript

## Version Matrix

| Package | Version | Purpose |
|---------|---------|---------|
| `vitest` | 3.x | Test runner (Jest-compatible API) |
| `@testcontainers/dynamodb` | 10.x | DynamoDB Local in Docker |
| `@testcontainers/postgresql` | 10.x | PostgreSQL in Docker for Drizzle tests |
| `aws-sdk-client-mock` | 4.x | Mock AWS SDK v3 clients |
| `aws-sdk-client-mock-vitest` | 4.x | Vitest matchers for SDK mock assertions |
| `localstack/localstack` (Docker image) | `3` (tag) | Full AWS emulation for SQS integration |
| `dotenv-cli` | 7.x | Load `.env.test` per test command |

---

## Guiding Principles

- Unit tests mock AWS SDK calls — they run in milliseconds and have no external deps.
- Integration tests use real Docker containers (DynamoDB Local, PostgreSQL) — they test actual data persistence.
- End-to-end tests use LocalStack — they test the full message flow including Lambda triggers.
- Never use production credentials in tests. Always use `.env.test` with fake/local values.
- Do not test auto-generated code (CDK synth output, Drizzle-generated migrations). Test your business logic.

---

## Lambda Unit Testing

Use `aws-sdk-client-mock` to intercept SDK calls at the client level. Your handler code does not change — the mock patches the client instance.

```typescript
// tests/unit/process-job.handler.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { mockClient } from 'aws-sdk-client-mock';
import 'aws-sdk-client-mock-vitest';
import { DynamoDBClient, PutItemCommand } from '@aws-sdk/client-dynamodb';
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';
import type { SQSEvent } from 'aws-lambda';
import { handler } from '../../src/handlers/process-job';

const ddbMock = mockClient(DynamoDBClient);
const sqsMock = mockClient(SQSClient);

const buildSqsEvent = (body: unknown): SQSEvent => ({
  Records: [
    {
      messageId: 'test-message-id',
      receiptHandle: 'test-receipt-handle',
      body: JSON.stringify(body),
      attributes: {
        ApproximateReceiveCount: '1',
        SentTimestamp: '1',
        SenderId: 'test',
        ApproximateFirstReceiveTimestamp: '1',
      },
      messageAttributes: {},
      md5OfBody: '',
      eventSource: 'aws:sqs',
      eventSourceARN: 'arn:aws:sqs:us-east-1:123456789012:test-queue',
      awsRegion: 'us-east-1',
    },
  ],
});

describe('process-job handler', () => {
  beforeEach(() => {
    ddbMock.reset();
    sqsMock.reset();
    process.env.IDEMPOTENCY_TABLE = 'test-idempotency';
    process.env.OUTPUT_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/123/output';
  });

  it('should process a valid job and write to DynamoDB', async () => {
    ddbMock.on(PutItemCommand).resolves({});
    sqsMock.on(SendMessageCommand).resolves({ MessageId: 'out-msg-id' });

    const event = buildSqsEvent({
      jobId: '550e8400-e29b-41d4-a716-446655440000',
      type: 'SEND_EMAIL',
      payload: { to: 'user@example.com', subject: 'Hello' },
    });

    const result = await handler(event, {} as never, () => {});

    expect(result).toEqual({ batchItemFailures: [] });
    expect(ddbMock).toHaveReceivedCommandTimes(PutItemCommand, 1);
  });

  it('should skip schema-invalid messages (log and acknowledge, no retry)', async () => {
    const event = buildSqsEvent({ notAValidJob: true });

    const result = await handler(event, {} as never, () => {});

    // Schema-invalid messages are acknowledged (not added to batchItemFailures)
    // per sqs-async-jobs skill guidance — avoids wasting retries
    expect(result).toEqual({ batchItemFailures: [] });
    expect(ddbMock).not.toHaveReceivedAnyCommand();
  });

  it('should return batchItemFailures when DynamoDB throws', async () => {
    ddbMock.on(PutItemCommand).rejects(new Error('ProvisionedThroughputExceeded'));

    const event = buildSqsEvent({
      jobId: '550e8400-e29b-41d4-a716-446655440001',
      type: 'SEND_EMAIL',
      payload: {},
    });

    const result = await handler(event, {} as never, () => {});

    expect(result?.batchItemFailures).toHaveLength(1);
  });
});
```

---

## Middleware Testing

Test middy middleware in isolation before composing them.

```typescript
// tests/unit/auth.middleware.test.ts
import { describe, it, expect } from 'vitest';
import middy from '@middy/core';
import type { APIGatewayProxyEventV2, APIGatewayProxyResultV2 } from 'aws-lambda';
import { authMiddleware } from '../../src/middleware/auth';

const baseHandler = async (): Promise<APIGatewayProxyResultV2> => ({
  statusCode: 200,
  body: JSON.stringify({ ok: true }),
});

const wrappedHandler = middy(baseHandler).use(authMiddleware());

describe('authMiddleware', () => {
  it('should reject requests without Authorization header', async () => {
    const event = { headers: {} } as unknown as APIGatewayProxyEventV2;
    const result = await wrappedHandler(event, {} as never);
    expect(result.statusCode).toBe(401);
  });

  it('should pass through requests with valid Bearer token', async () => {
    const event = {
      headers: { authorization: 'Bearer valid-token' },
    } as unknown as APIGatewayProxyEventV2;
    const result = await wrappedHandler(event, {} as never);
    expect(result.statusCode).toBe(200);
  });
});
```

---

## DynamoDB Integration Tests (DynamoDB Local)

Use testcontainers to spin up DynamoDB Local in Docker. Tables are created in `beforeAll` and torn down when the container stops.

```typescript
// tests/integration/jobs.repository.test.ts
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { DynamoDBContainer, type StartedDynamoDBContainer } from '@testcontainers/dynamodb';
import {
  DynamoDBClient,
  CreateTableCommand,
  BillingMode,
} from '@aws-sdk/client-dynamodb';
import { JobsRepository } from '../../src/repositories/jobs';

let container: StartedDynamoDBContainer;
let client: DynamoDBClient;
let repo: JobsRepository;

beforeAll(async () => {
  container = await new DynamoDBContainer().start();

  const endpoint = container.getConnectionUri();
  client = new DynamoDBClient({
    endpoint,
    region: 'us-east-1',
    credentials: { accessKeyId: 'fake', secretAccessKey: 'fake' },
  });

  await client.send(new CreateTableCommand({
    TableName: 'jobs',
    BillingMode: BillingMode.PAY_PER_REQUEST,
    AttributeDefinitions: [
      { AttributeName: 'pk', AttributeType: 'S' },
      { AttributeName: 'sk', AttributeType: 'S' },
    ],
    KeySchema: [
      { AttributeName: 'pk', KeyType: 'HASH' },
      { AttributeName: 'sk', KeyType: 'RANGE' },
    ],
  }));

  repo = new JobsRepository(client, 'jobs');
}, 30_000);

afterAll(async () => {
  await container?.stop();
});

describe('JobsRepository', () => {
  it('should save and retrieve a job', async () => {
    const job = { jobId: 'test-123', status: 'PENDING', createdAt: new Date().toISOString() };

    await repo.save(job);
    const retrieved = await repo.findById('test-123');

    expect(retrieved).toMatchObject(job);
  });

  it('should return null for non-existent job', async () => {
    const result = await repo.findById('does-not-exist');
    expect(result).toBeNull();
  });
});
```

---

## Aurora / Drizzle Integration Tests

Wrap each test in a transaction and roll back — this leaves the DB clean without truncating tables.

```typescript
// tests/integration/users.service.test.ts
import { describe, it, expect, beforeAll, afterAll, beforeEach, afterEach } from 'vitest';
import { PostgreSqlContainer, type StartedPostgreSqlContainer } from '@testcontainers/postgresql';
import { drizzle, type PostgresJsDatabase } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { migrate } from 'drizzle-orm/postgres-js/migrator';
import * as schema from '../../src/db/schema';
import { UsersService } from '../../src/services/users';

let container: StartedPostgreSqlContainer;
let db: PostgresJsDatabase<typeof schema>;
let sql: ReturnType<typeof postgres>;

beforeAll(async () => {
  container = await new PostgreSqlContainer('postgres:16-alpine').start();

  sql = postgres(container.getConnectionUri());
  db = drizzle(sql, { schema });

  // Run all migrations against the test DB
  await migrate(db, { migrationsFolder: './migrations' });
}, 60_000);

afterAll(async () => {
  await sql?.end();
  await container?.stop();
});

describe('UsersService', () => {
  let service: UsersService;

  beforeEach(() => {
    service = new UsersService(db);
  });

  it('should create and return a user', async () => {
    const user = await service.create({ email: 'test@example.com', name: 'Test User' });

    expect(user.id).toBeDefined();
    expect(user.email).toBe('test@example.com');
  });

  it('should throw on duplicate email', async () => {
    await service.create({ email: 'dupe@example.com', name: 'First' });

    await expect(
      service.create({ email: 'dupe@example.com', name: 'Second' })
    ).rejects.toThrow(/unique/i);
  });
});
```

---

## LocalStack: SQS + Lambda Integration Tests

Use LocalStack 3.x for full-stack integration tests. Start with docker-compose, not programmatically, to keep test setup simple.

```yaml
# docker-compose.test.yml
services:
  localstack:
    image: localstack/localstack:3
    ports:
      - "4566:4566"
    environment:
      SERVICES: sqs,lambda,iam,s3
      DEBUG: 0
      LAMBDA_EXECUTOR: local
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

```typescript
// tests/integration/sqs-flow.test.ts
import { describe, it, expect, beforeAll } from 'vitest';
import {
  SQSClient,
  CreateQueueCommand,
  SendMessageCommand,
  ReceiveMessageCommand,
} from '@aws-sdk/client-sqs';
import { handler } from '../../src/handlers/process-job';
import type { SQSEvent } from 'aws-lambda';

const LOCALSTACK_URL = 'http://localhost:4566';

const sqsClient = new SQSClient({
  endpoint: LOCALSTACK_URL,
  region: 'us-east-1',
  credentials: { accessKeyId: 'test', secretAccessKey: 'test' },
});

let queueUrl: string;

beforeAll(async () => {
  const { QueueUrl } = await sqsClient.send(new CreateQueueCommand({
    QueueName: 'test-jobs-queue',
  }));
  queueUrl = QueueUrl!;
});

describe('SQS job flow', () => {
  it('should process a message sent to SQS', async () => {
    await sqsClient.send(new SendMessageCommand({
      QueueUrl: queueUrl,
      MessageBody: JSON.stringify({
        jobId: '550e8400-e29b-41d4-a716-446655440099',
        type: 'SEND_EMAIL',
        payload: { to: 'integration@example.com' },
      }),
    }));

    // Receive from queue and manually invoke handler (simulates event source mapping)
    const { Messages = [] } = await sqsClient.send(new ReceiveMessageCommand({
      QueueUrl: queueUrl,
      MaxNumberOfMessages: 1,
    }));

    expect(Messages).toHaveLength(1);

    const event: SQSEvent = {
      Records: Messages.map((m) => ({
        messageId: m.MessageId!,
        receiptHandle: m.ReceiptHandle!,
        body: m.Body!,
        attributes: {} as never,
        messageAttributes: {},
        md5OfBody: '',
        eventSource: 'aws:sqs',
        eventSourceARN: 'arn:aws:sqs:us-east-1:000000000000:test-jobs-queue',
        awsRegion: 'us-east-1',
      })),
    };

    const result = await handler(event, {} as never, () => {});
    expect(result).toEqual({ batchItemFailures: [] });
  });
});
```

---

## Vitest Configuration (Nx Monorepo)

```typescript
// vitest.config.ts (per app)
import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.ts', 'tests/**/*.test.ts'],
    exclude: ['tests/integration/**'],
    setupFiles: ['../../libs/test-utils/src/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      thresholds: { lines: 80, functions: 80, branches: 70 },
    },
  },
  resolve: {
    alias: { '@': resolve(__dirname, './src') },
  },
});
```

```typescript
// vitest.integration.config.ts
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/integration/**/*.test.ts'],
    testTimeout: 60_000,   // containers can be slow to start
    hookTimeout: 90_000,
    pool: 'forks',         // isolation between integration suites
    poolOptions: { forks: { singleFork: true } },
  },
});
```

```json
// package.json scripts
{
  "scripts": {
    "test": "dotenv -e .env.test -- vitest run",
    "test:integration": "dotenv -e .env.test -- vitest run --config vitest.integration.config.ts",
    "test:watch": "dotenv -e .env.test -- vitest",
    "test:coverage": "dotenv -e .env.test -- vitest run --coverage"
  }
}
```

---

## Environment Setup (.env.test)

Commit `.env.test.example` to source control. Users copy it to `.env.test` locally.
Add `.env.test` to your project's `.gitignore` (alongside existing `.env` rules):
```
# In .gitignore
.env.test
!.env.test.example
```

```bash
# .env.test.example — committed to source control, copy to .env.test locally
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=fake
AWS_SECRET_ACCESS_KEY=fake
DYNAMODB_ENDPOINT=http://localhost:8000
LOCALSTACK_ENDPOINT=http://localhost:4566
DATABASE_URL=postgresql://test:test@localhost:5432/testdb
IDEMPOTENCY_TABLE=idempotency-test
LOG_LEVEL=silent
```

---

## When NOT to Use Each Tool

| Do NOT | Use Instead |
|--------|-------------|
| LocalStack for unit tests | `aws-sdk-client-mock` (100x faster) |
| Real DynamoDB for integration tests | `@testcontainers/dynamodb` (free, isolated) |
| Mocking DynamoDB behavior | DynamoDB Local (test real query patterns) |
| Testing CDK synth output | Trust CDK's own tests; test your constructs' props |
| `jest.mock('module')` in Vitest | `vi.mock('module')` — different global namespace |
