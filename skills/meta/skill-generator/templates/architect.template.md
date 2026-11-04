---
name: {{domain}}-architecture
description: |
  Designs {{domain}} system architecture, API contracts, and data models.
  Use when creating C4 diagrams, OpenAPI specs, or database schemas.
allowed-tools: Read, Grep, Glob, Write, Edit
---

# {{Domain}} Architecture

## System Context

{{system_context}}

## C4 Model

### Level 1: System Context

```
[User] --> [{{system_name}}]
{{#external_systems}}
[{{system_name}}] --> [{{name}}] : {{description}}
{{/external_systems}}
```

### Level 2: Container Diagram

| Container | Technology | Purpose |
|-----------|------------|---------|
| Frontend  | Next.js 15 | {{frontend_purpose}} |
| Backend   | FastAPI    | {{backend_purpose}} |
| Database  | PostgreSQL | {{database_purpose}} |

### Level 3: Component Diagram

**Backend Components:**
{{#backend_components}}
- `{{name}}`: {{description}}
{{/backend_components}}

**Frontend Components:**
{{#frontend_components}}
- `{{name}}`: {{description}}
{{/frontend_components}}

## Data Model

### Entities

```
{{#entities}}
{{name}}
├── {{#attributes}}{{name}}: {{type}}{{#required}} (required){{/required}}
{{/attributes}}
└── relationships: {{#relationships}}{{name}}{{/relationships}}

{{/entities}}
```

### Database Schema

{{database_schema}}

## API Contract

### Endpoints

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
{{#endpoints}}
| {{method}} | {{path}} | {{description}} | {{request}} | {{response}} |
{{/endpoints}}

### OpenAPI Spec Location

`solution/docs/architecture/openapi.yaml`

## Key Decisions

{{#decisions}}
### ADR-{{number}}: {{title}}

**Status:** {{status}}
**Context:** {{context}}
**Decision:** {{decision}}
**Consequences:** {{consequences}}

{{/decisions}}

## Non-Functional Requirements

| Requirement | Target | Approach |
|-------------|--------|----------|
{{#nfrs}}
| {{name}} | {{target}} | {{approach}} |
{{/nfrs}}
