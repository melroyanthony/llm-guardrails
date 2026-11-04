---
name: deprecation-migration
description: |
  Patterns for evolving existing codebases: strangler fig, adapter pattern, migration playbooks,
  compulsory vs advisory deprecation decisions.
  Use when migrating legacy code, deprecating APIs, or planning incremental rewrites.
  Triggers on: deprecation, migration, upgrade, legacy, strangler, backward compatibility.
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Deprecation and Migration Patterns

## Principle

Code is a liability, not an asset. Every line of code is a line that must be maintained, tested, and secured. Migration is how you manage that liability over time.

## Migration Patterns

### 1. Strangler Fig

Replace a legacy system incrementally by routing traffic through a new system that grows over time:

```
Request → Router → [New System handles /api/v2/*]
                 → [Legacy System handles everything else]
```

**When to use**: Large systems where big-bang replacement is too risky.

**Steps**:
1. Add a routing layer in front of the legacy system
2. Implement new functionality in the new system
3. Route specific endpoints to the new system
4. Gradually migrate remaining endpoints
5. Decommission the legacy system when fully migrated

### 2. Branch-by-Abstraction

Toggle between old and new implementations behind an interface:

```python
class PaymentProcessor(Protocol):
    def charge(self, amount: Decimal, token: str) -> ChargeResult: ...

class LegacyStripeProcessor:  # Old implementation
    def charge(self, amount, token): ...

class NewStripeProcessor:     # New implementation
    def charge(self, amount, token): ...

# Toggle via feature flag or config
processor = NewStripeProcessor() if use_new_stripe else LegacyStripeProcessor()
```

**When to use**: Swapping implementations of a well-defined interface.

### 3. Adapter Pattern

Bridge between old and new interfaces during migration:

```python
class NewAPIClient:
    def create_order(self, order: OrderV2) -> OrderResponse: ...

class LegacyAPIAdapter:
    """Adapts legacy OrderV1 calls to the new OrderV2 API."""
    def __init__(self, new_client: NewAPIClient):
        self._client = new_client

    def place_order(self, order: OrderV1) -> dict:
        v2_order = self._convert(order)
        response = self._client.create_order(v2_order)
        return self._convert_response(response)
```

**When to use**: External consumers depend on the old API shape.

### 4. Parallel Run

Run both old and new systems, compare results, cut over when confident:

```python
def process_payment(request):
    old_result = legacy_system.process(request)
    new_result = new_system.process(request)

    if old_result != new_result:
        logger.warning("Divergence detected", old=old_result, new=new_result)

    return old_result  # Still serving from old system
    # Switch to: return new_result  # When confidence is high
```

**When to use**: Critical paths where correctness must be verified before cutover.

## Deprecation Strategy

### Compulsory Deprecation
- **Trigger**: Security vulnerability, compliance violation, breaking dependency
- **Timeline**: Fixed deadline, no extensions
- **Communication**: CRITICAL alert, mandatory migration guide
- **Enforcement**: Hard removal at deadline, no backward compatibility

### Advisory Deprecation
- **Trigger**: Tech debt, better alternative available, maintenance burden
- **Timeline**: Soft timeline, warnings for N releases
- **Communication**: Deprecation notice in changelog, migration guide
- **Enforcement**: Gradual — warnings → errors → removal over 2-3 releases

### Deprecation Checklist

For each deprecated API:
- [ ] Sunset date documented
- [ ] Migration path documented with code examples
- [ ] Replacement API available and tested
- [ ] All internal consumers migrated
- [ ] Deprecation warning emitted at runtime
- [ ] Changelog entry with migration guide

## Migration Playbook Template

```markdown
## Migration: [Old Thing] → [New Thing]

### Scope
- Files affected: [list]
- Endpoints affected: [list]
- Database changes: [yes/no]

### Steps
1. [ ] Add adapter/bridge layer
2. [ ] Migrate consumer A
3. [ ] Migrate consumer B
4. [ ] Run parallel validation (N days)
5. [ ] Cut over to new implementation
6. [ ] Remove old code + adapter

### Rollback
At each step, rollback = revert the commit. No manual cleanup needed.

### Verification
- [ ] All existing tests pass after each step
- [ ] New tests cover the migration path
- [ ] Performance baseline maintained
```

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "We'll migrate when we have time" | You'll never have time. Schedule it or it won't happen. |
| "The old code still works, why change it?" | Working code with known vulnerabilities or unmaintained dependencies is a ticking bomb. |
| "Big-bang migration is faster" | Big-bang migrations fail big. Incremental migration lets you catch issues early. |
| "We can maintain both versions indefinitely" | Two versions means double the maintenance, testing, and documentation. Set a sunset date. |
