---
name: sqs-async-jobs
description: |
  SQS async job processing with Lambda triggers, DLQ configuration, and idempotency patterns.
  Use when implementing async job queues, retry strategies, or message-driven Lambda workflows.
  Triggers on: "SQS", "queue", "async job", "DLQ", "dead letter", "FIFO", "idempotency", "batch".
---

# SQS Async Job Processing

## Version Matrix

| Package | Version | Purpose |
|---------|---------|---------|
| `@aws-sdk/client-sqs` | 3.x | SQS client (v3 modular) |
| `@middy/core` | 5.x | Lambda middleware engine |
| `@middy/sqs-json-body-parser` | 5.x | Auto-parse SQS message bodies |
| `@aws-lambda-powertools/idempotency` | 2.x | Idempotency with DynamoDB backend |
| `zod` | 3.x | Runtime schema validation |
| `uuid` | 9.x | Generate idempotency keys |

---

## Queue Types: Standard vs FIFO

### Standard Queue
- Delivery: at-least-once (duplicates possible)
- Ordering: best-effort (not guaranteed)
- Throughput: nearly unlimited
- Use for: background jobs, email sending, image processing, analytics events

### FIFO Queue
- Delivery: exactly-once within a deduplication window (5 min)
- Ordering: strict FIFO within a message group
- Throughput: 300 msg/s without batching, 3000 msg/s with batching (batch size 10)
- Use for: user action sequences, financial transactions, state machine transitions
- Naming: must end with `.fifo`
- Cost: ~$0.10/million vs ~$0.04/million for Standard

**Rule of thumb**: Default to Standard. Use FIFO only when your business logic explicitly requires ordering or deduplication guarantees.

---

## Lambda Event Source Mapping

```typescript
// CDK example — same attributes apply in Terraform
new EventSourceMapping(this, 'SqsMapping', {
  target: myLambda,
  eventSourceArn: queue.queueArn,
  batchSize: 10,               // default 10, max 10 for SQS triggers
  maxConcurrency: 5,           // 2–1000; limits parallel Lambda instances
  reportBatchItemFailures: true, // maps to FunctionResponseTypes
});
```

Key attributes:
- `batchSize`: 1–10 for both Standard and FIFO SQS triggers. Start at 10.
- `maxConcurrency`: prevents thundering-herd on downstream databases. Set to (DB connection pool size / 2).
- `FunctionResponseTypes: ["ReportBatchItemFailures"]`: **always enable**. Without it, a single failure retries the entire batch.
- `visibilityTimeout`: must be >= 6x Lambda timeout. If Lambda runs 30 s, set visibility to 3 min.

---

## DLQ Configuration

Every queue must have a DLQ. Never share DLQs between queues.

```
Main Queue ──(maxReceiveCount=3)──► DLQ
```

- `maxReceiveCount`: 3 is a safe default. Use 1 for poison-pill-sensitive pipelines.
- DLQ retention: 14 days (maximum). Give your team time to investigate.
- DLQ alarm: CloudWatch on `ApproximateNumberOfMessagesVisible > 0`. See `DLQ-PATTERNS.md`.

```hcl
# Terraform — see SERVERLESS-IAC.md for full module
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.queue_name}-dlq"
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_sqs_queue" "main" {
  name                       = var.queue_name
  visibility_timeout_seconds = 180 # 6x a 30s Lambda timeout
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}
```

---

## Retry Strategies

SQS retries are implicit — a message becomes visible again after `visibilityTimeout` if not deleted.

**Visibility timeout as backoff**: Extend the visibility timeout inside the handler on transient errors. This implements a manual exponential backoff without needing a delay queue.

