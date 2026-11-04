# Middy Middleware Patterns

Middy wraps Lambda handlers with a composable middleware chain. Each middleware runs `before` (request) and `after` (response) hooks, plus an `onError` hook.

## Middleware Chain Architecture

```
Request →  [auth] → [validate] → [correlationId] → handler → [metrics] → [tracer] → [logger] → Response
                                                        ↓ (on error)
                                                   [errorHandler]
```

Order matters: auth before validate, errorHandler last (outermost).

```typescript
export const handler = middy(lambdaHandler)
  // Powertools — outermost so they capture everything
  .use(injectLambdaContext(logger, { clearState: true }))
  .use(captureLambdaHandler(tracer))
  .use(logMetrics(metrics, { captureColdStartMetric: true }))
  // App middleware — inner
  .use(correlationIdMiddleware(logger))
  .use(corsMiddleware())
  .use(authMiddleware({ required: true }))
  .use(validateBody(createItemSchema))
  .use(errorHandlerMiddleware());   // Last — catches errors from all above
```

## Auth Middleware (JWT Validation)

```typescript
// middleware/auth.ts
import middy from '@middy/core';
import { APIGatewayProxyEventV2 } from 'aws-lambda';
import { createRemoteJWKSet, jwtVerify } from 'jose';
import type { MiddlewareObj } from '@middy/core';

const JWKS = createRemoteJWKSet(
  new URL(process.env.JWKS_URI!)
);

interface AuthOptions {
  required?: boolean;
}

export function authMiddleware(opts: AuthOptions = {}): MiddlewareObj {
  return {
    before: async (request) => {
      const event = request.event as APIGatewayProxyEventV2;
      const token = event.headers?.authorization?.replace(/^Bearer\s+/i, '');

      if (!token) {
        if (opts.required !== false) {
          throw { statusCode: 401, message: 'Missing authorization token' };
        }
        return;
      }

      try {
        const { payload } = await jwtVerify(token, JWKS, {
          issuer: process.env.JWT_ISSUER,
          audience: process.env.JWT_AUDIENCE,
        });
        // Attach to event for handler use
        (request.event as APIGatewayProxyEventV2 & { user: unknown }).user =
          payload;
      } catch {
        throw { statusCode: 401, message: 'Invalid or expired token' };
      }
    },
  };
}
```

## API Key Auth Middleware (alternative)

```typescript
import { timingSafeEqual } from 'node:crypto';

function safeCompare(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  return timingSafeEqual(Buffer.from(a), Buffer.from(b));
}

export function apiKeyMiddleware(): MiddlewareObj {
  return {
    before: async (request) => {
      const event = request.event as APIGatewayProxyEventV2;
      const apiKey = event.headers?.['x-api-key'];
      const validKey = process.env.API_KEY;

      if (!apiKey || !validKey || !safeCompare(apiKey, validKey)) {
        throw { statusCode: 403, message: 'Invalid API key' };
      }
    },
  };
}
```

## Zod Validation Middleware

```typescript
// middleware/validate.ts
import type { MiddlewareObj } from '@middy/core';
import { APIGatewayProxyEventV2 } from 'aws-lambda';
import { ZodSchema, ZodError } from 'zod';

export function validateBody<T>(schema: ZodSchema<T>): MiddlewareObj {
  return {
    before: async (request) => {
      const event = request.event as APIGatewayProxyEventV2;
      let body: unknown;

      try {
        body = JSON.parse(event.body ?? '{}');
      } catch {
        throw { statusCode: 400, message: 'Invalid JSON body' };
      }

      const result = schema.safeParse(body);
      if (!result.success) {
        throw {
          statusCode: 422,
          message: 'Validation failed',
          errors: result.error.flatten().fieldErrors,
        };
      }
      // Attach parsed, typed body
      (request.event as APIGatewayProxyEventV2 & { parsedBody: T }).parsedBody =
        result.data;
    },
  };
}

export function validateQuery<T>(schema: ZodSchema<T>): MiddlewareObj {
  return {
    before: async (request) => {
      const event = request.event as APIGatewayProxyEventV2;
      const result = schema.safeParse(event.queryStringParameters ?? {});
      if (!result.success) {
        throw {
          statusCode: 422,
          message: 'Invalid query parameters',
          errors: result.error.flatten().fieldErrors,
        };
      }
      (request.event as APIGatewayProxyEventV2 & { parsedQuery: T }).parsedQuery =
        result.data;
    },
  };
}
```

