# DLQ Patterns and Operations

Dead Letter Queues capture messages that exhaust retries. Without active monitoring and a redrive strategy, a DLQ becomes a silent graveyard for lost data.

---

## Alert Thresholds

| Messages Visible | Severity | Action |
|-----------------|----------|--------|
| > 0 | Warning | Investigate within 1 business hour |
| > 100 | Critical | Page on-call, begin incident response |
| > 1000 | SEV-1 | Wake on-call, customer impact likely |

---

## CloudWatch Alarm

Create one alarm per DLQ. Never aggregate multiple DLQs into a single alarm — you lose signal on which queue is failing.

```hcl
resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  alarm_name          = "${var.queue_name}-dlq-not-empty"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300 # check every 5 minutes
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
  alarm_description = "DLQ ${var.queue_name}-dlq has messages. Investigate immediately."
}

resource "aws_sns_topic" "alerts" {
  name = "${var.project}-alerts"
}

resource "aws_sns_topic_subscription" "pagerduty" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "https"
  endpoint  = var.pagerduty_webhook_url
}
```

---

## Redrive to Source Queue

AWS provides a managed redrive API. Use it for bulk replay after a bug fix.

### Via AWS Console
1. Open SQS console, select the DLQ.
2. Click "Start DLQ redrive".
3. Choose "Redrive to source queue".
4. Set a redrive rate (messages/second) — start low (10/s) to avoid overwhelming downstream.

### Via AWS CLI
```bash
# Start redrive
TASK_HANDLE=$(aws sqs start-message-move-task \
  --source-arn arn:aws:sqs:us-east-1:123456789:my-queue-dlq \
  --destination-arn arn:aws:sqs:us-east-1:123456789:my-queue \
  --max-number-of-messages-per-second 50 \
  --query 'TaskHandle' --output text)

# Monitor progress
aws sqs get-message-move-task --task-handle "$TASK_HANDLE"

# Cancel if needed
aws sqs cancel-message-move-task --task-handle "$TASK_HANDLE"
```

---

## Poison Pill Detection and Handling

A poison pill is a message that always fails regardless of retry attempts — bad data, unsupported format, a permanent downstream error. Redriving it loops forever.

### Detection heuristic
A message is a poison pill if it has failed `maxReceiveCount` times AND the same error type appears on every attempt.

### Lambda handler pattern

```typescript
import type { SQSHandler, SQSBatchResponse } from 'aws-lambda';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

const s3 = new S3Client({});

const PERMANENT_ERRORS = [
  'ValidationError',
  'SchemaError',
  'UnsupportedMediaType',
];

function isPermanentError(error: unknown): boolean {
  if (error instanceof Error) {
    return PERMANENT_ERRORS.some((name) => error.constructor.name === name);
  }
  return false;
}

export const handler: SQSHandler = async (event): Promise<SQSBatchResponse> => {
  const failures: SQSBatchResponse['batchItemFailures'] = [];

  for (const record of event.Records) {
    try {
      await processRecord(record);
    } catch (err) {
      if (isPermanentError(err)) {
        // Archive poison pill to S3 for audit trail, do NOT return as failure
        await archivePoisonPill(record, err);
        console.error({
          event: 'poison_pill_archived',
          messageId: record.messageId,
          error: String(err),
        });
        // By not adding to failures, the message is acknowledged and removed from the source queue
      } else {
        failures.push({ itemIdentifier: record.messageId });
      }
    }
  }

  return { batchItemFailures: failures };
};

async function archivePoisonPill(record: unknown, error: unknown): Promise<void> {
  const key = `poison-pills/${new Date().toISOString()}/${
    (record as { messageId: string }).messageId
  }.json`;

  await s3.send(new PutObjectCommand({
    Bucket: process.env.ARCHIVE_BUCKET!,
    Key: key,
    Body: JSON.stringify({ record, error: String(error) }),
    ContentType: 'application/json',
  }));
}
```

---

## Scheduled DLQ Reprocessing Lambda

For non-critical queues where manual redrive is acceptable, a scheduled Lambda can automate the retry loop with exponential backoff.

```typescript
import {
  SQSClient,
  ReceiveMessageCommand,
  DeleteMessageCommand,
  SendMessageCommand,
} from '@aws-sdk/client-sqs';
import type { ScheduledHandler } from 'aws-lambda';

const sqs = new SQSClient({});
const MAX_REPROCESS_ATTEMPTS = 3;
const BATCH_SIZE = 10;

export const handler: ScheduledHandler = async () => {
  const { Messages = [] } = await sqs.send(new ReceiveMessageCommand({
    QueueUrl: process.env.DLQ_URL!,
    MaxNumberOfMessages: BATCH_SIZE,
    AttributeNames: ['ApproximateReceiveCount'],
    MessageAttributeNames: ['All'],
  }));

  for (const message of Messages) {
    const receiveCount = parseInt(
      message.Attributes?.ApproximateReceiveCount ?? '1',
      10
    );

    if (receiveCount > MAX_REPROCESS_ATTEMPTS) {
      // Permanently failed — archive and delete
      console.error({
        event: 'message_permanently_failed',
        messageId: message.MessageId,
        body: message.Body,
      });
      // TODO: write to S3 archive before deleting
    } else {
      // Re-enqueue to main queue with backoff delay
      const delaySeconds = Math.min(2 ** receiveCount * 10, 900);
      await sqs.send(new SendMessageCommand({
        QueueUrl: process.env.SOURCE_QUEUE_URL!,
        MessageBody: message.Body!,
        DelaySeconds: delaySeconds,
        MessageAttributes: message.MessageAttributes,
      }));
    }

    // Delete from DLQ regardless — either re-enqueued or archived
    await sqs.send(new DeleteMessageCommand({
      QueueUrl: process.env.DLQ_URL!,
      ReceiptHandle: message.ReceiptHandle!,
    }));
  }
};
```

EventBridge Scheduler rule (Terraform):

```hcl
resource "aws_scheduler_schedule" "dlq_reprocessor" {
  name = "${var.queue_name}-dlq-reprocessor"

  flexible_time_window { mode = "OFF" }

  schedule_expression = "rate(5 minutes)"

  target {
    arn      = aws_lambda_function.dlq_reprocessor.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}
```

---

## Full Terraform: SQS + DLQ + Alarm

```hcl
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.queue_name}-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = var.tags
}

resource "aws_sqs_queue" "main" {
  name                       = var.queue_name
  visibility_timeout_seconds = var.visibility_timeout_seconds

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "dlq_not_empty" {
  alarm_name          = "${var.queue_name}-dlq-not-empty"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }

  alarm_actions = [var.alert_sns_arn]
}
```