```typescript
import { SQSClient, ChangeMessageVisibilityCommand } from '@aws-sdk/client-sqs';

const sqsClient = new SQSClient({});

async function extendVisibility(
  receiptHandle: string,
  queueUrl: string,
  attempt: number
): Promise<void> {
  const backoffSeconds = Math.min(2 ** attempt * 30, 900); // max 15 min
  await sqsClient.send(new ChangeMessageVisibilityCommand({
    QueueUrl: queueUrl,
    ReceiptHandle: receiptHandle,
    VisibilityTimeout: backoffSeconds,
  }));
}
```

---

## Idempotency

SQS Standard delivers at-least-once. Your handler **must** be idempotent.

### Option A: AWS Lambda Powertools (recommended)

```typescript
import { makeIdempotent } from '@aws-lambda-powertools/idempotency';
import { DynamoDBPersistenceLayer } from '@aws-lambda-powertools/idempotency/dynamodb';

const persistenceStore = new DynamoDBPersistenceLayer({
  tableName: process.env.IDEMPOTENCY_TABLE!,
});

const processJob = makeIdempotent(
  async (jobId: string, payload: JobPayload) => {
    // business logic here — will only run once per jobId
  },
  { persistenceStore, dataIndexArgument: 0 }
);
```

### Option B: Conditional DynamoDB PutItem (lightweight)

```typescript
import { DynamoDBClient, PutItemCommand } from '@aws-sdk/client-dynamodb';
import { ConditionalCheckFailedException } from '@aws-sdk/client-dynamodb';

const dynamo = new DynamoDBClient({});

async function markProcessed(messageId: string): Promise<boolean> {
  try {
    await dynamo.send(new PutItemCommand({
      TableName: process.env.PROCESSED_TABLE!,
      Item: {
        messageId: { S: messageId },
        processedAt: { S: new Date().toISOString() },
        ttl: { N: String(Math.floor(Date.now() / 1000) + 86400 * 7) },
      },
      ConditionExpression: 'attribute_not_exists(messageId)',
    }));
    return true; // first time — process it
  } catch (e) {
    if (e instanceof ConditionalCheckFailedException) return false; // duplicate
    throw e;
  }
}
```

---

## Message Serialization

Validate every message body at the Lambda boundary. For permanently invalid messages (malformed JSON, schema mismatch), **log the error and skip** — do NOT add them to `batchItemFailures`. This acknowledges the message (removes it from the queue) and avoids wasting retries on messages that will never succeed. Only add to `batchItemFailures` for transient errors (network timeouts, downstream unavailable) that may succeed on retry.

```typescript
import { z } from 'zod';

const JobSchema = z.object({
  jobId: z.string().uuid(),
  type: z.enum(['SEND_EMAIL', 'RESIZE_IMAGE', 'GENERATE_REPORT']),
  payload: z.record(z.unknown()),
  enqueuedAt: z.string().datetime(),
});

type Job = z.infer<typeof JobSchema>;

function parseMessageBody(body: string): Job | null {
  try {
    const parsed = JSON.parse(body);
    return JobSchema.parse(parsed);
  } catch (e) {
    console.error({ event: 'invalid_message_schema', body, error: String(e) });
    return null; // caller should log and skip — do NOT add to batchItemFailures (avoids wasting retries)
  }
}
```

---

## Complete SQS Lambda Handler

