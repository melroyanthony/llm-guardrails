---
name: {{domain}}-frontend
description: |
  Implements {{domain}} frontend with Next.js 15 App Router and Server Components.
  Use when building pages, components, or client interactions.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# {{Domain}} Frontend

## Extends

- `foundation/frontend-nextjs`

## Domain Context

{{domain_context}}

## Project Structure

All code goes in `solution/frontend/`:

```
solution/frontend/
├── app/
│   ├── layout.tsx              # Root layout with providers
│   ├── page.tsx                # Home/dashboard page
│   ├── globals.css
{{#pages}}
│   ├── {{path}}/
│   │   ├── page.tsx            # {{description}}
│   │   └── loading.tsx         # Loading state
{{/pages}}
│   ├── api/                    # API routes (if needed)
│   └── actions/                # Server Actions
│       ├── {{domain}}.ts
├── components/
│   ├── ui/                     # Reusable UI components
│   └── {{domain}}/             # Domain-specific components
{{#components}}
│       ├── {{name}}.tsx
{{/components}}
├── lib/
│   ├── api.ts                  # API client (generated from OpenAPI)
│   └── utils.ts
├── types/
│   └── {{domain}}.ts           # TypeScript types
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

## Pages

{{#pages}}
### {{name}} (`/{{path}}`)

**Type:** {{component_type}} Component
**Purpose:** {{description}}

```tsx
{{#is_server}}
// Server Component (default) - can fetch data directly
import { db } from "@/lib/database";

export default async function {{name}}Page() {
  const data = await fetchData();
  return <{{name}}View data={data} />;
}
{{/is_server}}
{{#is_client}}
'use client';
// Client Component - for interactivity
import { useState } from 'react';

export default function {{name}}Page() {
  const [state, setState] = useState(initialState);
  return <{{name}}View />;
}
{{/is_client}}
```

{{/pages}}

## Components

{{#components}}
### {{name}}

**Type:** {{component_type}}
**Purpose:** {{description}}

```tsx
{{#is_client}}'use client';
{{/is_client}}
interface {{name}}Props {
  {{#props}}
  {{name}}: {{type}};
  {{/props}}
}

export function {{name}}({ {{props_destructure}} }: {{name}}Props) {
  {{implementation_hint}}
  return (
    <div>
      {/* {{description}} */}
    </div>
  );
}
```

{{/components}}

## Server Actions

{{#actions}}
### {{name}}

```tsx
'use server';

import { revalidatePath } from 'next/cache';

export async function {{name}}({{params}}) {
  // {{description}}
  {{implementation_hint}}
  revalidatePath('{{revalidate_path}}');
}
```

{{/actions}}

## Data Fetching Patterns

### From API

```tsx
// lib/api.ts - Generated from OpenAPI
const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export async function fetch{{Entity}}s() {
  const res = await fetch(`${API_BASE}/{{entity}}s`, {
    next: { revalidate: 60 } // ISR with 60s cache
  });
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
}
```

### Optimistic Updates

```tsx
'use client';
import { useOptimistic } from 'react';

function {{Component}}({ items }) {
  const [optimisticItems, addOptimistic] = useOptimistic(
    items,
    (state, newItem) => [...state, newItem]
  );

  async function handleAdd(formData) {
    addOptimistic({ ...newItem, pending: true });
    await create{{Entity}}(formData);
  }
}
```

## UI Patterns

{{#ui_patterns}}
### {{name}}

{{description}}

```tsx
{{code}}
```

{{/ui_patterns}}

## Validation Criteria

{{#validation_criteria}}
- [ ] {{criterion}}
{{/validation_criteria}}
