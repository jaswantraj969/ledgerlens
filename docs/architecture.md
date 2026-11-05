# Architecture

Diagrams describe the intended design. Implementation status is tracked in [progress/TASKS.md](progress/TASKS.md).

## System context
```mermaid
flowchart LR
  AP[Bookkeeping / AP staff] --> LL[LedgerLens]
  Dev[Developer] -->|REST + API key| LL
  Owner[Project owner] -->|evaluation reports| LL
  LL -.optional.-> LLM[Ollama or hosted LLM]
  LL -->|signed webhooks| Ext[Customer systems]
```

## Containers
```mermaid
flowchart TB
  FE[Frontend: React] --> API[API: FastAPI]
  API --> PG[(PostgreSQL)]
  API --> R[(Redis)]
  API --> FS[(Document storage)]
  W[Worker: RQ] --> R
  W --> PG
  W --> FS
  W -.optional.-> O[Ollama]
```

## Pipeline
```mermaid
sequenceDiagram
  participant C as Client
  participant A as API
  participant Q as Redis
  participant W as Worker
  participant D as PostgreSQL
  C->>A: upload
  A->>A: validate, sha256, dedup per org
  A->>D: store document, job=queued
  A->>Q: enqueue
  A-->>C: document and job ids
  Q->>W: job
  W->>D: parse, extract, verify, score (each keyed by document, step, version)
  W->>D: route to ready_for_review or completed
  C->>A: review decisions
  C->>A: export
```

## Data model
```mermaid
erDiagram
  organizations ||--o{ users : has
  organizations ||--o{ documents : owns
  users ||--o{ api_keys : holds
  documents ||--o{ pages : has
  documents ||--o{ jobs : runs
  documents ||--o{ extraction_runs : produces
  extraction_runs ||--o{ fields : yields
  fields ||--o{ field_evidence : cites
  fields ||--o{ validations : checked_by
  fields ||--o{ review_decisions : reviewed_in
  organizations ||--o{ webhooks : configures
  webhooks ||--o{ webhook_deliveries : sends
```

## Trust boundaries
```mermaid
flowchart LR
  subgraph Untrusted
    U[Uploaded files and their text]
    B[Browser]
  end
  subgraph Application
    API
    W[Worker]
  end
  subgraph Data
    PG[(PostgreSQL)]
    FS[(Storage)]
  end
  subgraph External
    L[Hosted LLM, optional]
  end
  B --> API
  U --> API
  API --> PG
  W --> PG
  W --> FS
  W -.document text leaves the host.-> L
```
Document text is treated as data, never as instructions. The LLM has no tools, and its output is schema-validated and checked against source evidence.
