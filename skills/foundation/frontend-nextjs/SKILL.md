---
name: frontend-nextjs
description: |
  Implements Next.js 15 frontends with App Router, Server Components, and TypeScript.
  Use when building pages, components, data fetching, or client interactions.
  Triggers on: "Next.js", "frontend", "React", "component", "page", "Server Component".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---


# Frontend Next.js Agent

Builds production-ready Next.js 15.5.9 applications with App Router and Server Components.

## Version Matrix (December 2025)

| Package | Version | Notes |
|---------|---------|-------|
| Next.js | 15.5.9 | App Router stable |
| React | 19.x | Server Components default |
| TypeScript | 5.x | Strict mode enabled |
| Node.js | 22.x | LTS, use Alpine for Docker |

## Project Initialization

**IMPORTANT**: Always use `nvm` for Node.js version management and `npx` for scaffolding. Never manually create package.json.

### Step 1: Set Node.js Version

```bash
# Load nvm (required in scripts)
source ~/.nvm/nvm.sh

# Use Node.js 22 LTS
nvm use 22 || nvm install 22

# Verify version
node --version  # Should show v22.x.x
```

### Step 2: Create Next.js Project (New Project)

```bash
# Navigate to output directory
cd solution

# Create Next.js app with App Router (installs deps automatically)
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir=false \
  --import-alias="@/*" \
  --use-npm \
  --yes

# Enter project directory
cd frontend

# Verify dependencies installed
npm list --depth=0
```

### For Existing Project (package.json exists)

```bash
cd solution/frontend

# Load nvm and set Node version
source ~/.nvm/nvm.sh
nvm use 22 || nvm install 22

# Install all dependencies (fetches latest compatible)
npm install

# Verify installation
npm list --depth=0
```

### Step 3: Add Additional Dependencies (if needed)

```bash
# Add runtime dependencies
npm install <package-name>

# Add dev dependencies
npm install --save-dev <package-name>
```

**CRITICAL**: Always run `source ~/.nvm/nvm.sh && nvm use 22` before npm commands, and `npm install` when node_modules is missing.

### Step 4: Configure for Docker (standalone output)

Edit `next.config.ts` to enable standalone output:

```typescript
// next.config.ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
};

export default nextConfig;
```

### Step 5: Create Additional Directories

```bash
# Create component structure
mkdir -p components/{ui,inventory}
mkdir -p lib types

# Create placeholder files
touch lib/api.ts lib/utils.ts types/index.ts
```

## Key Concepts

### Server Components (Default)

- Run on the server only
- Can directly access databases, file system, etc.
- Can use `async/await` at component level
- Smaller bundle size (no client JS shipped)
- **Cannot use**: `useState`, `useEffect`, event handlers, browser APIs

### Client Components

- Add `'use client'` directive at top of file
- Run on both server (SSR) and client
- **Can use**: React hooks, event handlers, browser APIs
- **Cannot use**: Async component functions

### Decision Rule

```
Does this component need interactivity?
├── No → Server Component (default)
└── Yes
    └── Does it need state or event handlers?
        ├── Yes → Client Component ('use client')
        └── No → Server Component with client child
```

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Home page
│   ├── globals.css
│   ├── loading.tsx          # Global loading UI
│   ├── error.tsx            # Global error UI
│   ├── {route}/
│   │   ├── page.tsx         # Route page
│   │   ├── layout.tsx       # Route layout (optional)
│   │   ├── loading.tsx      # Route loading (optional)
│   │   └── error.tsx        # Route error (optional)
│   └── api/                 # API routes (rarely needed)
├── components/
│   ├── ui/                  # Reusable UI components
│   └── {domain}/            # Domain-specific components
├── lib/
│   ├── api.ts               # API client
│   └── utils.ts             # Utility functions
├── types/
│   └── index.ts             # TypeScript types
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
└── package.json
```

## When NOT to Use
- **Angular required**: Use `frontend-angular-ecs` skill instead
- **Static site (no dynamic content)**: Use plain React+Vite or Astro — Next.js adds unnecessary complexity
- **Mobile app**: Use React Native, not Next.js
- **ECS Fargate with Angular stack**: If the architecture specifies Angular, use `frontend-angular-ecs` skill — Next.js also deploys well on Fargate via standalone output mode
- **No SSR/SEO needed**: Consider React+Vite for pure SPAs — lighter bundle, simpler deployment

## See Also

- `devops` skill for Dockerfile and docker-compose patterns
- `language-selection` skill for choosing between Next.js and other frontend options
- Server Actions pattern: covered inline in this skill under "Server Actions (Mutations)"

## References (progressive disclosure)

Load only when needed:

- [`references/core-patterns.md`](references/core-patterns.md)
- [`references/api-client-and-config.md`](references/api-client-and-config.md)


## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll skip the reference docs and improvise" | Load the linked reference for the stack you're on — improvisation causes drift |
| "This is too small for the checklist" | Run the verification checklist anyway; small skips compound |

## Red Flags

- Implementing from memory instead of loading the relevant `references/` file
- Skipping health checks, CI, or project structure conventions in the skill

## Verification

- [ ] Version matrix followed for the chosen stack
- [ ] Required reference file(s) loaded for the work in progress
- [ ] Quality / When-NOT checklist reviewed
