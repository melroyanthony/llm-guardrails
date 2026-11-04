---
description: "Scaffold an Nx monorepo for serverless TypeScript: Lambda API + Angular frontend + shared libs"
argument-hint: "<project-name>"
allowed-tools: Bash, Write, Read, Glob
---

# Serverless Init

Scaffold a production-ready Nx monorepo with npm workspaces for a serverless TypeScript stack.

## Input
$ARGUMENTS — Project name (kebab-case). Required.

## Stack
- **Backend**: Lambda + API Gateway (TypeScript, middy, Powertools)
- **Frontend**: Angular 21.x on ECS Fargate
- **Database**: Aurora Serverless v2 (Drizzle ORM) + DynamoDB (DynamoDB Toolbox)
- **Async**: SQS with Lambda triggers
- **IaC**: Terraform modules
- **Runtime**: Node.js 22 LTS via nvm

## Process

### 1. Validate input
```bash
PROJECT_NAME="$ARGUMENTS"
if [ -z "$PROJECT_NAME" ]; then
  echo "ERROR: Project name required. Usage: /serverless-init my-project"
  exit 1
fi
# Validate kebab-case: lowercase letters, digits, and hyphens only
if ! echo "$PROJECT_NAME" | grep -qE '^[a-z][a-z0-9-]*$'; then
  echo "ERROR: Project name must be kebab-case (e.g., my-project)"
  exit 1
fi
```

### 2. Create Nx monorepo with npm workspaces
```bash
# Ensure correct Node.js version
source ~/.nvm/nvm.sh 2>/dev/null || true
nvm use 22 || nvm install 22

npx create-nx-workspace@latest $PROJECT_NAME \
  --preset=ts \
  --nxCloud=skip \
  --packageManager=npm
cd $PROJECT_NAME
```

### 3. Add Angular frontend app
```bash
npx nx add @nx/angular
npx nx g @nx/angular:app shell --style=scss --routing --standalone --ssr=false
```

### 4. Create Lambda API workspace package
```bash
mkdir -p apps/api/src/{functions,middleware,lib}
mkdir -p apps/api/src/functions/{health,users,configs}

# Create apps/api/package.json so npm workspaces recognizes it
cat > apps/api/package.json << APIPKG
{
  "name": "@${PROJECT_NAME}/api",
  "version": "0.0.0",
  "private": true,
  "type": "module"
}
APIPKG

# Create Nx project config so nx build/test/lint targets work
cat > apps/api/project.json << PROJJSON
{
  "name": "api",
  "root": "apps/api",
  "sourceRoot": "apps/api/src",
  "targets": {
    "build": {
      "executor": "nx:run-commands",
      "options": { "command": "node apps/api/esbuild.config.mjs" }
    },
    "test": {
      "executor": "nx:run-commands",
      "options": { "command": "vitest run --config apps/api/vitest.config.ts" }
    }
  }
}
PROJJSON
```

### 5. Create shared libraries
```bash
npx nx g @nx/js:lib shared --directory=libs/shared --bundler=esbuild
npx nx g @nx/js:lib db --directory=libs/db --bundler=esbuild
```

### 6. Create infrastructure directory
```bash
mkdir -p infrastructure/terraform/{modules,environments}
mkdir -p infrastructure/terraform/modules/{lambda,aurora,dynamodb,ecs,sqs,vpc}
mkdir -p infrastructure/terraform/environments/{dev,staging,prod}
```

### 7. Initialize key config files

**Root `package.json`** — Ensure npm workspaces:
```json
{
  "workspaces": ["apps/*", "libs/*"]
}
```

**`apps/api/tsconfig.json`** — Strict TypeScript for Lambda:
```json
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "esModuleInterop": true,
    "outDir": "dist",
    "rootDir": "src",
    "declaration": true,
    "sourceMap": true
  }
}
```

**`apps/api/vitest.config.ts`** — Test configuration:
```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['src/**/*.test.ts'],
    coverage: { provider: 'v8', reporter: ['text', 'lcov'] },
  },
});
```

**`.nvmrc`**:
```
22
```

**`apps/api/esbuild.config.mjs`** — Lambda bundling:
```javascript
import { build } from 'esbuild';
import { glob } from 'glob';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

// Resolve paths relative to this config file's directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const entryPoints = await glob(`${__dirname}/src/functions/**/handler.ts`);

await build({
  entryPoints,
  bundle: true,
  platform: 'node',
  target: 'node22',
  format: 'esm',
  outdir: `${__dirname}/dist`,
  // Bundle everything including AWS SDK v3 — Lambda runtime only has SDK v2
  minify: true,
  treeShaking: true,
  sourcemap: true,
});
```

### 8. Install core dependencies

```bash
# Install from workspace root using -w flag for proper lockfile management
npm install -w apps/api @middy/core @middy/http-cors @middy/http-error-handler @middy/http-json-body-parser
npm install -w apps/api @aws-lambda-powertools/logger @aws-lambda-powertools/tracer @aws-lambda-powertools/metrics
npm install -w apps/api zod @aws-sdk/client-dynamodb @aws-sdk/lib-dynamodb @aws-sdk/client-sqs
npm install -w apps/api drizzle-orm pg dynamodb-toolbox
npm install -w apps/api -D @types/aws-lambda @types/pg drizzle-kit esbuild glob vitest

# Angular dependencies (already installed by Nx)
# Add @angular/ssr later if SSR is needed
```

### 9. Create starter Lambda handler

Write `apps/api/src/functions/health/handler.ts`:
```typescript
import middy from '@middy/core';
import httpJsonBodyParser from '@middy/http-json-body-parser';
import httpErrorHandler from '@middy/http-error-handler';
import cors from '@middy/http-cors';
import { Logger } from '@aws-lambda-powertools/logger';
import type { APIGatewayProxyEventV2, APIGatewayProxyResultV2 } from 'aws-lambda';

const logger = new Logger({ serviceName: 'health' });

const lambdaHandler = async (
  event: APIGatewayProxyEventV2
): Promise<APIGatewayProxyResultV2> => {
  logger.info('Health check', { path: event.rawPath });
  return {
    statusCode: 200,
    body: JSON.stringify({ status: 'ok', timestamp: new Date().toISOString() }),
  };
};

export const handler = middy(lambdaHandler)
  .use(httpJsonBodyParser())
  .use(httpErrorHandler())
  .use(cors());
```

### 10. Create Terraform entry point

Write `infrastructure/terraform/main.tf`:
```hcl
terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  default = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
}
```

### 11. Git init and first commit
```bash
git add .
git commit -m "feat(stage-0): scaffold Nx monorepo with Lambda + Angular + Terraform"
```

## Output
- Nx monorepo with npm workspaces
- Lambda API app with starter health handler
- Angular 21.x frontend app
- Shared libraries (types, database)
- Terraform module structure
- Ready for `/orchestrate` pipeline
