---
description: Implement Next.js frontend with TypeScript (Stage 3)
allowed-tools: Read, Glob, Grep, Write, Edit, Bash
---

# Frontend Developer

Implement production-ready Next.js frontend based on architecture specs.

## Tech Stack
- Node.js 22 (via nvm)
- Next.js 15+ with App Router
- TypeScript strict mode
- Tailwind CSS

## Project Setup

```bash
cd solution
source ~/.nvm/nvm.sh
nvm use 22 || nvm install 22

npx create-next-app@latest frontend \
  --typescript --tailwind --eslint --app \
  --src-dir=false --import-alias="@/*" --use-npm --yes

cd frontend
npm list --depth=0
```

## Code Structure
```
frontend/
├── app/
│   ├── layout.tsx       # Root layout
│   ├── page.tsx         # Home page
│   └── [feature]/page.tsx
├── components/          # Reusable components
├── lib/api.ts           # API client
├── types/api.ts         # TypeScript types
└── next.config.ts
```

## Critical Patterns

### TypeScript Types (match backend)
```typescript
export interface Item {
  id: number;
  name: string;
  quantity: number;
}
```

### API Client
```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${endpoint}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) throw new Error("API Error");
  return response.json();
}
```

### Client Components
```typescript
"use client";
import { useState, useEffect } from "react";
```

### Docker Config
```typescript
// next.config.ts
const nextConfig = { output: "standalone" };
```

## Test Tooling Setup

```bash
npm install -D vitest @vitejs/plugin-react vite-tsconfig-paths @testing-library/react @testing-library/jest-dom jsdom
```

Add to `package.json`:
```json
{ "scripts": { "test": "vitest run" } }
```

Create `vitest.config.ts` (jsdom environment, setup file for jest-dom matchers):
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  test: { environment: 'jsdom', globals: true, setupFiles: './tests/setup.ts' },
});
```

Create `tests/setup.ts`:
```typescript
import '@testing-library/jest-dom/vitest';
```

## Implementation Flow (TDD)

Follow RED → GREEN → REFACTOR for data-driven components. Skip TDD for layout/visual-only components.

1. Set up test tooling (Vitest + Testing Library + jsdom)
2. Create TypeScript types matching backend models
3. Implement API client functions (with tests)
4. For each data component (lists, forms, detail views):
   - Write test (RED): `tests/<component>.test.tsx`
   - Implement component (GREEN)
   - Commit with tests included
5. Compose pages with components
6. Update next.config.ts for Docker
7. Run full suite: `npm test`

## Run Commands
```bash
npm run dev
npm run build
```

## Input
- OpenAPI spec from `solution/docs/architecture/openapi.yaml`
- Backend API running on localhost:8000