## Error Handler Middleware

```typescript
// middleware/error-handler.ts
import type { MiddlewareObj } from '@middy/core';
import { APIGatewayProxyResultV2 } from 'aws-lambda';
import { Logger } from '@aws-lambda-powertools/logger';

const logger = new Logger({ serviceName: 'api' });

interface AppError {
  statusCode?: number;
  message?: string;
  errors?: unknown;
}

export function errorHandlerMiddleware(): MiddlewareObj {
  return {
    onError: async (request) => {
      const error = request.error;
      // Middlewares may throw plain objects { statusCode, message } rather than Error instances.
      // Use type guards to safely extract fields from either shape.
      const statusCode = (error as any)?.statusCode ?? 500;
      const message = error instanceof Error ? error.message : String((error as any)?.message ?? 'Internal server error');
      const stack = error instanceof Error ? error.stack : undefined;
      const errors = (error as any)?.errors;

      if (statusCode >= 500) {
        logger.error('Unhandled error', { error: request.error });
      } else {
        logger.warn('Client error', { statusCode, message });
      }

      const response: APIGatewayProxyResultV2 = {
        statusCode,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: message,
          ...(errors && { errors }),
          ...(process.env.NODE_ENV !== 'production' && stack && { stack }),
        }),
      };

      // Return response — prevents Lambda from marking invocation as failed
      request.response = response;
    },
  };
}
```

## Correlation ID Middleware

```typescript
// middleware/correlation-id.ts
import type { MiddlewareObj } from '@middy/core';
import { APIGatewayProxyEventV2 } from 'aws-lambda';
import { randomUUID } from 'node:crypto';
import { Logger } from '@aws-lambda-powertools/logger';

export function correlationIdMiddleware(logger: Logger): MiddlewareObj {
  return {
    before: async (request) => {
      const event = request.event as APIGatewayProxyEventV2;
      const correlationId =
        event.headers?.['x-correlation-id'] ??
        event.requestContext?.requestId ??
        randomUUID();

      logger.appendKeys({ correlationId });
      // Forward to downstream calls via context
      (request.event as APIGatewayProxyEventV2 & { correlationId: string }).correlationId =
        correlationId;
    },
    after: async (request) => {
      // Reflect correlation ID in response
      if (request.response && typeof request.response === 'object') {
        const response = request.response as { headers?: Record<string, string> };
        response.headers = {
          ...response.headers,
          'x-correlation-id': (request.event as APIGatewayProxyEventV2 & { correlationId: string }).correlationId,
        };
      }
    },
  };
}
```

## CORS Middleware

Prefer configuring CORS at the API Gateway level (see SKILL.md). Add this only for edge cases where per-function CORS is needed.

```typescript
// middleware/cors.ts
import type { MiddlewareObj } from '@middy/core';
import { Logger } from '@aws-lambda-powertools/logger';

const _corsLogger = new Logger({ serviceName: 'cors-middleware' });
const ALLOWED_ORIGINS = process.env.ALLOWED_ORIGINS?.split(',').filter(Boolean) ?? [];

if (ALLOWED_ORIGINS.length === 0) {
  _corsLogger.warn('ALLOWED_ORIGINS not configured — CORS will reject all cross-origin requests');
}

export function corsMiddleware(): MiddlewareObj {
  return {
    after: async (request) => {
      // Reject all cross-origin requests when no origins are configured
      if (ALLOWED_ORIGINS.length === 0) return;

      const event = request.event as { headers?: { origin?: string } };
      const origin = event.headers?.origin ?? '';

      // Do not set CORS headers for origins not in the allowlist
      if (!origin || !ALLOWED_ORIGINS.includes(origin)) return;

      if (request.response && typeof request.response === 'object') {
        const response = request.response as { headers?: Record<string, string> };
        response.headers = {
          ...response.headers,
          'Access-Control-Allow-Origin': origin,
          'Access-Control-Allow-Credentials': 'true',
        };
      }
    },
  };
}
```

