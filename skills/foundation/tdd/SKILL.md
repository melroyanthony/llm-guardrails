---
name: tdd
description: |
  Test-Driven Development workflow: RED → GREEN → REFACTOR.
  Write failing tests first, make them pass with minimal code, then refactor. Enforces 80%+ coverage.
  Use when implementing features that require test-driven development.
  Triggers on: "TDD", "test first", "red green refactor", "write tests first".
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Test-Driven Development (TDD)

## Seams — where tests go

A **seam** is the public boundary you test at. Before writing any test, list the seams under test and confirm them with the user when ambiguous. Prefer behavior through public interfaces over implementation-coupled tests. For deeper anti-patterns (tautological tests, horizontal slicing), see also `engineering/codebase-design` (seam vocabulary).

## The TDD Cycle

### 1. RED — Write a Failing Test
- Write ONE test that describes the desired behavior **at an agreed seam**
- Run it — it MUST fail (if it passes, the test is wrong or the feature already exists)
- The test should be specific and describe expected input/output
- Name the test descriptively: `test_should_return_404_when_user_not_found`

### 2. GREEN — Make It Pass
- Write the MINIMUM code to make the test pass
- Do not optimize, do not refactor, do not add extras
- Resist the urge to write "good" code — just make it work
- Run the test — it MUST pass

### 3. REFACTOR — Clean Up
- Now improve the code without changing behavior
- Remove duplication, improve naming, extract helpers
- Run ALL tests after each refactoring step — they MUST still pass
- Only refactor when tests are green

## Rules
1. **Never write production code without a failing test first**
2. **Write only enough test to fail** (compilation failure counts)
3. **Write only enough code to pass the failing test**
4. **Refactor only when all tests pass**
5. **Each cycle should take 2-5 minutes** (if longer, the step is too big)

## Coverage Targets

| Code Category | Minimum Coverage |
|---------------|-----------------|
| Business logic | 80% |
| API endpoints | 90% |
| Auth/Security | 100% |
| Financial/Payment | 100% |
| Utility/Helper | 70% |
| UI Components | 60% |

## Testing Patterns

### Python (pytest)

```python
# RED: Write the test first
def test_create_user_returns_user_with_id():
    user = create_user(name="Alice", email="alice@example.com")
    assert user.id is not None
    assert user.name == "Alice"
    assert user.email == "alice@example.com"

# GREEN: Minimal implementation
def create_user(name: str, email: str) -> User:
    return User(id=uuid4(), name=name, email=email)
```

### TypeScript (Vitest)

```typescript
// RED: Write the test first
test('createUser returns user with id', () => {
  const user = createUser({ name: 'Alice', email: 'alice@example.com' });
  expect(user.id).toBeDefined();
  expect(user.name).toBe('Alice');
  expect(user.email).toBe('alice@example.com');
});

// GREEN: Minimal implementation
function createUser(input: CreateUserInput): User {
  return { id: crypto.randomUUID(), ...input };
}
```

## Anti-Horizontal-Slice Rule

**DO NOT write all tests first, then all implementation.** This is the most common TDD failure mode. When you write 10 tests before any implementation, you outrun your headlights — committing to test structure before understanding the implementation. Each RED→GREEN→REFACTOR cycle should be ONE test at a time.

```
❌ WRONG (horizontal slices):
  Write test_create → Write test_read → Write test_update → Write test_delete
  Then implement create → read → update → delete

✅ RIGHT (vertical slices):
  Write test_create → Implement create → Refactor
  Write test_read → Implement read → Refactor
  Write test_update → Implement update → Refactor
  Write test_delete → Implement delete → Refactor
```

## Mocking Discipline

### Rule: Mock at System Boundaries Only

Do NOT mock your own classes, modules, or functions. Only mock external dependencies that cross system boundaries.

| Mock This (System Boundary) | Do NOT Mock This (Internal) |
|---|---|
| External API calls (HTTP clients) | Your own service classes |
| Database connections (in unit tests) | Your own utility functions |
| File system I/O | Your own data transformations |
| Third-party SDKs (Stripe, AWS) | Your own validators |
| Time/clock (for deterministic tests) | Your own models |

### Verify Through Interface, Not External Means

```python
# ❌ WRONG: Testing through implementation details
def test_create_user():
    create_user(name="Alice", email="alice@example.com")
    # Verifying via direct DB query — couples test to storage
    row = db.execute("SELECT * FROM users WHERE name = ?", ("Alice",)).fetchone()
    assert row is not None

# ✅ RIGHT: Testing through the public interface
def test_create_user():
    created = create_user(name="Alice", email="alice@example.com")
    retrieved = get_user(created.id)
    assert retrieved.name == "Alice"
```

If you need to bypass the interface to verify something, the interface is incomplete — add a method rather than peeking behind it.

## Anti-Patterns to Avoid
- Writing tests after code (that's "test-after", not TDD)
- Writing multiple tests before making any pass (horizontal slicing)
- Making large jumps in complexity between cycles
- Skipping the refactor step
- Testing implementation details instead of behavior
- Tautological tests: the assertion recomputes the expected value the way the code does, so it cannot disagree with the implementation. Expected values come from a known-good literal, a worked example, or the spec (adapted from Matt Pocock's `tdd` skill, MIT, https://github.com/mattpocock/skills)
- Writing tests that depend on execution order
- Mocking your own classes instead of only system boundaries

## Anti-Rationalization Guide

Common excuses agents use to skip TDD — and why they are wrong:

| Rationalization | Reality |
|---|---|
| "I'll write tests after the implementation" | That's test-after, not TDD. You lose the design feedback loop — tests written after code confirm what you built, not what you should have built. |
| "It's faster to write everything first and test at the end" | It *feels* faster until something breaks. A bug in function A that cascades to B, C, D takes 10x longer to diagnose than catching it when A was the only moving part. |
| "This function is too simple to test" | If it's too simple to test, it's too simple to break — write the test in 30 seconds and move on. If you can't write it in 30 seconds, it's not as simple as you think. |
| "I'll just manually verify it works" | Manual verification is non-repeatable. The next change will break it silently, and nobody will know until production. |
| "The coverage target is unrealistic for this timeline" | Reduce scope, not coverage. Fewer features with 80% coverage beats many features with 20% coverage every time. |
| "Mocking is too complex for this test" | If mocking is complex, the code has too many dependencies. That's the design feedback TDD gives you — simplify the interface. |

## When to Use TDD
- **Always**: Business logic, data transformations, API endpoints, validation rules
- **Sometimes**: UI components (use for complex interactions, skip for simple rendering)
- **Rarely**: Configuration, simple CRUD wrappers, generated code
