---
name: frontend-angular-ecs
description: |
  Angular 21.x frontend on ECS Fargate with Nx monorepo, standalone components, and signals.
  Use when building Angular frontends deployed on ECS Fargate with container orchestration.
  Triggers on: "Angular", "ECS", "Fargate", "standalone component", "signals", "SSR", "ALB".
---


# Frontend: Angular 21.x on ECS Fargate

Production Angular frontend containerized with nginx, deployed on ECS Fargate behind an Application Load Balancer. Uses Nx monorepo for multi-app/lib organization and npm workspaces for dependency sharing.

## Version Matrix

| Tool / Package | Version | Notes |
|---|---|---|
| Angular | 21.x | Standalone components, zoneless, signals |
| Node.js | 22 LTS | Via nvm (`nvm use 22`) — always required |
| Nx | 21.x | Monorepo build system, affected commands |
| TypeScript | 5.7+ | strict mode required |
| nginx | alpine | Serves SPA, proxies API calls, injects env |
| @angular/ssr | 21.x | Server-side rendering (optional) |
| npm workspaces | — | Root package.json workspace config |

## Nx Monorepo Setup

### Initialize a New Workspace

```bash
# Always load nvm before any Node work
source ~/.nvm/nvm.sh
nvm use 22 || nvm install 22

# Create Angular monorepo preset (Angular 21 + Nx 21)
npx create-nx-workspace@latest my-workspace \
  --preset=angular-monorepo \
  --appName=shell \
  --style=scss \
  --nxCloud=skip

cd my-workspace

# Generate additional libs
npx nx generate @nx/angular:library ui --standalone --directory=libs/ui
npx nx generate @nx/js:library data-access --bundler=none --directory=libs/data-access
npx nx generate @nx/js:library util --bundler=none --directory=libs/util
```

### npm Workspaces in Root `package.json`

```json
{
  "name": "my-workspace",
  "private": true,
  "workspaces": [
    "apps/*",
    "libs/*"
  ],
  "scripts": {
    "start":    "nx serve shell",
    "build":    "nx build shell --configuration=production",
    "test":     "nx run-many --target=test --all",
    "lint":     "nx run-many --target=lint --all",
    "affected": "nx affected --base=origin/main --head=HEAD"
  }
}
```

### Project Structure

```
my-workspace/
├── apps/
│   └── shell/                    # Main Angular SPA
│       ├── src/
│       │   ├── app/
│       │   │   ├── app.config.ts       # Standalone bootstrap config
│       │   │   ├── app.component.ts
│       │   │   ├── app.routes.ts       # Lazy-loaded routes
│       │   │   ├── features/
│       │   │   └── interceptors/
│       │   ├── environments/
│       │   │   └── runtime-env.ts      # Reads window.__env at runtime
│       │   ├── index.html
│       │   └── main.ts
│       ├── Dockerfile
│       ├── nginx.conf
│       ├── docker-entrypoint.sh
│       └── project.json
├── libs/
│   ├── ui/               # Shared standalone component library
│   ├── data-access/      # HttpClient services, signals stores
│   └── util/             # Pure functions, pipes, validators
└── package.json
```

## When NOT to Use Angular + ECS

| Scenario | Better Choice |
|---|---|
| Static marketing / docs site | S3 + CloudFront (no server cost, no ops) |
| Simple internal SPA, < 5 devs | React + Vite on Amplify Hosting |
| Server-rendered blog or e-commerce for SEO | Next.js on Lambda@Edge or App Runner |
| Mobile app with web code sharing | Ionic + Capacitor |
| < 1000 users, no enterprise requirements | Any static hosting + Lambda API |

Angular + ECS is the right choice when: large teams, complex component architecture, strong TypeScript discipline, enterprise UI needs (component libraries, design systems), and Fargate suits your ops model.

## See Also

- `CONTAINER-SETUP.md` — Multi-stage Dockerfile, nginx.conf, entrypoint.sh, CloudWatch logging
- `backend-serverless-ts/SKILL.md` — API Gateway backend this Angular app calls
- `infrastructure/SERVERLESS-IAC.md` — ALB, ECS cluster, ECR, auto-scaling Terraform modules

## References (progressive disclosure)

Load only when needed:

- [`references/angular-patterns.md`](references/angular-patterns.md)
- [`references/ecs-deployment.md`](references/ecs-deployment.md)


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