## Powertools Integration

```typescript
// Used as middy middleware — not manually called in handler
import { injectLambdaContext } from '@aws-lambda-powertools/logger/middleware';
import { captureLambdaHandler } from '@aws-lambda-powertools/tracer/middleware';
import { logMetrics } from '@aws-lambda-powertools/metrics/middleware';

// injectLambdaContext: adds requestId, xrayTraceId, coldStart to all log lines
// captureLambdaHandler: creates X-Ray subsegment wrapping the handler
// logMetrics: flushes CloudWatch EMF metrics after handler completes

export const handler = middy(lambdaHandler)
  .use(injectLambdaContext(logger, { clearState: true })) // clearState: remove per-request keys
  .use(captureLambdaHandler(tracer, { captureResponse: false })) // captureResponse: false avoids logging PII
  .use(logMetrics(metrics, { captureColdStartMetric: true }));
```

## Warm-Up Handler Pattern

When using provisioned concurrency, some schedulers send warm-up events. Short-circuit them:

```typescript
// lib/warmup.ts
import type { MiddlewareObj } from '@middy/core';
import { APIGatewayProxyResultV2 } from 'aws-lambda';

export function warmupMiddleware(): MiddlewareObj {
  return {
    before: async (request) => {
      const event = request.event as { source?: string };
      if (event.source === 'serverless-plugin-warmup') {
        request.response = { statusCode: 200, body: 'warmed' } satisfies APIGatewayProxyResultV2;
      }
    },
  };
}
```

## Composing a Full Middleware Stack

```typescript
// lib/create-handler.ts — factory to apply standard middleware
import middy from '@middy/core';
import { injectLambdaContext } from '@aws-lambda-powertools/logger/middleware';
import { captureLambdaHandler } from '@aws-lambda-powertools/tracer/middleware';
import { logMetrics } from '@aws-lambda-powertools/metrics/middleware';
import { APIGatewayProxyEventV2, APIGatewayProxyResultV2 } from 'aws-lambda';
import { Logger } from '@aws-lambda-powertools/logger';
import { Tracer } from '@aws-lambda-powertools/tracer';
import { Metrics } from '@aws-lambda-powertools/metrics';
import { ZodSchema } from 'zod';
import { correlationIdMiddleware } from '../middleware/correlation-id.js';
import { corsMiddleware } from '../middleware/cors.js';
import { authMiddleware } from '../middleware/auth.js';
import { validateBody } from '../middleware/validate.js';
import { errorHandlerMiddleware } from '../middleware/error-handler.js';
import { warmupMiddleware } from '../middleware/warmup.js';

interface HandlerOptions<TBody> {
  bodySchema?: ZodSchema<TBody>;
  auth?: boolean;
}

export function createHandler<TBody = never>(
  fn: (event: APIGatewayProxyEventV2 & { parsedBody?: TBody }) => Promise<APIGatewayProxyResultV2>,
  opts: HandlerOptions<TBody> = {}
) {
  const logger = new Logger({ serviceName: 'api' });
  const tracer = new Tracer({ serviceName: 'api' });
  const metrics = new Metrics({ namespace: 'MyApp', serviceName: 'api' });

  return middy(fn)
    .use(injectLambdaContext(logger, { clearState: true }))
    .use(captureLambdaHandler(tracer, { captureResponse: false }))
    .use(logMetrics(metrics, { captureColdStartMetric: true }))
    .use(correlationIdMiddleware(logger))
    .use(warmupMiddleware())
    .use(opts.auth !== false ? authMiddleware() : { before: async () => {} })
    .use(opts.bodySchema ? validateBody(opts.bodySchema) : { before: async () => {} })
    .use(errorHandlerMiddleware());
}

// Usage
export const handler = createHandler(lambdaHandler, {
  bodySchema: createItemSchema,
  auth: true,
});
```
