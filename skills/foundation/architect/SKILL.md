---
name: architect
description: |
  Designs system architecture, C4 diagrams, API contracts, and database schemas.
  Use when creating architecture, defining APIs, or making structural decisions.
  Triggers on: "architecture", "C4", "API design", "schema", "ADR", "contract".
allowed-tools: Read, Grep, Glob, Write, Edit
---

# Architect Agent

Creates coherent system architecture with C4 diagrams, OpenAPI specs, and database schemas.

## Workflow

1. **Context**: Define system boundaries and actors
2. **Containers**: Identify major deployable units
3. **Components**: Detail internal structure
4. **Contracts**: Define API and data interfaces
5. **Decisions**: Document key choices as ADRs. Draw the container view and any status or call order as a fenced `mermaid` block. The `diagrams` skill is the rule for type, size, and keeping the picture true when the code changes.

## Project Structure Convention (Cognita-inspired)

```
solution/
├── backend/               # FastAPI application
│   ├── app/
│   │   ├── config.py      # Settings singleton
│   │   ├── database.py    # Async engine
│   │   ├── models/        # SQLModel tables
│   │   ├── modules/       # Feature modules (pluggable)
│   │   ├── api/v1/        # API routes
│   │   └── services/      # Shared business logic
│   ├── tests/
│   ├── alembic/
│   └── Dockerfile
├── frontend/              # Next.js application
│   ├── app/               # App Router pages
│   ├── components/        # React components
│   ├── lib/               # API client, utilities
│   ├── types/             # TypeScript types
│   └── Dockerfile
├── docs/                  # Architecture documentation
│   ├── architecture/
│   │   ├── workspace.dsl  # C4 diagrams
│   │   ├── openapi.yaml   # API specification
│   │   └── database-schema.md
│   └── decisions/         # ADRs
│       └── ADR-*.md
├── volumes/               # Docker volume data (gitignored)
├── docker-compose.yml     # Orchestration
├── .env.example           # Environment template
├── Makefile               # Dev commands
└── README.md              # Cognita-style README
```

Key principles:
- **Modular backend**: Feature modules are self-contained and pluggable
- **Docs in output**: Architecture docs deploy with the code
- **Volume persistence**: Docker volumes in `./volumes/` for easy inspection
- **Single compose**: One `docker-compose.yml` for full stack

## C4 Model with Structurizr DSL

### Workspace Template

```dsl
workspace "{Project Name}" {
    !identifiers hierarchical

    model {
        # People
        user = person "User" "End user of the system"

        # System
        system = softwareSystem "{System Name}" {
            frontend = container "Frontend" "Next.js 15" "Web Application" {
                tags "Web"
            }
            backend = container "Backend" "FastAPI" "REST API" {
                tags "API"
            }
            database = container "Database" "PostgreSQL 17" "Data Store" {
                tags "Database"
            }
        }

        # Relationships
        user -> system.frontend "Uses" "HTTPS"
        system.frontend -> system.backend "API calls" "JSON/HTTPS"
        system.backend -> system.database "Reads/Writes" "asyncpg"
    }

    views {
        systemContext system "Context" {
            include *
            autoLayout
        }

        container system "Containers" {
            include *
            autoLayout tb
        }

        styles {
            element "Web" {
                shape WebBrowser
                background #438DD5
            }
            element "API" {
                shape Hexagon
                background #85BBF0
            }
            element "Database" {
                shape Cylinder
                background #438DD5
            }
        }
    }
}
```

### Running Structurizr Lite

```bash
docker run -p 8080:8080 \
  -v $(pwd)/solution/docs/architecture:/usr/local/structurizr \
  structurizr/lite
```

Then open http://localhost:8080 to view diagrams.

## OpenAPI Spec Template

```yaml
openapi: 3.1.0
info:
  title: {Project Name} API
  version: 1.0.0
  description: |
    {Brief description}

servers:
  - url: http://localhost:8000
    description: Development

paths:
  /api/v1/{resource}:
    get:
      summary: List {resources}
      operationId: list{Resources}
      tags:
        - {resource}
      parameters:
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
        - name: offset
          in: query
          schema:
            type: integer
            default: 0
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/{Resource}'

    post:
      summary: Create {resource}
      operationId: create{Resource}
      tags:
        - {resource}
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/{Resource}Create'
      responses:
        '201':
          description: Created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/{Resource}'

components:
  schemas:
    {Resource}:
      type: object
      required:
        - id
        - name
      properties:
        id:
          type: integer
        name:
          type: string
        created_at:
          type: string
          format: date-time

    {Resource}Create:
      type: object
      required:
        - name
      properties:
        name:
          type: string
```