```typescript
import type { SQSHandler, SQSBatchResponse } from 'aws-lambda';
import middy from '@middy/core';
import { z } from 'zod';

const JobSchema = z.object({
  jobId: z.string().uuid(),
  type: z.enum(['SEND_EMAIL', 'RESIZE_IMAGE']),
  payload: z.record(z.unknown()),
});

type Job = z.infer<typeof JobSchema>;

async function processJob(job: Job): Promise<void> {
  // business logic — must be idempotent
  switch (job.type) {
    case 'SEND_EMAIL':
      await sendEmail(job.payload);
      break;
    case 'RESIZE_IMAGE':
      await resizeImage(job.payload);
      break;
  }
}

const baseHandler: SQSHandler = async (event): Promise<SQSBatchResponse> => {
  const failures: SQSBatchResponse['batchItemFailures'] = [];

  await Promise.allSettled(
    event.Records.map(async (record) => {
      // Parse body manually: SQS delivers record.body as a raw string.
      // We use JSON.parse + Zod instead of @middy/sqs-json-body-parser because
      // that middleware mutates record.body in place, conflicting with the
      // typed SQSRecord interface and making the raw string unavailable for
      // error logging.
      let parsedBody: unknown;
      try {
        parsedBody = JSON.parse(record.body);
      } catch {
        // Malformed JSON — permanently invalid, log and skip (do not retry)
        console.error({
          event: 'json_parse_failed',
          messageId: record.messageId,
          body: record.body,
        });
        return; // acknowledged — message removed from queue
      }

      const parseResult = JobSchema.safeParse(parsedBody);

      if (!parseResult.success) {
        // Schema error — log and skip. Do NOT add to failures (avoids wasting retries).
        // Message is acknowledged and removed from queue.
        console.error({
          event: 'schema_validation_failed',
          messageId: record.messageId,
          error: parseResult.error.issues,
        });
        return; // skip — message acknowledged, no retry
      }

      try {
        await processJob(parseResult.data);
        console.info({ event: 'job_processed', jobId: parseResult.data.jobId });
      } catch (err) {
        console.error({
          event: 'job_failed',
          messageId: record.messageId,
          error: String(err),
        });
        failures.push({ itemIdentifier: record.messageId });
      }
    })
  );

  return { batchItemFailures: failures };
};

export const handler = middy(baseHandler);
```

---

## FIFO Deduplication

```typescript
import { SQSClient, SendMessageCommand } from '@aws-sdk/client-sqs';
import { createHash } from 'node:crypto';

const client = new SQSClient({});

async function enqueueUserAction(
  userId: string,
  action: string,
  payload: unknown
): Promise<void> {
  // MessageGroupId determines ordering — all messages for same group are ordered
  // MessageDeduplicationId prevents duplicates within 5-minute window
  await client.send(new SendMessageCommand({
    QueueUrl: process.env.FIFO_QUEUE_URL!,
    MessageBody: JSON.stringify({ userId, action, payload }),
    MessageGroupId: userId,                         // ordered per user
    // Deterministic, bounded dedup ID (max 128 chars). Hash the canonicalized payload.
    MessageDeduplicationId: createHash('sha256')
      .update(`${userId}:${action}:${JSON.stringify(payload)}`)
      .digest('hex')
      .slice(0, 128),
  }));
}
```

---

## When NOT to Use SQS

| Requirement | Use Instead |
|-------------|-------------|
| Real-time response needed (<100 ms) | Direct Lambda invoke or API call |
| Strict ordering without FIFO cost | Kinesis Data Streams |
| Fan-out to multiple consumers | SNS + SQS subscription per consumer |
| High-throughput streaming (>1M msg/s) | Kinesis or MSK (Managed Kafka) |
| Scheduled jobs | EventBridge Scheduler |
| Long-running workflows with branching | Step Functions |

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| Message stuck "in flight" | `visibilityTimeout` shorter than Lambda execution | Set `visibilityTimeout >= 6x Lambda timeout` |
| DLQ overflowing | Lambda errors not caught, entire batch retried | Enable `ReportBatchItemFailures`, return failures array |
| Lambda timeout < visibility timeout | Message processed twice | Always set visibility timeout first, then process |
| `KMSDisabledException` | SQS queue uses KMS, Lambda lacks `kms:Decrypt` | Add `kms:Decrypt` and `kms:GenerateDataKey` to Lambda IAM role |
| Duplicate processing on FIFO | Using `ContentBasedDeduplication` with mutable bodies | Use explicit `MessageDeduplicationId` instead |
| Batch size too large for downstream | DB connection exhaustion | Reduce `batchSize` or set `maxConcurrency` |
