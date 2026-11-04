# System Design Approach

How to tackle system design in time-constrained scenarios.

## The Three-Phase Framework

### Phase 1: Draw the System Boundary (5 min)
Define what's in scope and what's not.

```
Questions to ask:
- What are the core use cases?
- What's the expected scale (users, requests, data)?
- What are the constraints (time, technology, team)?
- What can we defer to "future work"?
```

**Output**: A box labeled "System" with inputs/outputs identified.

### Phase 2: Decompose into Components (10 min)
Break the system into 5-6 major building blocks.

```
Standard components to consider:
- Clients (web, mobile, API consumers)
- Load balancer / API gateway
- Application servers (stateless)
- Cache layer (Redis, in-memory)
- Database (primary storage)
- Background workers (async tasks)
- External services (auth, payments, notifications)
```

**Output**: Block diagram with labeled components.

### Phase 3: Discuss Interactions (15 min)
Explain how data flows between components.

```
For each interaction, consider:
- Protocol (HTTP, gRPC, WebSocket, message queue)
- Sync vs async
- Data format (JSON, protobuf)
- Failure modes and handling
```

**Output**: Arrows with annotations showing data flow.

---

## The 50,000 Foot Rule

**Start high, go deep selectively.**

```
Wrong approach:
"Let me explain how we'd implement the video transcoding pipeline..."
(Too deep, too early)

Right approach:
"At a high level, we have clients, an API layer, storage, and processing.
Which area would you like me to dive deeper on?"
(Gives overview, invites collaboration)
```

### Depth Triggers
Go deeper only when:
- Interviewer/stakeholder asks
- It's a core differentiator
- There's a non-obvious trade-off to discuss

---

## Anti-Patterns to Avoid

### 1. Buzzword Overreliance
```
Bad: "We'll use Kafka for event streaming, Redis for caching,
      and Kubernetes for orchestration."

Why it fails:
- Invites "why Kafka vs RabbitMQ?" questions you may not answer well
- Shows technology-first thinking instead of problem-first

Better: "We need async processing for [reason]. A message queue
        like Kafka or RabbitMQ would work. Given our scale of X
        messages/sec, I'd lean toward [choice] because [reason]."
```

**Rule**: Only mention technologies you can justify and defend.

### 2. Premature Solutions
```
Bad: Immediately jumping to "We'll use microservices with..."

Why it fails:
- Skips requirement gathering
- Shows you're pattern-matching, not thinking

Better:
1. "Let me understand the requirements first..."
2. "What's our expected scale?"
3. "Are there consistency requirements?"
4. "Now, given these constraints, here's my approach..."
```

**Rule**: Ask 3-5 clarifying questions before proposing solutions.

### 3. False Expertise
```
Bad: "I've worked extensively with distributed consensus algorithms..."
     (when you've only read about Raft once)

Why it fails:
- Experts will probe deeper
- Getting caught destroys credibility

Better: "I understand the concept of distributed consensus at a high
        level. For implementation, I'd rely on proven solutions like
        etcd or Zookeeper rather than rolling our own."
```

**Rule**: Honest boundaries build trust. Say "I'm not sure, but I'd approach it by..."

### 4. Over-Engineering
```
Bad: "We'll need sharding, read replicas, a CDN, rate limiting,
      circuit breakers, and a service mesh..."

Why it fails:
- Most challenges don't need all of this
- Shows you can't right-size solutions

Better: "For our scale of ~100 RPS, a single database with proper
        indexes is sufficient. If we grew 100x, we'd add read
        replicas first, then consider sharding."
```

**Rule**: Design for current needs with a clear scaling path.

---

## Clarifying Questions Checklist

Ask these before designing:

### Functional Requirements
- [ ] What are the core user actions?
- [ ] What data do we need to store?
- [ ] Are there real-time requirements?
- [ ] What are the read vs write patterns?

### Non-Functional Requirements
- [ ] Expected number of users?
- [ ] Requests per second (peak)?
- [ ] Data retention requirements?
- [ ] Latency expectations?
- [ ] Availability requirements (99.9%? 99.99%)?

### Constraints
- [ ] Time to build?
- [ ] Team size and expertise?
- [ ] Existing infrastructure?
- [ ] Budget constraints?

---

## Collaborative Exploration Mindset

### Frame as Discussion, Not Performance

```
Performance mode (avoid):
"Here's exactly how I would build this..."
(Rigid, defensive, closed to feedback)

Exploration mode (prefer):
"One approach would be X. Another option is Y.
Given our constraints, I'm leaning toward X because...
What aspects would you like me to elaborate on?"
(Flexible, open, invites dialogue)
```

### Acknowledge Trade-offs

```
Good signals:
- "The downside of this approach is..."
- "We're trading off X for Y here"
- "If requirements change to Z, we'd need to revisit this"

These show:
- Mature engineering thinking
- Awareness that no solution is perfect
- Ability to adapt when constraints change
```

### Handle Uncertainty Gracefully

```
When you don't know:
"I haven't worked with that specific technology, but based on
my understanding of similar systems, I'd expect it to..."

When you're unsure of the best approach:
"There are a few ways to solve this. Let me think through
the trade-offs... [pause and think visibly]"

When pushed on details you can't answer:
"That's getting into implementation details I'd want to
research more carefully. At the design level, the key
constraint is [X] and we'd need to validate [Y] approach."
```

---

## Time Management for Challenges

### 2-4 Hour Challenge
| Phase | Time | Focus |
|-------|------|-------|
| Requirements | 15 min | Clarify scope, identify MVP |
| High-level design | 20 min | Components, interactions |
| Detailed design | 30 min | API, database, key flows |
| Documentation | 20 min | ADRs, diagrams |
| **Buffer** | 10 min | Review, refinement |

### 45-Minute Interview
| Phase | Time | Focus |
|-------|------|-------|
| Clarify | 5 min | Requirements, constraints |
| High-level | 10 min | Components, boundaries |
| Deep dive | 20 min | 1-2 areas in detail |
| Trade-offs | 5 min | Alternatives, limitations |
| Q&A | 5 min | Address concerns |

---

## Summary: The Architect's Checklist

Before designing:
- [ ] Asked clarifying questions
- [ ] Understood scale requirements
- [ ] Identified core use cases
- [ ] Defined what's out of scope

While designing:
- [ ] Started at 50,000 ft
- [ ] Decomposed into 5-6 components
- [ ] Explained key interactions
- [ ] Discussed trade-offs explicitly

Avoided:
- [ ] Premature solutions
- [ ] Unjustified technology choices
- [ ] Over-engineering for hypothetical scale
- [ ] Claiming expertise I don't have
