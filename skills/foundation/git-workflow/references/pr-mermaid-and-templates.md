## Mermaid Diagram Types for PRs

### 1. Flowchart (Decision Logic)
```mermaid
flowchart TD
    A[Request] --> B{Authenticated?}
    B -->|Yes| C{Authorized?}
    B -->|No| D[401 Unauthorized]
    C -->|Yes| E[Process Request]
    C -->|No| F[403 Forbidden]
    E --> G[200 Success]
```

### 2. Sequence Diagram (API Flow)
```mermaid
sequenceDiagram
    actor U as User
    participant F as Frontend
    participant B as Backend
    participant DB as Database

    U->>F: Submit Form
    F->>B: POST /api/resource
    B->>B: Validate Input
    B->>DB: INSERT resource
    DB-->>B: Created
    B-->>F: 201 + resource
    F-->>U: Success Message
```

### 3. Entity Relationship (Database Changes)
```mermaid
erDiagram
    TABLE_A ||--o{ TABLE_B : "has many"
    TABLE_A {
        int id PK
        string name
    }
    TABLE_B {
        int id PK
        int a_id FK
        string value
    }
```

### 4. State Diagram (Status Transitions)
```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Pending: submit
    Pending --> Approved: approve
    Pending --> Rejected: reject
    Approved --> Published: publish
    Rejected --> Draft: revise
    Published --> [*]
```

### 5. C4 Container (Architecture Changes)
```mermaid
graph TB
    subgraph "System Boundary"
        F[Frontend<br/>Next.js]
        B[Backend<br/>FastAPI]
        DB[(Database<br/>PostgreSQL)]
        Q[Queue<br/>Redis]
    end

    U[User] --> F
    F --> B
    B --> DB
    B --> Q
```