## Database Schema Patterns

### Entity Naming

- Tables: `snake_case`, plural (`inventory_items`)
- Columns: `snake_case` (`created_at`)
- Foreign keys: `{related_table}_id` (`location_id`)
- Indexes: `idx_{table}_{column}` (`idx_inventory_items_location_id`)

### Standard Columns

Every table should have:
```sql
id SERIAL PRIMARY KEY,
created_at TIMESTAMP DEFAULT NOW(),
updated_at TIMESTAMP DEFAULT NOW()
```

### Relationship Patterns

```
One-to-Many: Parent has `id`, Child has `parent_id`
Many-to-Many: Junction table with both foreign keys
```

## ADR Template

```markdown
# ADR-{number}: {Title}

## Status
{Proposed | Accepted | Deprecated | Superseded}

## Context
{What is the issue that we're seeing that is motivating this decision?}

## Decision
{What is the change that we're proposing and/or doing?}

## Consequences

### Positive
- {Good outcome}

### Negative
- {Trade-off accepted}

### Neutral
- {Side effect}
```

## Output Artifacts

All artifacts go inside `solution/` for clean deployment:

| Artifact | Path | Format |
|----------|------|--------|
| User Journeys | `solution/docs/architecture/user-journeys.md` | Markdown + Mermaid |
| Data Flow | `solution/docs/architecture/data-flow.md` | Markdown + Mermaid |
| System Design | `solution/docs/architecture/system-design.md` | Markdown |
| C4 Workspace | `solution/docs/architecture/workspace.dsl` | Structurizr DSL |
| OpenAPI Spec | `solution/docs/architecture/openapi.yaml` | OpenAPI 3.1 |
| Error Catalog | `solution/docs/architecture/api-error-catalog.md` | Markdown |
| Database Schema | `solution/docs/architecture/database-schema.md` | Markdown + SQL |
| Security Model | `solution/docs/architecture/security-model.md` | Markdown |
| Deployment Topology | `solution/docs/architecture/deployment-topology.md` | Markdown + Mermaid |
| Postman Collection | `solution/docs/api-testing/collection.json` | Postman v2.1 |
| Postman Env (Dev) | `solution/docs/api-testing/env.dev.json` | Postman Environment |
| Postman Env (Staging) | `solution/docs/api-testing/env.staging.json` | Postman Environment |
| ADRs | `solution/docs/decisions/ADR-{NNN}-*.md` | Markdown |

## Anti-Rationalization Guide

Common excuses agents use to skip architecture steps — and why they are wrong:

| Rationalization | Reality |
|---|---|
| "The architecture is obvious, I'll skip the C4 diagram" | If it's obvious, the diagram takes 5 minutes. If it's not, you just saved yourself from discovering a missing component mid-implementation. |
| "I'll define the API as I build it" | Ad-hoc APIs accumulate inconsistencies (mixed naming, missing pagination, inconsistent error formats) that are expensive to fix once frontends depend on them. |
| "We don't need ADRs for a small project" | ADRs aren't about project size — they're about preventing the next agent (or your future self) from re-debating a decision you already resolved. Two sentences is enough. |
| "The database schema will emerge from the models" | Schema-first catches relationship issues (missing foreign keys, wrong cardinality, missing indexes) before any code is written. Model-first embeds those issues in code. |
| "Security can be added later" | Security bolted on after the fact is always weaker and more expensive than security designed in. Auth, authz, and input validation are architectural decisions, not features. |
| "One ADR is enough" | One ADR means you only documented one decision. You made dozens. The two most impactful undocumented decisions will be the ones the next agent gets wrong. |

## Quality Checklist

- [ ] User journeys cover all primary flows with acceptance criteria
- [ ] Data flow diagrams show request lifecycle (Mermaid sequence)
- [ ] C4 diagrams accurately represent the system
- [ ] All MVP endpoints defined in OpenAPI
- [ ] Request/response schemas complete
- [ ] API error catalog covers auth, resources, and system errors
- [ ] Database schema handles all entities with relationships
- [ ] Security model documents auth, authz, rate limiting
- [ ] Deployment topology defined for dev and production
- [ ] At least 2 meaningful ADRs written
- [ ] Environment variables documented
- [ ] Naming is consistent across all artifacts
