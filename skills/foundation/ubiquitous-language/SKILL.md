---
name: ubiquitous-language
description: |
  Extract and formalize domain terminology into a shared glossary. Prevents terminology drift
  across pipeline stages where different agents may use different words for the same concept.
  Use when domain terminology is ambiguous or inconsistent across agents or stages.
  Triggers on: "domain terms", "glossary", "terminology", "what does X mean", "naming".
allowed-tools: Read, Glob, Grep, Write, Edit
---

# Ubiquitous Language

Extract domain terminology from requirements and conversations into a shared glossary that all agents reference consistently.

## Principle

When the product-manager says "user," the architect says "account," and the developer says "profile" — they're creating three models for one concept. A shared glossary eliminates this drift.

## Output File

`solution/UBIQUITOUS_LANGUAGE.md`:

```markdown
# Ubiquitous Language

Domain terminology for [project name]. All agents and documentation MUST use these terms consistently.

## Terms

### Item
- **Definition**: A physical product tracked in the inventory system
- **NOT**: "product" (marketing term), "SKU" (internal identifier only), "thing"
- **Used in**: API endpoints (`/api/v1/items`), database table (`items`), UI components
- **Example**: "An item has a name, quantity, and location"

### Movement
- **Definition**: A change in an item's quantity (inbound or outbound)
- **NOT**: "transaction" (implies financial), "transfer" (implies location change)
- **Used in**: API (`/api/v1/movements`), business logic, reports

## Ambiguities Resolved

| Ambiguous Term | Resolved To | Rationale |
|---|---|---|
| "user" vs "account" | **User** | Matches auth provider terminology (JWT claims) |
| "stock" vs "inventory" | **Inventory** | "Stock" is ambiguous (stock market, livestock) |
```

## When to Run

### Stage 1 (Product Manager)
After requirements analysis, extract domain terms from `problem/PROBLEM.md` and requirements docs. Write initial glossary.

### Stage 2 (Architect)
Read existing glossary. Add technical terms from architecture decisions (database tables, API resources, service names). Flag any terminology conflicts with Stage 1.

### Stage 3 (Implementation)
Reference glossary for naming: variable names, function names, route paths, database columns, component names. All must use glossary terms.

### Re-Running (Incremental Updates)
When invoked on a project with an existing glossary:
1. Read current `solution/UBIQUITOUS_LANGUAGE.md`
2. Incorporate new terms from the current context
3. Update evolved definitions
4. Re-flag new ambiguities
5. Do NOT remove existing resolved terms

## Extraction Process

1. **Read the source** (problem statement, requirements, architecture docs, existing code)
2. **Identify domain nouns** — entities, resources, concepts that appear repeatedly
3. **Flag ambiguities** — same word used for different concepts, or different words for same concept
4. **Propose canonical terms** — one word per concept, with clear definition
5. **Document "NOT" alternatives** — explicitly list terms that should NOT be used
6. **Map to code** — how each term appears in API paths, database tables, variable names

## Naming Rules

| Layer | Convention | Example |
|---|---|---|
| API path | kebab-case plural | `/api/v1/inventory-items` |
| Database table | snake_case plural | `inventory_items` |
| Python model | PascalCase singular | `InventoryItem` |
| TypeScript interface | PascalCase singular | `InventoryItem` |
| Variable | camelCase/snake_case singular | `inventoryItem` / `inventory_item` |
| Component | PascalCase singular | `InventoryItemList` |

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Everyone knows what we mean" | They don't. Three agents will use three different terms for the same concept. |
| "We can rename things later" | Renaming touches API paths, database columns, variable names, tests, and docs. Do it once, now. |
| "A glossary is overkill for a small project" | Small projects have 5-10 domain terms. Writing them down takes 5 minutes and prevents 5 hours of confusion. |
