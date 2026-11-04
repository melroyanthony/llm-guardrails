---
name: {{domain}}-database
description: |
  Manages {{domain}} database schema, migrations, and data operations.
  Use when creating migrations, seeding data, or optimizing queries.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# {{Domain}} Database

## Extends

- `foundation/database`

## Schema Overview

```sql
{{#tables}}
-- {{description}}
CREATE TABLE {{name}} (
    id SERIAL PRIMARY KEY,
    {{#columns}}
    {{name}} {{type}}{{#nullable}}{{else}} NOT NULL{{/nullable}}{{#default}} DEFAULT {{default}}{{/default}},
    {{/columns}}
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

{{#indexes}}
CREATE INDEX idx_{{table}}_{{name}} ON {{table}}({{columns}});
{{/indexes}}

{{/tables}}
```

## Relationships

```
{{#relationships}}
{{from}} {{cardinality}} {{to}} : {{description}}
{{/relationships}}
```

## Migration Strategy

1. **Initial migration**: Create all tables with relationships
2. **Seed data**: Load from problem statement data sources
3. **Indexes**: Add after confirming query patterns

## Seed Data

{{#seed_sources}}
### {{name}}

**Source:** {{source}}
**Target Table:** {{target_table}}
**Transform:** {{transform_description}}

```python
async def seed_{{snake_name}}(db: AsyncSession):
    # Load from {{source}}
    data = load_{{source_type}}("{{source_path}}")

    for row in data:
        record = {{model}}(
            {{#mappings}}
            {{field}}=row["{{source_field}}"],
            {{/mappings}}
        )
        db.add(record)

    await db.commit()
```

{{/seed_sources}}

## Query Patterns

{{#queries}}
### {{name}}

**Purpose:** {{description}}
**Frequency:** {{frequency}}

```python
async def {{function_name}}(db: AsyncSession, {{params}}) -> {{return_type}}:
    stmt = select({{model}}){{#joins}}.join({{join}}){{/joins}}
    {{#filters}}.where({{filter}}){{/filters}}
    {{#order}}.order_by({{order}}){{/order}}
    result = await db.execute(stmt)
    return result.{{fetch_method}}()
```

{{/queries}}

## Validation Criteria

{{#validation_criteria}}
- [ ] {{criterion}}
{{/validation_criteria}}
