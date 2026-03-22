# PC2 v2.0 — Product Content Creator
## Detailed Requirements Document

**Version:** 2.0
**Date:** 2026-03-22
**Status:** Draft
**Target Clients:** The Home Depot (THD), SiteOne Landscape Supply
**Exclusions:** Athena DQ, CDI (separate builds)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [User Roles & Permissions](#2-user-roles--permissions)
3. [Application Architecture](#3-application-architecture)
4. [Database & Storage Architecture](#4-database--storage-architecture)
5. [Modular Pipeline Architecture](#5-modular-pipeline-architecture)
6. [AI/ML Model Integration Layer](#6-aiml-model-integration-layer)
7. [External System Integrations](#7-external-system-integrations)
8. [Human-in-the-Loop Framework (All Stages)](#8-human-in-the-loop-framework-all-stages)
9. [Per-Stage Confidence Scoring Engine](#9-per-stage-confidence-scoring-engine)
10. [Data Model](#10-data-model)
11. [Stage 1 — Raw Supplier Data Ingestion](#11-stage-1--raw-supplier-data-ingestion)
12. [Stage 2 — Categorisation](#12-stage-2--categorisation)
13. [Stage 3 — Deduplication](#13-stage-3--deduplication)
14. [Stage 4 — Enrichment](#14-stage-4--enrichment)
15. [Stage 5 — DIM Check + Validation](#15-stage-5--dim-check--validation)
16. [Stage 6 — Template Transformation](#16-stage-6--template-transformation)
17. [Stage 7 — Final Review + Publish](#17-stage-7--final-review--publish)
18. [Demo Scenario — Hardcoded Data Specification](#18-demo-scenario--hardcoded-data-specification)
19. [UI/UX Requirements — Content Team Experience](#19-uiux-requirements--content-team-experience)
20. [Non-Functional Requirements](#20-non-functional-requirements)
21. [Glossary](#21-glossary)

---

## 1. Project Overview

### 1.1 Purpose

PC2 v2.0 is an enterprise AI platform for end-to-end product item data processing. It takes raw, messy, incomplete product data from a supplier — in any format — and produces a clean, enriched, validated, retailer-formatted product record ready to publish to a retailer's PIM system.

### 1.2 Core Value Proposition

PC2 is not a raw LLM wrapper. Iksula's value is the orchestration and domain layer that sits around AI models:

| Iksula IP Layer | Description |
|---|---|
| Category-specific prompt libraries | Per retail taxonomy class, tuned for each retailer |
| Retail domain knowledge base | Attribute standards, picklists, value dictionaries |
| LLM + ML routing engine | Selects the right model per task (OCR, vision, text, classification) |
| Confidence scoring engine | Three-component composite score (source reliability, consistency, completeness) |
| Deduplication logic | Retail-trained item matching across name variants, model numbers, attributes |
| DIM validation rules | Per-category dimension/weight/format rules built from retailer compliance requirements |
| Retailer template mapping | Exact field mapping, value formatting, and export for SiteOne and THD |

### 1.3 Processing Pipeline

```
Raw Supplier Data → Ingestion → Categorisation → Deduplication → Enrichment → DIM Validation → Template Transformation → HIL Review → Publish
     Stage 1         Stage 2        Stage 3         Stage 4         Stage 5           Stage 6              Stage 7
```

A single product record object accumulates data through all 7 stages. State is never reset between stages.

### 1.4 AI Simulation Strategy

All AI steps are simulated with `setTimeout` + hardcoded realistic outputs. Every AI output must display:
- Which model produced it (named model, e.g. "GPT-4o", "Iksula Vision v1.2")
- Which Iksula layer processed it
- What prompt template or rule was applied
- Confidence score + breakdown

**Named models used throughout the application:**

| Model ID | Purpose |
|---|---|
| Iksula OCR Engine v2 | PDF text extraction |
| GPT-4o | Copy generation, LLM inference |
| Iksula Vision v1.2 | Image/label analysis, visual attribute extraction |
| Iksula KB v3.1 | Knowledge base attribute lookup, picklist matching |
| Iksula Dedup Model v1.0 | Duplicate/variant detection |
| Iksula DIM Validator v2.3 | Dimension, unit, range, format validation |
| Iksula Enrichment — Irrigation v4 | Category-specific enrichment pipeline |
| Iksula Retail Taxonomy v4.2 | Taxonomy classification engine |

---

## 2. User Roles & Permissions

### 2.1 Role Definitions

| Role | Description | Capabilities |
|---|---|---|
| **Admin** | Manages platform operations | Upload supplier batches, manage template configs, monitor job health, view analytics, full read/write access |
| **Reviewer** | Domain expert for human-in-the-loop decisions | Work HIL queue, approve/edit/reject flagged fields, handle dedup decisions, view records |
| **Viewer** | Read-only consumer | View published records, download reports, export data |

### 2.2 Role Visibility

All three roles must be visible and selectable in the UI. The application should demonstrate role-based access control — different UI elements visible/enabled based on active role.

### 2.3 Role-Specific UI Restrictions

| Action | Admin | Reviewer | Viewer |
|---|---|---|---|
| Upload supplier data | Yes | No | No |
| Manage templates | Yes | No | No |
| View analytics dashboard | Yes | No | No |
| Monitor job health | Yes | No | No |
| Work HIL queue | Yes | Yes | No |
| Approve/Edit/Reject fields | Yes | Yes | No |
| Handle dedup decisions | Yes | Yes | No |
| View published records | Yes | Yes | Yes |
| Download reports/exports | Yes | Yes | Yes |

---

## 3. Application Architecture

### 3.1 Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | React 18 + Tailwind CSS | Component-based UI, rapid styling |
| **Backend** | Python FastAPI | ML/AI model integration, async processing, file handling |
| **Database** | Supabase (PostgreSQL 15 + pgvector) | Structured data + vector similarity for dedup/search |
| **Object Storage** | Supabase Storage (S3-compatible) | PDFs, images, CSVs, exported files |
| **Queue** | Supabase Edge Functions + pg_cron / Celery | Batch job processing, async model calls |
| **Auth** | Supabase Auth (Row-Level Security) | Role-based access, JWT tokens |
| **Realtime** | Supabase Realtime | Live progress updates during processing |
| **Cache** | Redis | Model response caching, session state |

### 3.2 Why React Alone Is Not Sufficient

A React SPA cannot handle:
- **File uploads & OCR processing** — PDFs and images must be received, stored, and processed server-side
- **AI/ML model orchestration** — calling multiple models (LLM, vision, OCR) requires server-side API key management, retry logic, rate limiting
- **Batch job processing** — processing 6+ items asynchronously requires a job queue, not browser-side setTimeout
- **Database operations** — product records, audit trails, vector embeddings need persistent server-side storage
- **Security** — API keys, model credentials, and supplier data cannot live in the browser

**Architecture decision:** Full-stack application with React frontend + Python FastAPI backend + Supabase for data/storage/auth.

### 3.3 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Tailwind)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Stage UI │ │ HIL Queue│ │ Batch Mgr│ │ Analytics│ │ Admin    │ │
│  │Components│ │ Views    │ │ Dashboard│ │ Charts   │ │ Config   │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │
│       └─────────────┴────────────┴─────────────┴────────────┘       │
│                              │ REST + WebSocket                     │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────────┐
│                     BACKEND (Python FastAPI)                        │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────────┐  │
│  │ Pipeline   │ │ Model      │ │ Integration│ │ Job Queue       │  │
│  │ Orchestr.  │ │ Registry   │ │ Gateway    │ │ Manager         │  │
│  │            │ │            │ │            │ │ (Celery/pg_cron)│  │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └────────┬────────┘  │
│        │              │              │                  │           │
│  ┌─────┴──────────────┴──────────────┴──────────────────┴────────┐  │
│  │                    Modular Stage Processors                    │  │
│  │  S1:Ingest │ S2:Classify │ S3:Dedup │ S4:Enrich │ S5:Validate│  │
│  │  S6:Transform │ S7:Review+Publish                             │  │
│  └───────────────────────────┬───────────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────────┐
│                     DATA LAYER (Supabase)                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐  │
│  │ PostgreSQL   │ │ pgvector     │ │ Object       │ │ Auth +    │  │
│  │ Product recs │ │ Embeddings   │ │ Storage      │ │ RLS       │  │
│  │ Audit trails │ │ Dedup index  │ │ PDFs/Images  │ │ JWT/Roles │  │
│  │ Job queue    │ │ Semantic     │ │ CSVs/Exports │ │           │  │
│  │ Templates    │ │ search       │ │              │ │           │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └───────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────────┐
│                 EXTERNAL SERVICES                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ OpenAI   │ │ Anthropic│ │ Custom   │ │ Retailer │ │ Supplier │  │
│  │ GPT-4o   │ │ Claude   │ │ Client   │ │ PIM APIs │ │ Portals  │  │
│  │          │ │          │ │ Models   │ │ THD/Site1│ │ Feeds    │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.4 State Architecture

**REQ-ARCH-001:** A single product record object accumulates data through all 7 stages. Persisted in Supabase PostgreSQL after each stage completes.

**REQ-ARCH-002:** State is never reset between stages. Each stage appends/modifies fields on the same record row.

**REQ-ARCH-003:** The product record must carry full provenance metadata per field — source, model, confidence, timestamp, human overrides — stored as JSONB columns.

**REQ-ARCH-004:** Frontend receives real-time stage progress updates via Supabase Realtime subscriptions (WebSocket).

### 3.5 Navigation Architecture

**REQ-NAV-001:** Top stepper bar showing all 7 stages (or fewer if pipeline is configured with stages disabled).

**REQ-NAV-002:** Active stage highlighted with blue indicator.

**REQ-NAV-003:** Users can navigate back to inspect earlier stages.

**REQ-NAV-004:** Locked fields (auto-approved) cannot be edited when navigating back.

**REQ-NAV-005:** Each stage badge shows status:
- **Complete** — green check icon
- **Active** — blue indicator
- **Pending** — grey indicator
- **Disabled** — hidden or struck through (if stage is toggled off in pipeline config)

### 3.6 Enterprise Transparency Bar

Every AI output panel must include:

| Element | Description |
|---|---|
| Model attribution | Which named Iksula/third-party/client model produced the value |
| Layer attribution | Which Iksula processing layer handled it |
| Prompt/rule reference | Which prompt template or validation rule was applied |
| Confidence score | Composite 0–100 score with breakdown into sub-components |

**Rationale:** The client must never wonder where any value came from. This is non-negotiable for enterprise trust.

### 3.7 Demo Mode vs Production Mode

**REQ-ARCH-005:** The application supports two runtime modes:

| Mode | Backend | Database | AI Models | Use Case |
|---|---|---|---|---|
| **Demo mode** | FastAPI with mock endpoints | Supabase with seeded demo data | `setTimeout` + hardcoded outputs | Sales demos, pitches |
| **Production mode** | FastAPI with real endpoints | Supabase with live data | Real model API calls | Client deployments |

Demo mode uses the same full architecture but with mock service implementations behind the same interfaces. This means the demo is architecturally identical to production — not a throwaway prototype.

---

## 4. Database & Storage Architecture

### 4.1 Why Supabase

| Requirement | Supabase Capability |
|---|---|
| Structured product records, audit trails | PostgreSQL 15 with JSONB for flexible attributes |
| Vector similarity for dedup & semantic search | pgvector extension — embeddings stored alongside relational data |
| File storage for PDFs, images, CSVs | S3-compatible Object Storage with signed URLs |
| Real-time progress updates | Supabase Realtime (WebSocket subscriptions on DB changes) |
| Role-based access control | Row-Level Security (RLS) policies per user role |
| Auth with JWT | Supabase Auth — integrates with enterprise SSO (SAML, OIDC) |
| Scalability | Managed infrastructure, connection pooling, read replicas |

### 4.2 Database Schema Overview

#### 4.2.1 Core Tables

**REQ-DB-001: `products` table**
```sql
products (
  id              UUID PRIMARY KEY,
  batch_id        UUID REFERENCES batches(id),
  client_id       UUID REFERENCES clients(id),
  pipeline_config UUID REFERENCES pipeline_configs(id),
  current_stage   INTEGER (1-7),
  status          ENUM (draft, processing, review, published, rejected),
  raw_data        JSONB,           -- Stage 1 extracted fields
  classified_data JSONB,           -- Stage 2 taxonomy assignment
  dedup_result    JSONB,           -- Stage 3 match outcome
  enriched_data   JSONB,           -- Stage 4 filled fields + copy
  validation_data JSONB,           -- Stage 5 DIM check results
  transformed_data JSONB,          -- Stage 6 retailer-mapped record
  final_record    JSONB,           -- Stage 7 published record
  field_provenance JSONB,          -- Per-field source/confidence/audit
  overall_confidence FLOAT,
  created_at      TIMESTAMPTZ,
  updated_at      TIMESTAMPTZ,
  published_at    TIMESTAMPTZ
)
```

**REQ-DB-002: `audit_trail` table**
```sql
audit_trail (
  id          UUID PRIMARY KEY,
  product_id  UUID REFERENCES products(id),
  field_name  VARCHAR,
  stage       INTEGER,
  action      ENUM (extracted, enriched, validated, transformed, approved, edited, rejected),
  old_value   TEXT,
  new_value   TEXT,
  actor_type  ENUM (system, model, human),
  actor_id    VARCHAR,             -- model name or user ID
  model_name  VARCHAR,             -- if actor is a model
  confidence  FLOAT,
  reason      TEXT,                -- for edits/rejections
  created_at  TIMESTAMPTZ
)
```

**REQ-DB-003: `batches` table**
```sql
batches (
  id           UUID PRIMARY KEY,
  client_id    UUID REFERENCES clients(id),
  file_name    VARCHAR,
  file_path    VARCHAR,            -- Supabase Storage path
  file_type    ENUM (pdf, csv, xlsx, image, api_feed),
  item_count   INTEGER,
  status       ENUM (queued, processing, complete, failed),
  error_message TEXT,
  created_by   UUID REFERENCES users(id),
  created_at   TIMESTAMPTZ,
  completed_at TIMESTAMPTZ
)
```

**REQ-DB-004: `clients` table**
```sql
clients (
  id                UUID PRIMARY KEY,
  name              VARCHAR,        -- e.g. "SiteOne", "THD"
  pipeline_config   UUID REFERENCES pipeline_configs(id),
  taxonomy_version  VARCHAR,
  template_version  VARCHAR,
  active_models     JSONB,          -- client-specific model overrides
  created_at        TIMESTAMPTZ
)
```

#### 4.2.2 Vector & Embedding Tables

**REQ-DB-005: `product_embeddings` table**
```sql
product_embeddings (
  id           UUID PRIMARY KEY,
  product_id   UUID REFERENCES products(id),
  embedding    VECTOR(1536),       -- pgvector column
  embedding_model VARCHAR,          -- e.g. "text-embedding-3-small"
  text_source  TEXT,                -- the text that was embedded
  created_at   TIMESTAMPTZ
)

-- Indexes for fast similarity search
CREATE INDEX ON product_embeddings USING ivfflat (embedding vector_cosine_ops);
```

**REQ-DB-006: `image_hashes` table**
```sql
image_hashes (
  id           UUID PRIMARY KEY,
  product_id   UUID REFERENCES products(id),
  hash_type    ENUM (perceptual, average, difference),
  hash_value   VARCHAR,
  image_path   VARCHAR,            -- Supabase Storage path
  created_at   TIMESTAMPTZ
)
```

#### 4.2.3 Configuration Tables

**REQ-DB-007: `pipeline_configs` table**
```sql
pipeline_configs (
  id              UUID PRIMARY KEY,
  client_id       UUID REFERENCES clients(id),
  name            VARCHAR,
  stages_enabled  JSONB,           -- e.g. {"1": true, "2": true, "3": false, ...}
  stage_order     INTEGER[],       -- custom stage ordering
  stage_configs   JSONB,           -- per-stage configuration overrides
  created_at      TIMESTAMPTZ,
  updated_at      TIMESTAMPTZ
)
```

**REQ-DB-008: `model_registry` table**
```sql
model_registry (
  id              UUID PRIMARY KEY,
  model_name      VARCHAR,         -- e.g. "GPT-4o", "Client Custom OCR v1"
  model_type      ENUM (llm, vision, ocr, embedding, classification, custom),
  provider        ENUM (iksula, openai, anthropic, google, client_custom),
  endpoint_url    VARCHAR,
  api_key_ref     VARCHAR,         -- reference to secret store, NOT the key itself
  capabilities    JSONB,           -- what tasks this model can perform
  default_for     JSONB,           -- which stages/tasks this model is default for
  is_active       BOOLEAN,
  added_by        ENUM (iksula, client),
  client_id       UUID REFERENCES clients(id),  -- NULL for Iksula-provided models
  created_at      TIMESTAMPTZ
)
```

**REQ-DB-009: `retailer_templates` table**
```sql
retailer_templates (
  id              UUID PRIMARY KEY,
  client_id       UUID REFERENCES clients(id),
  template_name   VARCHAR,         -- e.g. "SiteOne Template v2.4"
  version         VARCHAR,
  field_mappings  JSONB,           -- PC2 field → retailer field mapping
  value_transforms JSONB,          -- transformation rules per field
  mandatory_fields JSONB,
  char_limits     JSONB,
  export_formats  VARCHAR[],       -- ['csv', 'xml', 'json']
  last_updated    TIMESTAMPTZ,
  maintained_by   VARCHAR          -- "Iksula" or client name
)
```

### 4.3 Object Storage Structure

```
supabase-storage/
├── uploads/
│   ├── {client_id}/
│   │   ├── pdfs/          -- Uploaded spec sheets
│   │   ├── images/        -- Product images, labels
│   │   ├── csvs/          -- Supplier spreadsheets
│   │   └── api_feeds/     -- Cached API feed snapshots
├── processed/
│   ├── {client_id}/
│   │   ├── ocr_output/    -- Raw OCR text output
│   │   ├── thumbnails/    -- Generated image thumbnails
│   │   └── crops/         -- Image crops for HIL source snippets
├── exports/
│   ├── {client_id}/
│   │   ├── csv/           -- Exported retailer CSVs
│   │   ├── xml/           -- Exported retailer XML
│   │   └── json/          -- Exported retailer JSON
└── templates/
    ├── siteone/           -- SiteOne template definitions
    └── thd/               -- THD template definitions
```

### 4.4 Data Retention & Compliance

**REQ-DB-010:** All product records and audit trails are retained indefinitely (configurable per client).

**REQ-DB-011:** Uploaded files are retained for 90 days after processing (configurable).

**REQ-DB-012:** Supabase RLS policies enforce that:
- Admins see all data for their client
- Reviewers see only records assigned to their queue
- Viewers see only published records

---

## 5. Modular Pipeline Architecture

### 5.1 Objective

The 7-stage pipeline must be modular — each stage is an independently deployable, configurable, and toggleable processing unit. Clients can activate only the stages they need.

### 5.2 Why Modularity Matters

| Scenario | Pipeline Configuration |
|---|---|
| Client already has categorisation in their PIM | Disable Stage 2, use their existing taxonomy |
| Client has no dedup needs (single supplier) | Disable Stage 3 |
| Client only needs enrichment + validation | Enable Stages 1, 4, 5, 7 only |
| Client wants to add custom processing between stages | Insert custom stage via plugin |
| Client wants different models per stage | Override model assignment per stage |

### 5.3 Functional Requirements

#### 5.3.1 Stage Toggle

**REQ-MOD-001:** Each of the 7 stages can be independently enabled or disabled per client via `pipeline_configs.stages_enabled`.

**REQ-MOD-002:** When a stage is disabled:
- It is skipped in processing — the pipeline routes directly to the next enabled stage
- It is hidden or greyed out in the stepper UI
- Its output fields use defaults or pass-through values from the previous stage

**REQ-MOD-003:** Certain stage dependencies must be enforced:
- Stage 1 (Ingestion) is always required — cannot be disabled
- Stage 7 (Review + Publish) is always required — cannot be disabled
- Stage 5 (Validation) cannot be enabled without Stage 4 (Enrichment) — validation needs enriched data
- All other stages are independently toggleable

#### 5.3.2 Stage Interface Contract

**REQ-MOD-004:** Every stage processor implements a standard interface:

```python
class StageProcessor(ABC):
    """Base interface for all pipeline stage processors."""

    @abstractmethod
    async def process(self, product: ProductRecord, config: StageConfig) -> StageResult:
        """Process a product record through this stage."""
        pass

    @abstractmethod
    def validate_input(self, product: ProductRecord) -> ValidationResult:
        """Check that required input fields are present."""
        pass

    @abstractmethod
    def get_required_models(self) -> list[ModelRequirement]:
        """Declare which AI models this stage needs."""
        pass

    @abstractmethod
    def get_output_fields(self) -> list[FieldSpec]:
        """Declare which fields this stage produces."""
        pass
```

**REQ-MOD-005:** Each stage declares:
- **Input contract** — which fields it requires from previous stages
- **Output contract** — which fields it produces
- **Model requirements** — which AI models it needs (resolved from Model Registry)
- **Configuration schema** — what per-stage settings are available

#### 5.3.3 Pipeline Orchestrator

**REQ-MOD-006:** The Pipeline Orchestrator:
- Reads the client's `pipeline_config` to determine active stages and order
- Validates that stage dependencies are satisfied
- Executes stages sequentially (or parallelises independent stages where possible)
- Routes the product record from stage to stage, skipping disabled stages
- Persists the product record to Supabase after each stage completes
- Emits real-time progress events via Supabase Realtime

**REQ-MOD-007:** Pipeline configuration is per-client but can be overridden per-batch (e.g. a specific batch might skip dedup because the client knows these are all new items).

#### 5.3.4 Custom Stage Plugin

**REQ-MOD-008:** Clients can register custom stages that plug into the pipeline:
- Custom stage implements the `StageProcessor` interface
- Assigned a position in the pipeline (e.g. "after Stage 4, before Stage 5")
- Has access to the same product record and model registry
- Example: a client adds a "Compliance Check" stage between Enrichment and DIM Validation

### 5.4 Pipeline Configuration Examples

**SiteOne — Full pipeline:**
```json
{
  "stages_enabled": { "1": true, "2": true, "3": true, "4": true, "5": true, "6": true, "7": true },
  "stage_order": [1, 2, 3, 4, 5, 6, 7]
}
```

**THD — No dedup (managed externally):**
```json
{
  "stages_enabled": { "1": true, "2": true, "3": false, "4": true, "5": true, "6": true, "7": true },
  "stage_order": [1, 2, 4, 5, 6, 7]
}
```

**Small supplier — Enrichment + validation only:**
```json
{
  "stages_enabled": { "1": true, "2": false, "3": false, "4": true, "5": true, "6": false, "7": true },
  "stage_order": [1, 4, 5, 7]
}
```

---

## 6. AI/ML Model Integration Layer

### 6.1 Objective

Provide a unified abstraction for integrating Iksula models, third-party AI services (OpenAI, Anthropic, Google), and client-provided custom models — all behind a single interface. Any model can be swapped, added, or replaced without changing stage logic.

### 6.2 Why This Matters

| Without model abstraction | With model abstraction |
|---|---|
| Stage code hardcodes `openai.chat.completions.create()` | Stage code calls `model_registry.invoke("llm", task="copy_generation")` |
| Switching from GPT-4o to Claude requires code changes | Switching is a config change in the model registry |
| Client cannot add their own models | Client registers model endpoint, it's available to all stages |
| No fallback if a model is down | Registry supports fallback chains |

### 6.3 Functional Requirements

#### 6.3.1 Model Registry

**REQ-MODEL-001:** Central model registry (stored in `model_registry` table) tracks all available models.

**REQ-MODEL-002:** Each model entry specifies:

| Field | Description |
|---|---|
| `model_name` | Display name (e.g. "GPT-4o", "Client Custom OCR v1") |
| `model_type` | Category: `llm`, `vision`, `ocr`, `embedding`, `classification`, `custom` |
| `provider` | Who provides it: `iksula`, `openai`, `anthropic`, `google`, `client_custom` |
| `endpoint_url` | API endpoint (for custom models) |
| `api_key_ref` | Reference to secret store — never stores the key directly |
| `capabilities` | What tasks this model can perform (e.g. `["copy_generation", "attribute_inference"]`) |
| `default_for` | Which stages/tasks this model is the default for |
| `is_active` | Whether the model is currently available |

#### 6.3.2 Model Adapter Interface

**REQ-MODEL-003:** Every model — Iksula, third-party, or client-provided — is accessed through a standard adapter:

```python
class ModelAdapter(ABC):
    """Unified interface for all AI/ML models."""

    @abstractmethod
    async def invoke(self, input: ModelInput) -> ModelOutput:
        """Send input to the model and return structured output."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the model endpoint is responsive."""
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """Return the list of tasks this model can perform."""
        pass
```

**REQ-MODEL-004:** Built-in adapters for:

| Adapter | Models Supported |
|---|---|
| `OpenAIAdapter` | GPT-4o, GPT-4-turbo, text-embedding-3-small/large |
| `AnthropicAdapter` | Claude Sonnet 4, Claude Opus 4 |
| `IksulaOCRAdapter` | Iksula OCR Engine v2 (internal service) |
| `IksulaVisionAdapter` | Iksula Vision v1.2 (internal service) |
| `IksulaKBAdapter` | Iksula KB v3.1 (knowledge base lookup) |
| `GenericRESTAdapter` | Any model with a REST API (for client custom models) |
| `HuggingFaceAdapter` | HuggingFace Inference API models |

#### 6.3.3 Client Custom Model Registration

**REQ-MODEL-005:** Clients can register their own models via Admin UI or API:

| Step | Description |
|---|---|
| 1. Register | Client provides: model name, type, endpoint URL, auth method |
| 2. Test | System runs a health check and test invocation |
| 3. Map | Client maps the model to specific stages/tasks (e.g. "use my OCR for Stage 1") |
| 4. Activate | Model becomes available in the model registry for that client |

**REQ-MODEL-006:** Client models can:
- **Replace** an Iksula default model for specific tasks (e.g. client's own OCR replaces Iksula OCR)
- **Augment** the pipeline by adding capabilities (e.g. client adds a brand-detection model)
- **Run alongside** Iksula models for comparison/validation

**REQ-MODEL-007:** The enterprise transparency bar always shows which model produced each output — including client-provided models. Attribution: "Client Custom OCR v1 (provided by [client name])".

#### 6.3.4 Model Routing & Fallback

**REQ-MODEL-008:** The Model Router selects which model to use for each task based on:
1. Client-specific overrides (if the client has mapped a custom model to this task)
2. Stage-specific defaults (e.g. Stage 4 copy generation defaults to GPT-4o)
3. Model capabilities (match task requirements to model capabilities)
4. Availability (skip models that fail health check)

**REQ-MODEL-009:** Fallback chains — if the primary model fails or times out:
```
Primary: Client Custom OCR v1
  → Fallback 1: Iksula OCR Engine v2
    → Fallback 2: GPT-4o (vision mode for OCR)
      → Fail: Route to HIL for manual entry
```

**REQ-MODEL-010:** All model invocations are logged:

| Log Field | Description |
|---|---|
| Model name | Which model was called |
| Task | What task was requested |
| Latency | Response time in ms |
| Token usage | Input/output tokens (for LLMs) |
| Cost | Estimated cost per call |
| Success/failure | Whether the call succeeded |
| Fallback used | Whether a fallback model was invoked |

#### 6.3.5 Prompt Template Management

**REQ-MODEL-011:** Prompt templates are versioned and stored in the database:

```python
prompt_templates (
  id              UUID PRIMARY KEY,
  template_name   VARCHAR,         -- e.g. "Iksula Copy Prompt — Irrigation Controllers v3.0"
  model_type      ENUM (llm, vision),
  category_class  VARCHAR,         -- e.g. "Smart Controllers"
  retailer        VARCHAR,         -- e.g. "SiteOne"
  template_text   TEXT,            -- The actual prompt with {{placeholders}}
  version         VARCHAR,
  is_active       BOOLEAN,
  created_at      TIMESTAMPTZ
)
```

**REQ-MODEL-012:** Prompt templates are:
- Category-specific (different prompt for Irrigation Controllers vs Power Tools)
- Retailer-specific (different tone/format for SiteOne vs THD)
- Versioned (can roll back to previous versions)
- Editable by Admin users via the UI

---

## 7. External System Integrations

### 7.1 Objective

PC2 must integrate with retailer PIM systems, supplier data portals, and external AI services — not exist as an isolated tool.

### 7.2 Integration Architecture

```
┌──────────────────────────────────────────────────┐
│               PC2 Integration Gateway            │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐  │
│  │ PIM        │ │ Supplier   │ │ AI Service   │  │
│  │ Connectors │ │ Connectors │ │ Connectors   │  │
│  └─────┬──────┘ └─────┬──────┘ └──────┬───────┘  │
└────────┼──────────────┼───────────────┼──────────┘
         │              │               │
    ┌────┴────┐    ┌────┴────┐    ┌─────┴─────┐
    │Retailer │    │Supplier │    │AI/ML      │
    │PIM      │    │Portals  │    │Services   │
    │Systems  │    │& Feeds  │    │           │
    └─────────┘    └─────────┘    └───────────┘
```

### 7.3 PIM Integration

**REQ-INT-001:** PC2 integrates with retailer PIM systems for publishing records:

| Retailer | PIM System | Integration Method | Status |
|---|---|---|---|
| SiteOne | SiteOne PIM | REST API push | Primary target |
| THD | THD Item Management | Batch file upload (CSV/XML) + API | Primary target |

**REQ-INT-002:** PIM integration supports:
- **Push to staging** — publish record to retailer's staging/QA catalog
- **Push to production** — publish record to live catalog (requires additional approval)
- **Pull existing catalog** — import existing catalog data for dedup matching (Stage 3)
- **Sync status** — track whether the record was accepted/rejected by the PIM

**REQ-INT-003:** PIM connector is configurable per retailer template. Each template defines:
- API endpoint or file drop location
- Authentication method (API key, OAuth2, SFTP credentials)
- Required field format and validation rules
- Submission batch size limits

### 7.4 Supplier Portal Integration

**REQ-INT-004:** PC2 connects to supplier data sources:

| Source Type | Description | Integration Method |
|---|---|---|
| Supplier API feeds | Real-time product data from supplier systems | REST/SOAP API polling |
| Supplier portals | Web portals where suppliers upload product data | Webhook receiver or scheduled scrape |
| EDI feeds | Electronic Data Interchange for large suppliers | EDI parser (ANSI X12 / EDIFACT) |
| Email attachments | Suppliers who send spec sheets via email | Email inbox monitor + file extraction |
| FTP/SFTP drops | Suppliers who drop files to a shared folder | Scheduled file watcher |

**REQ-INT-005:** Supplier portal connector supports:
- Auto-detection of file format (PDF, CSV, XLSX, XML, JSON)
- Scheduled feed polling (configurable interval)
- Dedup against recent imports to avoid reprocessing
- Notification to Admin when new supplier data arrives

### 7.5 AI/ML Service Integration

**REQ-INT-006:** PC2 integrates with external AI services through the Model Registry (Section 6):

| Service | Models | Used For |
|---|---|---|
| OpenAI | GPT-4o, GPT-4-turbo, text-embedding-3 | Copy generation, inference, embeddings |
| Anthropic | Claude Sonnet/Opus | Copy generation, classification, reasoning |
| Google Cloud | Vision AI, Document AI | OCR, image analysis |
| AWS | Textract, Rekognition | OCR fallback, image analysis fallback |
| HuggingFace | Open-source models | Embeddings, classification, custom fine-tuned models |
| Custom endpoints | Client-hosted models | Any task the client has built a model for |

**REQ-INT-007:** All external service calls go through the Integration Gateway which provides:
- Rate limiting per service
- Cost tracking per call
- Retry with exponential backoff
- Circuit breaker (disable a service if it's consistently failing)
- Request/response logging for audit

### 7.6 Webhook & Event System

**REQ-INT-008:** PC2 emits events that external systems can subscribe to:

| Event | Trigger | Payload |
|---|---|---|
| `batch.uploaded` | New batch uploaded | batch_id, item_count, client_id |
| `product.stage_complete` | A product completes a pipeline stage | product_id, stage, status |
| `product.needs_review` | A product enters the HIL queue | product_id, flagged_fields |
| `product.published` | A product is published | product_id, retailer, export_format |
| `model.fallback_triggered` | Primary model failed, fallback used | model_name, fallback_model, task |

**REQ-INT-009:** Webhook delivery supports:
- Configurable endpoint URLs per client
- HMAC signature verification
- Retry on failure (3 attempts with backoff)
- Event log for debugging

---

## 7A. External Data Quality (DQ) Integration

### 7A.1 Objective

PC2 connects to Iksula's separate **Athena DQ** tool at the output of each pipeline stage. DQ runs quality checks on the stage output before the record proceeds. Manual override is allowed — a human can bypass DQ findings when they have context the automated rules don't.

### 7A.2 Design Principle

**DQ is an external system, not built into PC2.** PC2 sends stage output to the DQ API, receives pass/fail/warning results, and displays them inline. PC2 does not replicate DQ logic — it consumes DQ results.

### 7A.3 Integration Architecture

```
┌──────────┐     ┌────────────┐     ┌──────────┐     ┌──────────────┐
│ Stage N  │ ──► │ DQ API     │ ──► │ DQ       │ ──► │ PC2 displays │
│ output   │     │ call       │     │ results  │     │ DQ results   │
└──────────┘     └────────────┘     └──────────┘     └──────┬───────┘
                                                            │
                                                     ┌──────┴───────┐
                                                     │ Human review │
                                                     │ Override OK  │
                                                     └──────────────┘
```

### 7A.4 Functional Requirements

**REQ-DQ-001:** After each stage completes processing, PC2 sends the stage output to the Athena DQ API endpoint.

**REQ-DQ-002:** The DQ API call includes:
- Product record (current state)
- Stage number that just completed
- Client ID and pipeline config
- Field-level provenance metadata

**REQ-DQ-003:** The DQ API returns per-field results:

| DQ Result | Meaning | PC2 Action |
|---|---|---|
| Pass | Field passes all DQ rules | Green DQ badge on field |
| Warning | Field has quality concern but is not blocking | Amber DQ badge, shown to reviewer |
| Fail | Field fails DQ rules | Red DQ badge, blocks progression (unless overridden) |
| Skip | DQ has no rule for this field | No badge shown |

**REQ-DQ-004:** DQ results are displayed inline on the stage output, alongside the confidence score:

```
Field: Material
Value: ABS Plastic
Confidence: 95% [green]
DQ Check: Pass [green] — "Value matches DQ material dictionary"
```

**REQ-DQ-005:** DQ failures are shown prominently and block stage progression by default:

```
Field: Shipping Weight
Value: 0.36 kg
DQ Check: FAIL [red] — "Weight below minimum threshold for this category (min 0.5 kg)"
[Override with reason] [Edit value]
```

**REQ-DQ-006: Manual Override**

When DQ flags a field as fail or warning, the human can override:
- Click "Override" button
- Select override reason from list: "DQ rule not applicable", "Supplier confirmed correct", "Exception for this product", "DQ rule needs updating"
- Add optional free-text note
- Field proceeds with status "DQ overridden" + audit trail entry

**REQ-DQ-007:** Override audit trail:
```json
{
  "field": "shipping_weight",
  "dq_result": "fail",
  "dq_rule": "MIN_WEIGHT_CHECK_v2.1",
  "dq_message": "Weight below minimum for category",
  "override_by": "reviewer@iksula.com",
  "override_reason": "Supplier confirmed correct",
  "override_note": "Lightweight electronic unit — confirmed with Orbit spec sheet",
  "timestamp": "2026-03-22T14:35:00Z"
}
```

**REQ-DQ-008:** DQ is configurable per stage in the pipeline config:

```json
{
  "dq_integration": {
    "enabled": true,
    "api_endpoint": "https://dq.iksula.com/api/v2/check",
    "stages_enabled": { "1": true, "2": true, "3": false, "4": true, "5": true, "6": true, "7": true },
    "block_on_fail": true,
    "allow_override": true,
    "timeout_ms": 5000,
    "fallback_on_timeout": "proceed_with_warning"
  }
}
```

**REQ-DQ-009:** If the DQ API is unavailable or times out, PC2 proceeds with a warning: "DQ check unavailable — proceeding without quality validation". This is logged in the audit trail.

**REQ-DQ-010:** Admin can view DQ check statistics: pass rate per stage, most common failures, override frequency, DQ rules that need updating.

---

## 8. Human-in-the-Loop Framework (All Stages)

### 8.1 Design Principle

**Every stage has human review built in — not just Stage 7.**

The previous architecture concentrated HIL at Stage 7 with a few routing exceptions. This is wrong for enterprise content teams. The correct model:

- Every stage produces output → human can review, edit, or approve before the record moves to the next stage
- High-confidence fields auto-approve and flow through silently — the human sees them but doesn't have to act
- Low-confidence fields require explicit action — the human must approve, edit, or flag
- **Nothing is permanently locked until final publish.** Even auto-approved fields remain editable by authorised users at any stage

### 8.2 Per-Stage HIL Pattern

**REQ-HIL-001:** Every stage follows the same review pattern:

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  AI Process  │ ──► │  Stage Results    │ ──► │  Human Review    │ ──► │  Next Stage  │
│  (automated) │     │  (with scores)   │     │  (inline edit)   │     │  (proceeds)  │
└──────────────┘     └──────────────────┘     └──────────────────┘     └──────────────┘
                           │                         │
                           │  confidence ≥ threshold  │  user can still edit
                           │  ──► auto-approved       │  auto-approved fields
                           │  (but still editable)    │
```

**REQ-HIL-002:** Per-stage review actions available to the user:

| Action | Description | Available At |
|---|---|---|
| **Approve** | Accept the AI output as-is, proceed to next stage | All stages |
| **Edit + Approve** | Modify any field value, then approve | All stages |
| **Approve All** | One-click approve all fields at this stage (for power users) | All stages |
| **Flag for Later** | Mark a field as needing attention but proceed to next stage | All stages |
| **Reject + Note** | Reject a value with a reason — field marked for re-enrichment or manual entry | All stages |
| **Request Re-run** | Ask the AI to re-process this field with a different model or prompt | All stages |

**REQ-HIL-003:** Stage progression rules:

| Rule | Behaviour | Configurable |
|---|---|---|
| Auto-advance on high confidence | If ALL fields at a stage score above the auto-approve threshold, the stage auto-completes and the record advances | Yes — can be turned off to require explicit "Approve & Continue" click |
| Block on failures | If any field has a validation failure (Stage 5) or a mandatory blank, the stage blocks until resolved | Yes — admin can set which failures block vs warn |
| Allow skip-ahead | User can jump forward to see later stages while earlier stages are still in review | Yes — default off for content teams, on for admins |
| Allow editing previous stages | User can go back and edit fields from completed stages | Yes — default on. Editing a previous stage triggers re-validation of downstream stages |

### 8.3 Stage-Specific HIL Details

#### 8.3.1 Stage 1 — Ingestion HIL

| What the human reviews | Actions |
|---|---|
| Extracted field values from PDF/Image/CSV/Web/API | Edit any extracted value, add missing values manually |
| Source attribution (OCR vs Vision vs CSV) | Confirm or correct which source is authoritative |
| Blank fields ("Not found — will enrich") | Optionally fill in manually now, or leave for enrichment |

**Key UX:** Show the source document (PDF page, image, CSV row) side by side with extracted fields. The human can see exactly what the AI read and correct misreads.

#### 8.3.2 Stage 2 — Categorisation HIL

| What the human reviews | Actions |
|---|---|
| Taxonomy assignment (Dept → Cat → Class → Sub-class) | Confirm or select alternative from top 3 suggestions |
| Mandatory attribute list for the assigned class | Add/remove attributes from the mandatory list if the class is unusual |

**Key UX:** Taxonomy browser with search — if the AI got the category wrong, the human can search and select the correct one, not just pick from 3 alternatives.

#### 8.3.3 Stage 3 — Deduplication HIL

| What the human reviews | Actions |
|---|---|
| Match result (new / variant / duplicate) | Confirm or override the AI's assessment |
| Side-by-side comparison with matched record | Select per-field which value to keep (merge mode) |

**Key UX:** This is already well-specified. No changes needed — dedup is inherently a human decision for ambiguous cases.

#### 8.3.4 Stage 4 — Enrichment HIL

| What the human reviews | Actions |
|---|---|
| Every enriched field value | Edit any value, see what the AI considered as alternatives |
| Generated copy (title, short desc, long desc) | Edit copy directly — inline text editing, not a modal |
| Completeness meter | See which fields are still missing, fill manually |

**Key UX:** The copy editing experience is critical for content teams. It must feel like editing in a CMS — inline, live character count, no friction.

#### 8.3.5 Stage 5 — Validation HIL

| What the human reviews | Actions |
|---|---|
| Validation failures (red) | Fix the value or override the rule with a reason |
| Warnings (amber) | Acknowledge or fix |
| Unit conversions | Confirm the normalised value is correct |

**Key UX:** Show the validation rule that failed, the expected range/format, and a fix suggestion. One click to apply the suggestion.

#### 8.3.6 Stage 6 — Template Transformation HIL

| What the human reviews | Actions |
|---|---|
| Field mapping (PC2 → retailer) | Confirm or manually map unmapped fields |
| Value transformations | Confirm or edit transformed values |
| Output preview | Review the final output file before it proceeds |

**Key UX:** Visual mapping lines between fields. Click any unmapped (amber) field to manually assign it.

#### 8.3.7 Stage 7 — Final Review + Publish HIL

| What the human reviews | Actions |
|---|---|
| Complete record — all fields from all stages | Final review of everything |
| Any fields flagged for later from previous stages | Must resolve before publish |
| Audit trail per field | Review the journey of each value |

**Key UX:** This stage is the summary — it shows the cumulative result of all previous stage reviews. If the user has been thorough at each stage, Stage 7 should have few or no items to review.

### 8.4 Editing Rules

**REQ-HIL-004:** Editing permissions:

| Rule | Description |
|---|---|
| All fields are editable until publish | No field is truly "locked" until the record is published. Auto-approved fields can still be edited by clicking into them |
| Editing an auto-approved field changes its status | Status changes from "auto_approved" to "human_edited". Audit trail records the override |
| Editing a field in a previous stage triggers re-validation | If a user goes back to Stage 1 and changes the voltage from "24V" to "12V", Stages 2–7 re-validate any dependent fields. The user sees a toast: "Downstream fields affected — will re-validate" |
| Published records can be unlocked by Admin | Admin can unlock a published record for re-editing. This creates a new version, not an in-place edit |

**REQ-HIL-005:** Edit tracking:

Every human edit at every stage is logged:
```json
{
  "stage": 4,
  "field": "colour",
  "old_value": "Silver",
  "new_value": "Grey",
  "editor": "reviewer@iksula.com",
  "timestamp": "2026-03-22T14:30:00Z",
  "reason": "Vision model misidentified — product is clearly grey per spec sheet page 2"
}
```

### 8.5 "Approve & Continue" Flow

**REQ-HIL-006:** At the bottom of every stage, a clear action bar:

```
┌─────────────────────────────────────────────────────────────────┐
│  [← Previous Stage]    Stage 4: Enrichment    [Next Stage →]   │
│                                                                 │
│  3 fields need review  ·  12 auto-approved  ·  0 failures      │
│                                                                 │
│  [ Approve All & Continue ]    [ Review Flagged Items ]         │
└─────────────────────────────────────────────────────────────────┘
```

- **"Approve All & Continue"** — approves all remaining items at this stage and advances to the next stage. Available only when there are no blocking failures
- **"Review Flagged Items"** — scrolls to the first item needing attention
- **Progress indicator** — "3 fields need review · 12 auto-approved · 0 failures" — shows at a glance how much work the human has at this stage

---

## 9. Per-Stage Confidence Scoring Engine

### 9.1 Design Principle

**Each stage has its own confidence scoring logic — not a one-size-fits-all formula.**

The nature of "confidence" is fundamentally different at each stage:
- Stage 1: How reliable was the extraction? (OCR quality, vision clarity)
- Stage 2: How certain is the taxonomy placement? (classification model confidence)
- Stage 3: How similar is the match? (similarity score)
- Stage 4: How trustworthy is the enriched value? (source + picklist match)
- Stage 5: Did it pass or fail validation? (binary + severity)
- Stage 6: How complete is the mapping? (coverage + transformation confidence)

### 9.2 Per-Stage Confidence Definitions

#### 9.2.1 Stage 1 — Extraction Confidence

| Component | Weight (default) | Description |
|---|---|---|
| Source clarity | 40% | OCR quality score, image resolution, CSV structure quality |
| Field match certainty | 35% | How confidently the AI matched extracted text to a specific field |
| Value completeness | 25% | Is the extracted value complete or truncated/partial? |

**Configurable settings:**
```json
{
  "stage_1_confidence": {
    "source_clarity_weight": 0.40,
    "field_match_weight": 0.35,
    "value_completeness_weight": 0.25,
    "auto_approve_threshold": 90,
    "needs_review_threshold": 65,
    "ocr_quality_minimum": 70,
    "flag_partial_values": true
  }
}
```

#### 9.2.2 Stage 2 — Classification Confidence

| Component | Weight (default) | Description |
|---|---|---|
| Model confidence | 50% | Classification model's own probability score |
| Taxonomy depth match | 30% | Confidence that the sub-class (not just department) is correct |
| Attribute alignment | 20% | Do the extracted attributes match the expected attributes for this class? |

**Configurable settings:**
```json
{
  "stage_2_confidence": {
    "model_confidence_weight": 0.50,
    "taxonomy_depth_weight": 0.30,
    "attribute_alignment_weight": 0.20,
    "auto_approve_threshold": 85,
    "needs_review_threshold": 60,
    "require_human_confirm_below": 80,
    "show_top_n_alternatives": 3
  }
}
```

#### 9.2.3 Stage 3 — Dedup Confidence

| Component | Weight (default) | Description |
|---|---|---|
| Exact match score | 40% | SKU/UPC/EAN/model number exact match (100 or 0) |
| Semantic similarity | 35% | LLM-powered name + attribute similarity |
| Attribute overlap | 25% | Percentage of matching attributes between records |

**Configurable settings:**
```json
{
  "stage_3_confidence": {
    "exact_match_weight": 0.40,
    "semantic_similarity_weight": 0.35,
    "attribute_overlap_weight": 0.25,
    "new_item_threshold": 30,
    "variant_threshold": 60,
    "duplicate_threshold": 85,
    "always_route_to_hil": false,
    "image_hash_weight": 0.15
  }
}
```

#### 9.2.4 Stage 4 — Enrichment Confidence

| Component | Weight (default) | Description |
|---|---|---|
| Source reliability | 40% | KB match > OCR > CSV > LLM > Web (configurable hierarchy) |
| Picklist consistency | 35% | Does the value match an expected picklist entry for this class? |
| Multi-source agreement | 25% | Do multiple sources agree on this value? |

**Configurable settings:**
```json
{
  "stage_4_confidence": {
    "source_reliability_weight": 0.40,
    "picklist_consistency_weight": 0.35,
    "multi_source_agreement_weight": 0.25,
    "auto_approve_threshold": 85,
    "needs_review_threshold": 60,
    "source_reliability_scores": {
      "kb_match": 95,
      "pdf_ocr": 85,
      "csv_supplier": 80,
      "image_vision": 75,
      "llm_inference": 65,
      "web_lookup": 60
    },
    "multi_source_agreement_bonus": 10,
    "conflict_resolution": "highest_reliability"
  }
}
```

#### 9.2.5 Stage 5 — Validation Confidence

| Component | Weight (default) | Description |
|---|---|---|
| Pass/fail result | 60% | Binary — did the value pass the validation rule? |
| Conversion certainty | 25% | For unit conversions — how reliable is the conversion? |
| Rule specificity | 15% | Is this a class-specific rule (high confidence) or a generic rule (lower)? |

**Configurable settings:**
```json
{
  "stage_5_confidence": {
    "pass_fail_weight": 0.60,
    "conversion_certainty_weight": 0.25,
    "rule_specificity_weight": 0.15,
    "block_on_failure": true,
    "allow_override_with_reason": true,
    "warn_on_implicit_conversion": true,
    "acceptable_conversion_loss": 0.01
  }
}
```

#### 9.2.6 Stage 6 — Transformation Confidence

| Component | Weight (default) | Description |
|---|---|---|
| Mapping certainty | 50% | Is the field mapping unambiguous? (1:1 = high, inferred = lower) |
| Value transformation validity | 30% | Did the value transform correctly to the target format? |
| Template completeness | 20% | Are all mandatory template fields populated? |

**Configurable settings:**
```json
{
  "stage_6_confidence": {
    "mapping_certainty_weight": 0.50,
    "transformation_validity_weight": 0.30,
    "template_completeness_weight": 0.20,
    "auto_approve_threshold": 90,
    "needs_review_threshold": 70,
    "flag_unmapped_fields": true,
    "flag_format_mismatches": true
  }
}
```

### 9.3 Admin Configuration UI

**REQ-CONF-001:** Admin backend provides a **Confidence Configuration** panel with:

| Feature | Description |
|---|---|
| Stage selector | Dropdown to select which stage's confidence logic to configure |
| Weight sliders | Adjustable sliders for each component weight (must sum to 1.0) |
| Threshold inputs | Numeric inputs for auto-approve, needs-review, and low-confidence thresholds |
| Source reliability editor | Drag-and-drop ranking of source reliability with numeric scores |
| Preview simulator | "With these settings, X% of fields from the last batch would be auto-approved at this stage" |
| Per-client overrides | Each client can have different confidence configs — show which clients use the default vs custom |
| Change log | Audit trail of every config change — who changed what, when, old vs new values |
| Reset to defaults | One-click restore to Iksula recommended defaults |

**REQ-CONF-002:** Confidence config is stored in the `pipeline_configs` table as part of `stage_configs` JSONB:

```json
{
  "stage_configs": {
    "1": { "confidence": { /* Stage 1 config */ }, "hil": { /* Stage 1 HIL rules */ } },
    "2": { "confidence": { /* Stage 2 config */ }, "hil": { /* Stage 2 HIL rules */ } },
    "...": "..."
  }
}
```

**REQ-CONF-003:** Config changes take effect for new records only. Records already in the pipeline continue with the config that was active when they entered.

**REQ-CONF-004:** Admin can create config **presets** (e.g. "Conservative — more human review", "Aggressive — more auto-approval", "SiteOne standard", "THD standard") and assign them per client or per batch.

### 9.4 Confidence Score Display for Content Teams

**REQ-CONF-005:** Content team users see a **simplified confidence indicator**, not raw numbers:

| Visual | Meaning | What the user does |
|---|---|---|
| Green check | High confidence — auto-approved | Nothing (but can click to edit if needed) |
| Amber dot | Needs review — AI isn't sure | Review and approve/edit |
| Red alert | Low confidence or failure | Must act before proceeding |

**REQ-CONF-006:** The raw numeric score and component breakdown are available on click/expand — but the default view is the simplified indicator. Content teams should not be overwhelmed by numbers.

---

## 10. Data Model

> **Full database schema in [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md)** — 15 tables with complete SQL.

### 10.1 Three-Layer Normalisation Model (Critical)

> **Full schema in [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md)** — 20 tables, complete SQL, mapping flows, and queries.

**REQ-DATA-001:** All product attribute data is stored in three layers:

| Layer | Table | Purpose | When Written | Mutable? |
|---|---|---|---|---|
| **Layer 0 — Raw Supplier** | `product_raw_values` | Original data exactly as received from supplier — any format, any field names, any units | Stage 1 (ingest) + Stage 4 (web scrape) | Never modified |
| **Layer 1 — Iksula Normalised** | `product_iksula_values` | Canonical internal format — clean, typed, unit-standardised, class-specific, retailer-agnostic | Stage 1 (normalise) + Stage 4 (enrich) | Updated during enrichment and review |
| **Layer 2 — Client Normalised** | `product_client_values` | Retailer-specific output — client field names, client value formats, client units | Stage 6 (transform) | Updated during review |

**REQ-DATA-002: Layer 0 — Raw Supplier Data**
- Every field extracted from every source (OCR, CSV, Vision, Web, API) is stored as a raw value with the supplier's original field name and format
- Raw values are never modified — they are the immutable audit baseline
- Multiple raw values can map to the same Iksula attribute (e.g. weight from PDF, weight from Amazon, weight from manufacturer site)
- Supplier data structures are recorded in `supplier_templates` with their field definitions
- `supplier_field_mappings` maps supplier fields → Iksula attributes with normalisation rules (unit conversion, value mapping, regex extraction)
- Supplier mappings are auto-detected, human-correctable, and reusable across all batches from the same supplier

**REQ-DATA-003: Layer 1 — Iksula Normalised**
- Each taxonomy class (e.g. "Smart Controllers") has a defined set of attributes in `iksula_class_attributes`
- Each attribute has allowed values / picklists in `iksula_allowed_values` with synonyms for auto-matching
- A product record stores one row per attribute in `product_iksula_values` with full provenance
- When multiple raw values map to the same attribute, multi-source reconciliation determines the primary value
- All enrichment, validation, DQ checks, and dedup work operates on this layer

**REQ-DATA-004: Layer 2 — Client Normalised**
- `client_field_mappings` — maps Iksula attribute → client field name + transform rule (10+ rule types: unit conversion, value lookup, format, case, concat, join, duration, temperature range, truncate)
- `client_value_mappings` — maps Iksula enum values → client values (e.g. "grey" → "Gray" for SiteOne, "GRY" for THD)
- These mappings are auto-generated on first use, then human-correctable
- A mapping correction applies to ALL future products in that class — not just the current product

**REQ-DATA-005: Mapping Correction at Every Layer**
- **Layer 0 → 1:** Human corrects a supplier field mapping (e.g. "# Stations" → `zones`). Applies to all future imports from that supplier.
- **Layer 1 → 2:** Human corrects a client field mapping (e.g. `compatible_valve_types` → "Valve Compatibility"). Applies to all future products in that class for that client.
- **Value mapping:** Human corrects a value translation (e.g. Iksula "grey" → SiteOne "Gray"). Applies everywhere that value appears.
- All corrections are logged in `audit_trail` with `layer`, before/after, and reason.
- Optionally: re-process existing products with the corrected mapping (bulk re-normalise or re-transform).

### 10.2 Product Record Schema

The central product record object must support the following field categories:

#### 8.1.1 Identity Fields

| Field | Type | Source |
|---|---|---|
| `product_name` | string | Extracted / Generated |
| `model_number` | string | Extracted |
| `sku` | string | Extracted / Assigned |
| `upc` | string (12 digits) | Extracted |
| `ean` | string (13 digits) | Extracted |
| `supplier_name` | string | Extracted |
| `brand` | string | Extracted |

#### 8.1.2 Classification Fields

| Field | Type | Source |
|---|---|---|
| `department` | string | Stage 2 classification |
| `category` | string | Stage 2 classification |
| `class` | string | Stage 2 classification |
| `sub_class` | string | Stage 2 classification |
| `taxonomy_version` | string | System |
| `classification_confidence` | number (0–100) | Stage 2 model |
| `retailer_taxonomy` | enum: siteone / thd | User selection |

#### 8.1.3 Physical Attributes

| Field | Type | Unit |
|---|---|---|
| `material` | string | — |
| `colour` | string | — |
| `weight` | number | kg |
| `shipping_weight` | number | kg |
| `width` | number | cm |
| `depth` | number | cm |
| `height` | number | cm |
| `voltage` | string | V |
| `ip_rating` | string | — |

#### 8.1.4 Product-Specific Attributes (Irrigation Controllers)

| Field | Type | Source |
|---|---|---|
| `zones` | number | Extracted |
| `wifi_enabled` | boolean | Extracted |
| `operating_temp_range` | string | Enriched |
| `certifications` | string[] | Enriched |
| `compatible_valve_types` | string[] | Enriched |
| `app_name` | string | Enriched |
| `warranty_months` | number | Extracted / Enriched |

#### 8.1.5 Content Fields

| Field | Type | Constraints |
|---|---|---|
| `product_title` | string | Max 80 chars, SEO-optimised, retailer-formatted |
| `short_description` | string | Max 150 chars, feature-led |
| `long_description` | string | Max 400 chars, spec-heavy, B2B tone |

#### 8.1.6 Provenance Metadata (per field)

Every field in the product record must carry:

```json
{
  "value": "<field value>",
  "source": "OCR | Vision | CSV | Web | API | KB | LLM | Human",
  "model": "<model name that produced this value>",
  "iksula_layer": "<Iksula processing layer>",
  "prompt_template": "<prompt template name, if applicable>",
  "confidence": {
    "composite": 85,
    "source_reliability": 90,
    "consistency": 80,
    "completeness": 85
  },
  "extraction_page_ref": "<page number, if from PDF>",
  "picklist_match": "<matched picklist entry, if from KB>",
  "alternatives_considered": [
    { "value": "alt1", "score": 72 },
    { "value": "alt2", "score": 58 }
  ],
  "status": "auto_approved | needs_review | low_confidence | validation_fail | human_approved | human_edited | rejected",
  "audit_trail": [
    {
      "action": "extracted | enriched | validated | approved | edited | rejected",
      "value": "<value at this point>",
      "actor": "system | <reviewer_name>",
      "timestamp": "<ISO 8601>",
      "reason": "<optional, for edits/rejections>"
    }
  ]
}
```

### 8.2 Batch Job Schema

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Unique batch identifier |
| `file_name` | string | Uploaded file name |
| `item_count` | number | Number of items in batch |
| `status` | enum | Queued / Processing / Complete / Failed |
| `created_at` | ISO 8601 | Upload timestamp |
| `completed_at` | ISO 8601 | Completion timestamp |
| `items` | ProductRecord[] | Array of product records |

### 8.3 Deduplication Match Schema

| Field | Type | Description |
|---|---|---|
| `match_type` | enum | exact / fuzzy / attribute_similarity / image_hash |
| `similarity_score` | number (0–100) | Overall match confidence |
| `matched_record_id` | string | ID of existing catalog record |
| `field_diffs` | object[] | Per-field comparison between incoming and existing |
| `outcome` | enum | new_item / likely_duplicate / possible_variant |
| `resolution` | enum | merge / keep_variant / reject_incoming / override_existing |

---

## 11. Stage 1 — Raw Supplier Data Ingestion

### 9.1 Objective

Capture and structure raw product data from any supplier source format into the PC2 internal product record.

### 9.2 Functional Requirements

#### 9.2.1 Input Modes

**REQ-S1-001: PDF Spec Sheet Upload**
- Drag-and-drop upload zone
- Simulated OCR processing using "Iksula OCR Engine v2"
- Simulated LLM parsing using "GPT-4o" for field extraction
- Fields populate in real time with animated progression
- Each extracted field shows page reference from source PDF
- Processing steps animate in sequence: "Reading file…" → "Extracting text…" → "Parsing fields…" → "Structuring record…"

**REQ-S1-002: Product Image / Label Upload**
- Drag-and-drop image upload
- Simulated vision model processing using "Iksula Vision v1.2"
- Extracts: label text, model numbers, certification marks, spec values
- Each extracted field tagged with "Vision" source badge

**REQ-S1-003: Supplier CSV / Spreadsheet Upload**
- File upload for CSV/XLSX files
- Simulated parsing handles: messy headers, non-standard column names, merged cells
- Column mapping preview shown before import
- Fields tagged with "CSV" source badge

**REQ-S1-004: Web Lookup**
- Input: product name or manufacturer + model number
- Simulated structured extraction from manufacturer website
- Shows source URL for each extracted value
- Fields tagged with "Web" source badge

**REQ-S1-005: API Feed**
- Show a mock "connected supplier feed" interface
- Display 6 items in a job queue (simulated)
- Each item shows: supplier name, product name, feed status
- Fields tagged with "API" source badge

#### 9.2.2 Output Requirements

**REQ-S1-006: Per-Field Output Display**

Each extracted field must show:

| Element | Description |
|---|---|
| Source badge | OCR / Vision / CSV / Web / API (colour-coded) |
| Value | Extracted value, or blank |
| Extraction confidence | 0–100 numeric score |
| Blank label | "Not found — will enrich" label on empty fields |

**REQ-S1-007:** Blank fields must NOT be hidden. Display them explicitly with the "Not found — will enrich" label to set up the enrichment stage.

#### 9.2.3 Batch Upload UI

**REQ-S1-008: Batch Upload Zone**
- Separate from single-item upload
- Premium drag-and-drop zone — visually distinct, not a plain grey box
- File preview showing: file name, size, type
- Clear error states for unsupported file types

**REQ-S1-009: Job Queue Table**

| Column | Description |
|---|---|
| File name | Uploaded file name |
| Item count | Number of items detected in file |
| Status | Queued / Processing / Complete / Failed (colour-coded) |
| Actions | View / Cancel / Retry |

**REQ-S1-010:** Demo shows 6 rows in the queue. One item processes through the pipeline. The rest remain in various states (Queued, Processing) to convey enterprise scale.

#### 9.2.4 Upload UX Quality

**REQ-S1-011:** The upload zone must feel premium:
- Animated border on drag hover
- File type icon display
- Progress indicator during upload
- Named processing steps animate in sequence with realistic timing
- Error states with clear messaging and recovery actions

### 9.3 Iksula IP Visibility

- Model attribution: "Iksula OCR Engine v2" and "GPT-4o" shown on PDF extraction
- Model attribution: "Iksula Vision v1.2" shown on image extraction
- Processing pipeline: each named step shown during animation

---

## 12. Stage 2 — Categorisation

### 10.1 Objective

Place the ingested item in the correct retailer taxonomy — Department → Category → Class → Sub-class.

### 10.2 Functional Requirements

#### 10.2.1 Auto-Classification

**REQ-S2-001:** Based on product name, description, and extracted attributes, simulate a classification model assigning the product to a four-level taxonomy hierarchy:
- Department
- Category
- Class
- Sub-class

**REQ-S2-002:** Show confidence score per taxonomy level (0–100).

**REQ-S2-003:** Classification model attribution: "Iksula Retail Taxonomy v4.2".

#### 10.2.2 Retailer Taxonomy Support

**REQ-S2-004:** Show two taxonomy tabs:
- **SiteOne taxonomy** — labelled "Mapped against Iksula Retail Taxonomy v4.2 — SiteOne edition"
- **THD taxonomy** — labelled "Mapped against Iksula Retail Taxonomy v4.2 — THD edition"

**REQ-S2-005:** Same product may map to different taxonomy nodes per retailer. Show both mappings side by side.

#### 10.2.3 Mandatory Attributes

**REQ-S2-006:** Once class is assigned, immediately display a mandatory attributes panel:
- Title: "Mandatory attributes for [Sub-class] class"
- List 8–10 mandatory attributes for the assigned class
- **Green** highlight: attributes already found in Stage 1
- **Red** highlight: attributes still missing
- This visually sets up the enrichment stage

#### 10.2.4 Human-in-the-Loop Routing

**REQ-S2-007:** If classification confidence is below 80% on any taxonomy level:
- Route to HIL queue for category confirmation
- Show top 3 alternative classifications with confidence scores
- Reviewer selects the correct classification
- Confirmed classification is locked (non-editable)

**REQ-S2-008:** If confidence ≥ 80%, auto-approve and lock the classification.

### 10.3 Iksula IP Visibility

**REQ-S2-009:** Display: "Iksula Retail Taxonomy — SiteOne edition, 847 classes, last updated March 2026"

**Rationale:** This taxonomy is proprietary IP built from years of catalog work. A generic LLM does not have retailer-specific taxonomy depth. This must be visually prominent.

---

## 13. Stage 3 — Deduplication

### 11.1 Objective

Determine whether the incoming item already exists in the catalog — as an exact duplicate, a variant, or a genuinely new item.

### 11.2 Functional Requirements

#### 11.2.1 Match Methods

**REQ-S3-001:** Run four match checks in sequence, animating each step:

| # | Method | Description | Model |
|---|---|---|---|
| 1 | Exact match | SKU, UPC, EAN, model number lookup | Iksula Dedup Model v1.0 |
| 2 | Fuzzy name match | LLM-powered semantic similarity on product name + key attributes | Iksula Dedup Model v1.0 |
| 3 | Attribute similarity | Vector similarity across the full attribute set | Iksula Dedup Model v1.0 |
| 4 | Image hash match | Visual similarity against catalog images (if image uploaded) | Iksula Vision v1.2 |

**REQ-S3-002:** Each method shows: running animation → result (match found / no match) → confidence score.

#### 11.2.2 Match Outcomes

**REQ-S3-003:** Three possible outcomes:

| Outcome | Condition | UI Treatment | Action |
|---|---|---|---|
| **New item** | No match found | Green badge | Proceed to enrichment |
| **Likely duplicate** | High similarity (≥ 85%) | Red badge | Route to HIL — merge / reject |
| **Possible variant** | Medium similarity (60–84%) | Amber badge | Route to HIL — confirm variant or duplicate |

#### 11.2.3 Side-by-Side Comparison View

**REQ-S3-004:** For duplicate/variant outcomes, show a two-column diff:
- **Left column:** Incoming item (new data)
- **Right column:** Existing catalog item (matched record)
- Field-level differences highlighted
- Matching fields shown in neutral colour
- Differing fields highlighted with colour contrast

**REQ-S3-005:** Reviewer action buttons:

| Action | Description |
|---|---|
| **Merge** | Keep best value per field (reviewer selects per field) |
| **Keep as variant** | Confirm incoming item is a new variant, proceed separately |
| **Reject incoming** | Discard the incoming item |
| **Override existing** | Replace existing catalog record with incoming data |

#### 11.2.4 Demo Scenario

**REQ-S3-006:** Demo shows a "Possible variant" match:
- Incoming: Orbit 6-Zone Controller B-0624W
- Matched: Orbit 4-Zone Controller B-0424W (existing)
- Similarity: 78%
- Reviewer confirms: new variant
- Record proceeds to enrichment

### 11.3 Iksula IP Visibility

**REQ-S3-007:** Display: "Iksula Dedup Model v1.0 — trained on 12M retail product pairs"

**REQ-S3-008:** Callout: Retail-specific dedup understands that "24V Controller 6-zone" and "6-Station 24 Volt Smart Irrigation Timer" are the same product. Generic string matching does not.

---

## 14. Stage 4 — Enrichment

### 12.1 Objective

Fill all attribute gaps, generate AI-ready product content, and maximise field completeness.

### 12.2 Functional Requirements

#### 12.2.1 Attribute Gap Fill

**REQ-S4-001:** For every blank mandatory attribute, run four enrichment sources in sequence, animating each:

| # | Source | Description | Model |
|---|---|---|---|
| 1 | Iksula KB | Match against class-specific picklist and attribute dictionary | Iksula KB v3.1 |
| 2 | LLM inference | Category-specific prompt template, infer from surrounding context | GPT-4o |
| 3 | Web scrape — Google + manufacturer | Search by SKU/EAN/title, scrape top 3 URLs (see 12.2.2) | Iksula Web Scraper v1.0 |
| 4 | Web scrape — marketplaces | Search Amazon/retailer sites, scrape top 10 results (see 12.2.2) | Iksula Web Scraper v1.0 |

**REQ-S4-002:** Every filled field must show:
- Source label (KB / LLM / Web-Google / Web-Marketplace)
- Model attribution
- For KB matches: "Matched to Iksula [Category] picklist [list of valid values] — selected [value]"
- For web scrape: source URL, scrape timestamp, which page the value was found on

#### 12.2.2 Web-Based Attribute Extraction

**REQ-S4-012: Google Search + Manufacturer Scrape**

For every product with missing attributes, the system:

1. Takes the product identifier — SKU ID, EAN, UPC, or product title
2. Constructs a search query: `"{model_number}" OR "{product_name}" site:manufacturer.com specifications`
3. Executes a Google search (via SerpAPI or similar)
4. Opens the **top 3 result URLs**
5. Scrapes each page for structured product data (spec tables, attribute lists, product detail sections)
6. Extracts attribute values and maps them to the retailer template fields

| Step | Action | Output |
|---|---|---|
| Search | Google: "Orbit B-0624W specifications" | Top 3 URLs |
| URL 1 | orbitonline.com/products/B-0624W | Weight: 0.8 lbs, Dims: 7×4.7×2.4 in |
| URL 2 | irrigationdirect.com/orbit-b0624w | Operating temp: 32–122°F, App: Orbit B-hyve |
| URL 3 | homedepot.com/p/orbit-6-zone/12345 | Color: Grey, Material: ABS Plastic |

**REQ-S4-013: Marketplace Scrape (Amazon + Retailer Sites)**

In parallel with or after Google scrape, the system:

1. Searches **Amazon** using the product title or model number
2. Scrapes the **top 10 results** that match (filtered by brand/model similarity)
3. Extracts attributes from: product title, bullet points, product description, technical specifications table, "From the manufacturer" section
4. Can also search **other retailer sites** configured per client: Home Depot, Lowe's, SiteOne, distributor sites

| Source | Search Query | Fields Extracted |
|---|---|---|
| Amazon | "Orbit B-0624W irrigation controller" | Weight, dimensions, voltage, zones, color, material, bullet points for description |
| Amazon (result 2) | Similar product listing | Compatible valves, certifications, app name |
| Amazon (result 3) | Related product | Warranty info, operating temp |
| Home Depot | "Orbit 6-zone smart controller" | Category, specs table, images |

**REQ-S4-014: Scrape-to-Template Mapping**

Scraped attributes are automatically mapped to the active retailer template:

| Scraped Raw Value | Template Field | Mapping Logic |
|---|---|---|
| "Weighs 0.8 pounds" | Weight (kg) | Extract numeric + unit, normalise to kg → 0.36 kg |
| "Works with Orbit B-hyve app" | App Name | Extract app name from sentence → "Orbit B-hyve" |
| "Operating Temperature: 32°F to 122°F" | Operating Temp (°C) | Extract range, convert to °C → "0–50°C" |
| "6 zones, 24V" | Zones / Voltage | Split multi-value, map to separate fields |
| Amazon bullet: "IP44 outdoor rated" | IP Rating | Extract standard code → "IP44" |

**REQ-S4-015: Web Scrape Display**

For every web-scraped attribute, the UI shows:

| Element | Description |
|---|---|
| Source badge | "Web-Google" (blue) or "Web-Amazon" (orange) |
| Source URL | Clickable link to the page where the value was found |
| Scrape timestamp | When the data was scraped |
| Raw text | The original text from the page (before parsing) |
| Parsed value | The cleaned, normalised value mapped to the template |
| Confidence | Based on: source reliability + number of sources that agree + picklist match |

**REQ-S4-016: Multi-Source Agreement from Web Scrape**

When multiple web sources return the same attribute:
- If 2+ sources agree on a value → confidence boosted, value auto-selected
- If sources conflict → all values shown, highest-confidence selected, flagged for HIL review
- Example: Amazon says "0.8 lbs", manufacturer says "0.36 kg" → same value, different units → agreement confirmed, confidence boosted

**REQ-S4-017: Web Scrape Configuration (Admin)**

Configurable per client in Admin > Pipeline Config:

| Setting | Default | Description |
|---|---|---|
| `google_scrape_enabled` | true | Enable Google search + top URL scraping |
| `google_max_urls` | 3 | Max URLs to scrape from Google results |
| `marketplace_scrape_enabled` | true | Enable Amazon/retailer site scraping |
| `marketplace_sources` | ["amazon.com"] | List of marketplace sites to search |
| `marketplace_max_results` | 10 | Max results to scrape per marketplace |
| `scrape_timeout_ms` | 10000 | Timeout per URL scrape |
| `prefer_manufacturer_site` | true | Prioritise manufacturer URLs over third-party |
| `blocked_domains` | [] | Domains to never scrape (competitor sites, etc.) |

**REQ-S4-018: Demo Scenario — Web Scrape**

For the Orbit B-0624W demo, hardcode these web scrape results:

| Source | URL | Attributes Found |
|---|---|---|
| Google #1 | orbitonline.com/products/B-0624W | Weight: 0.8 lbs, Dims: 7×4.7×2.4 in, App: Orbit B-hyve |
| Google #2 | irrigationdirect.com/orbit-b0624w | Operating temp: 32–122°F, Warranty: 24 months |
| Google #3 | homedepot.com/p/orbit-6-zone/309876 | Color: Grey, Certifications: CE, RoHS |
| Amazon #1 | amazon.com/dp/B09XYZ1234 | Weight: 12.8 oz, Zones: 6, Voltage: 24V, Color: Gray |
| Amazon #2 | amazon.com/dp/B09XYZ5678 | Compatible: 24VAC solenoid valves, App: B-hyve |

#### 12.2.3 Image Enrichment

**REQ-S4-003:** If an image was uploaded, run a visual analysis pass generating derived attributes:

| Derived Attribute | Example Value |
|---|---|
| Dominant colour | Grey |
| Form factor | Wall-mount box |
| Finish type | Matte |
| Mounting type | Wall-mount |
| Packaging style | Retail blister pack |

**REQ-S4-004:** Label all vision-derived attributes: "Vision-derived — Iksula Vision Model v1.2"

**REQ-S4-005:** These are new attributes not available from any text source — this demonstrates the value of multi-modal AI.

#### 12.2.4 Copy Generation

**REQ-S4-006:** Generate three copy assets using category-specific prompts:

| Asset | Constraints | Style |
|---|---|---|
| Product title | Max 80 characters | SEO-optimised, retailer-formatted |
| Short description | Max 150 characters | Feature-led, for SiteOne contractor audience |
| Long description | Max 400 characters | Spec-heavy, B2B tone |

**REQ-S4-007:** Show prompt template name: "Iksula Copy Prompt — Irrigation Controllers v3.0 — SiteOne edition"

**REQ-S4-008:** All three copy fields must be editable by the user.

**REQ-S4-009:** Show character count and limit indicator for each copy field.

#### 12.2.5 Completeness Meter

**REQ-S4-010:** Prominent animated bar at top of stage:
- Shows: "Field completeness: [before]% → [after]%"
- Animates from Stage 1 completeness score to post-enrichment score
- Demo values: 44% → 93%
- This is a visual ROI indicator of the enrichment step

#### 12.2.6 Model Panel

**REQ-S4-011:** Collapsible panel: "Models used in this enrichment"

| Model | Role |
|---|---|
| Iksula KB v3.1 | Attribute lookup |
| GPT-4o | Copy generation |
| Iksula Vision v1.2 | Image analysis |

### 12.3 Iksula IP Visibility

- Category-specific prompt templates (named, versioned)
- Picklist matching with explicit dictionary reference
- Multi-model orchestration made visible
- Completeness improvement quantified

---

## 15. Stage 5 — DIM Check + Validation

### 13.1 Objective

Validate dimensions, units, ranges, mandatory fields, and data formats. Block non-compliant records from progressing.

### 13.2 Functional Requirements

#### 13.2.1 DIM Checks

**REQ-S5-001: Unit Normalisation**
- Convert all dimensions to standard units (cm, kg, V, A, °C)
- Flag mixed units within the same record (e.g. inches and cm)
- Show original value and normalised value side by side
- Model: "Iksula DIM Validator v2.3"

**REQ-S5-002: Range Validation**
- Check each value is within the expected range for the assigned class
- Example: voltage for irrigation controllers must be 12V, 24V, or 120V — not 240V
- Flag out-of-range values as warnings or failures

**REQ-S5-003: Logical Consistency**
- Check that width × depth × height produces a plausible product volume
- Flag impossibly large or small dimensions
- Cross-check weight vs dimensions for plausibility

#### 13.2.2 Mandatory Field Check

**REQ-S5-004:** Cross-check against the mandatory attribute list defined in Stage 2.

**REQ-S5-005:** Every mandatory field must have a value at this point. Any still blank after enrichment is a **hard fail** — flagged red, must be resolved in HIL before the record can proceed.

#### 13.2.3 Format Validation

**REQ-S5-006:** Validate value formats:

| Field Type | Validation Rule |
|---|---|
| UPC | Must be exactly 12 digits |
| EAN | Must be exactly 13 digits |
| Model number | Must match supplier pattern |
| URL fields | Must be valid URLs |
| Image fields | Must have accessible URLs or uploaded files |

#### 13.2.4 Validation Results Display

**REQ-S5-007:** Results table with columns:

| Column | Description |
|---|---|
| Rule name | Name of the validation rule applied |
| Field affected | Which product field was checked |
| Value | Current field value |
| Result | Pass (green) / Warning (amber) / Fail (red) |
| Fix suggestion | Automated suggestion for fixing the issue |

**REQ-S5-008:** Three summary metric cards at top:
- **Passed** (green) — count of passed checks
- **Warnings** (amber) — count of warnings
- **Failures** (red) — count of failures

**REQ-S5-009:** Failures block stage progression. Must be resolved in HIL (Stage 7) before the record can be published.

#### 13.2.5 Demo Scenario

**REQ-S5-010:** Hardcoded validation results:

| Check | Input | Output | Result |
|---|---|---|---|
| Weight normalisation | "0.8 lbs" | "0.36 kg" | Pass (green) |
| Dimension normalisation | "7 × 4.7 × 2.4 inches" | "17.8 × 11.9 × 6.1 cm" | Pass (green) |
| Temperature normalisation | "32–122°F" | "0–50°C" | Pass (green) |
| Shipping weight | Missing | — | Fail (red, routes to HIL) |

### 13.3 Iksula IP Visibility

**REQ-S5-011:** Display: "Iksula DIM Validator v2.3 — 340 validation rules across 847 classes"

**Rationale:** These rules are built from years of retailer compliance requirements. THD has specific DIM requirements that a generic validator does not know. This is especially compelling for THD's merchandising and supply chain teams.

---

## 16. Stage 6 — Template Transformation

### 14.1 Objective

Map the enriched, validated product record to the exact output format required by the target retailer's PIM system.

### 14.2 Functional Requirements

#### 14.2.1 Retailer Template Selection

**REQ-S6-001:** Show two template options:
- **SiteOne template** — labelled "SiteOne Template v2.4 — maintained by Iksula, last updated Jan 2026"
- **THD template** — labelled "THD Template v6.1 — Iksula certified"

**REQ-S6-002:** Each template defines:

| Template Property | Description |
|---|---|
| Field names | Retailer-specific field naming (e.g. "Product Short Title" vs "Item Name") |
| Field order | Column/field sequence as expected by the PIM |
| Mandatory vs optional | Which fields are required for submission |
| Character limits | Max length per field |
| Accepted value formats | Data type, enum values, formatting rules |

**REQ-S6-003:** Template selector with preview of the output structure before transformation.

#### 14.2.2 Field Mapping Visualisation

**REQ-S6-004:** Animated field mapping step:
- **Left side:** PC2 internal field names (enriched record)
- **Right side:** Retailer template field names
- **Connecting lines:** Animated lines showing field-to-field mapping
- **Unmapped fields:** Highlighted in amber
- **Mapping confidence:** "98% auto-mapped — 2 fields need manual mapping"

#### 14.2.3 Value Transformation

**REQ-S6-005:** Apply retailer-specific formatting rules:

| Transformation | Example |
|---|---|
| Capitalisation rules | THD requires title case on product names |
| Unit formats | SiteOne prefers imperial; THD prefers metric option |
| Boolean conversion | Yes/No → 1/0 for THD |
| Multi-value formatting | Pipe-separated vs comma-separated per retailer |
| Date formats | MM/DD/YYYY vs YYYY-MM-DD per retailer |
| Warranty formatting | "24 months" → "2 Years" per SiteOne standard |

#### 14.2.4 Output Preview

**REQ-S6-006:** Live preview of the output file in the exact column order and format of the selected retailer template.

**REQ-S6-007:** Export format options:

| Format | Use Case |
|---|---|
| CSV | SiteOne standard |
| XML | THD PIM integration |
| JSON | API integration |
| PIM-ready | Direct PIM import format |

#### 14.2.5 Demo Scenario

**REQ-S6-008:** Hardcoded transformation examples:

| PC2 Field | Retailer Field | Original Value | Transformed Value |
|---|---|---|---|
| `operating_temperature_range` | Operating Temp (°C) | 0–50°C | 0–50°C (accepted as-is) |
| `warranty_months` | Warranty Period | 24 | 2 Years |
| `product_name` | Product Short Title | Orbit smart irrigation controller | Orbit Smart Irrigation Controller (title case) |

**REQ-S6-009:** Show 2 fields needing manual mapping — the user sees that 98% auto-mapped but some edge cases still need human input.

### 14.3 Iksula IP Visibility

**REQ-S6-010:** Display template provenance:
- "SiteOne Template v2.4 — maintained by Iksula, last updated Jan 2026"
- "THD Template v6.1 — Iksula certified"

**Rationale:** These templates represent maintained relationships with retailers. The client cannot get this from a generic AI tool. SiteOne cares most about this stage — they don't want another tool that produces data they then have to manually reformat.

---

## 17. Stage 7 — Final Review + Publish

### 17.1 Objective

Stage 7 is the **final checkpoint** before publishing. By this point, the human has already reviewed and approved fields at each previous stage (see Section 8 — HIL Framework). Stage 7 aggregates any remaining unresolved items, provides the complete record view, and handles publish.

Confidence scoring logic and thresholds are defined in Section 9 (Per-Stage Confidence Scoring Engine) and apply at every stage, not just Stage 7.

### 17.2 Functional Requirements

#### 17.2.1 Final Review Queue

**REQ-S7-004:** Queue sorted by priority:
1. Validation fails (purple) — first
2. Low confidence (red) — second
3. Needs review (amber) — third

**REQ-S7-005:** Each queue card shows:

| Element | Description |
|---|---|
| Field name | Which field needs review |
| AI value | The value proposed by the AI |
| Confidence breakdown | Three-component score visualisation |
| Source snippet | Exact text or image crop that produced this value |
| Alternative values | Top 2–3 alternatives with scores |
| Actions | Approve / Edit + Approve / Reject |

#### 17.2.2 Reviewer Actions

**REQ-S7-006: Approve**
- Accept the AI-proposed value as-is
- Field status changes to "human_approved"
- Audit trail entry added

**REQ-S7-007: Edit + Approve**
- Reviewer modifies the value, then approves
- Field badge changes to "Human edited"
- Show toast notification: "Correction queued for Iksula KB review — will improve future enrichment"
- Audit trail entry added with both old and new values
- **This makes the learning loop visible** — corrections feed back into the KB

**REQ-S7-008: Reject**
- Reject with mandatory reason selection:
  - Wrong value
  - No valid source
  - Outside class standards
  - Supplier error
- Rejected fields do NOT block publish
- Flagged as "Pending source data" in the final record
- Audit trail entry with rejection reason

#### 17.2.3 Publish

**REQ-S7-009:** "Publish record" button enabled once all validation fails and review items are resolved.

**REQ-S7-010:** Final record view shows:

| Element | Description |
|---|---|
| All fields with values | Complete product record |
| Source per field | Where each value came from |
| Resolution status | Auto-approved / Human approved / Human edited / Rejected |
| Overall readiness score | Composite record-level score |

**REQ-S7-011:** Audit trail per field (expandable):

| Audit Entry | Fields |
|---|---|
| Original supplier value | Value as received in Stage 1 |
| AI model that processed it | Model name and version |
| Iksula layer that scored it | Processing layer reference |
| Human reviewer who approved it | Reviewer name |
| Timestamp | ISO 8601 |
| Action taken | Approved / Edited / Rejected |

**REQ-S7-012:** Export options: CSV / JSON / XML

**REQ-S7-013:** Publish confirmation: "Record published to SiteOne staging catalog"

### 17.3 Iksula IP Visibility

**REQ-S7-014:** The audit trail is non-negotiable for THD. Compliance and procurement will ask exactly where every field came from.

Audit chain: original supplier value → AI model that processed it → Iksula layer that scored it → human reviewer who approved it → timestamp.

**This is what separates an enterprise product from a prototype.**

---

## 18. Demo Scenario — Hardcoded Data Specification

### 18.1 Demo Product

| Field | Value |
|---|---|
| Product | Orbit 24V 6-Zone Smart Irrigation Controller |
| Features | Wi-Fi enabled, outdoor-rated, IP44 |
| Model | B-0624W |
| Supplier | Orbit Irrigation Products |

This product must be used throughout all 7 stages. Data is hardcoded with realistic values, gaps, and edge cases.

### 18.2 Stage-by-Stage Demo Data

#### Stage 1 — Ingestion

**Input method:** PDF spec sheet (drag-and-drop)

**Extracted fields:**

| Field | Value | Confidence | Source |
|---|---|---|---|
| Product name | Orbit 24V 6-Zone Smart Irrigation Controller | 97 | OCR |
| Model number | B-0624W | 99 | OCR |
| Voltage | 24V | 95 | OCR |
| Zones | 6 | 96 | OCR |
| Wi-Fi | Yes | 92 | OCR |
| IP rating | IP44 | 94 | OCR |
| Supplier | Orbit Irrigation Products | 98 | OCR |

**Blank fields (show with "Not found — will enrich"):**

| Field | Status |
|---|---|
| Material | Not found |
| Colour | Not found |
| Weight | Not found |
| Dimensions (cm) | Not found |
| Operating temp (°C) | Not found |
| Certifications | Not found |
| Compatible valve types | Not found |
| App name | Not found |

#### Stage 2 — Categorisation

| Level | Value | Confidence |
|---|---|---|
| Department | Hardware & Tools | 96% |
| Category | Irrigation | 95% |
| Class | Controllers | 94% |
| Sub-class | Smart Controllers | 94% |

Mandatory attributes for Smart Controllers class (10 attributes):
- 4 found (green): voltage, zones, Wi-Fi, IP rating
- 6 missing (red): material, colour, weight, dimensions, operating temp, certifications

#### Stage 3 — Deduplication

| Field | Value |
|---|---|
| Matched record | Orbit 4-Zone Controller B-0424W |
| Similarity score | 78% |
| Outcome | Possible Variant (amber) |
| Resolution | Reviewer confirms new variant → proceeds |

#### Stage 4 — Enrichment

**Filled attributes:**

| Field | Value | Source | Model |
|---|---|---|---|
| Material | ABS Plastic | KB match | Iksula KB v3.1 |
| Colour | Grey | Vision-derived | Iksula Vision v1.2 |
| Weight | 0.8 kg | Web | Iksula Enrichment — Irrigation v4 |
| Dimensions | 18 × 12 × 6 cm | Web | Iksula Enrichment — Irrigation v4 |
| Operating temp | 0–50°C | LLM inference | GPT-4o |
| Certifications | CE, RoHS | KB match | Iksula KB v3.1 |
| Compatible valves | 24VAC solenoid | KB match | Iksula KB v3.1 |
| App name | Orbit B-hyve | Web | Iksula Enrichment — Irrigation v4 |

**Copy generated:**
- **Title:** "Orbit 24V 6-Zone Smart Wi-Fi Irrigation Controller — IP44 Outdoor" (76 chars)
- **Short desc:** "Smart 6-zone irrigation controller with Wi-Fi, 24V, IP44-rated for outdoor use. Compatible with Orbit B-hyve app." (113 chars)
- **Long desc:** "The Orbit B-0624W is a 6-zone smart irrigation controller operating on 24V with built-in Wi-Fi connectivity. IP44-rated for outdoor installation, it supports 24VAC solenoid valves and is controllable via the Orbit B-hyve app. Constructed from durable ABS plastic in grey finish. CE and RoHS certified. Operating temperature range: 0–50°C." (338 chars)

**Completeness:** 44% → 93%

#### Stage 5 — DIM Check + Validation

| Rule | Field | Input | Output | Result |
|---|---|---|---|---|
| Unit normalisation | Weight | 0.8 lbs | 0.36 kg | Pass (green) |
| Unit normalisation | Dimensions | 7 × 4.7 × 2.4 in | 17.8 × 11.9 × 6.1 cm | Pass (green) |
| Unit normalisation | Operating temp | 32–122°F | 0–50°C | Pass (green) |
| Mandatory check | Shipping weight | Missing | — | Fail (red) |

Summary: 3 Passed, 0 Warnings, 1 Failure

#### Stage 6 — Template Transformation

Target: SiteOne Template v2.4

| PC2 Internal Field | SiteOne Field | Value | Transformation |
|---|---|---|---|
| `operating_temperature_range` | Operating Temp (°C) | 0–50°C | Accepted as-is |
| `warranty_months` | Warranty Period | 24 → "2 Years" | Numeric to text format |
| `product_name` | Product Short Title | Title case applied | Capitalisation rule |

Mapping: 98% auto-mapped, 2 fields need manual mapping.

#### Stage 7 — HIL Review + Publish

**Queue items (4):**

| # | Field | Issue | Confidence | Priority | Resolution |
|---|---|---|---|---|---|
| 1 | Shipping weight | Mandatory field missing (validation fail) | — | Purple | Reviewer enters "0.45 kg" |
| 2 | Colour | AI value "Grey" | 72 | Amber | Reviewer approves as-is |
| 3 | Compatible valve types | AI value "24VAC solenoid" | 68 | Amber | Reviewer approves |
| 4 | App name | AI value "Orbit B-hyve" | 61 | Amber | Reviewer edits to "Orbit B-hyve app" |

**Final action:** Publish → "Record published to SiteOne staging catalog"

---

## 19. UI/UX Requirements — Content Team Experience

### 19.1 Design Philosophy

**The primary user is a content team member, not an engineer.**

Content teams process hundreds of products per day. They need:
- **Clarity** — see what needs their attention, ignore what doesn't
- **Speed** — approve/edit/move on with minimal clicks
- **Confidence** — know that the AI got it right without needing to understand how
- **No overwhelm** — enterprise detail is available on demand, not in their face

The UI has two layers:
1. **Content team layer** (default) — clean, simple, focused on values and actions
2. **Enterprise detail layer** (expandable) — model names, confidence breakdowns, audit trails, prompt templates

### 19.2 Layout

**REQ-UI-001:** Single-page application with persistent top navigation.

**REQ-UI-002:** Top stepper bar always visible, showing all 7 stages with status badges and inline HIL status ("3 items need review" badge on each stage).

**REQ-UI-003:** Main content area renders the active stage.

**REQ-UI-004:** Role selector visible in header (Admin / Reviewer / Viewer).

**REQ-UI-016:** Per-stage action bar at the bottom (see Section 8.5) — always visible, shows: "X fields need review · Y auto-approved · Z failures" + "Approve All & Continue" button.

### 19.3 Content Team Default View

**REQ-UI-017:** The default view for content team users (Reviewer role) shows:

| Element | What they see | What they DON'T see (until they expand) |
|---|---|---|
| Field value | The value, editable on click | Model name, prompt template |
| Confidence | Green check / amber dot / red alert | Numeric score, component breakdown |
| Source | Small badge: "OCR" / "KB" / "AI" / "Web" | Full source reference, page number |
| Action buttons | Approve / Edit / Flag | Audit history, alternative values |

**REQ-UI-018:** "Click to see more" pattern — every field row is expandable:
- **Collapsed (default):** Field name · Value · Confidence indicator (green/amber/red) · Source badge · [Approve] [Edit]
- **Expanded:** Full confidence breakdown · Model attribution · Source snippet · Alternative values · Audit trail

**REQ-UI-019:** Content team users should be able to process a record through all 7 stages in under 5 minutes if the AI gets most fields right (which it should for standard products).

### 19.4 Inline Editing Experience

**REQ-UI-020:** All fields are editable inline — click the value to edit, press Enter or click away to save. No modals, no separate edit screens.

**REQ-UI-021:** Copy fields (title, short description, long description) use a rich text area with:
- Live character count and limit indicator
- Character limit warning (amber) when within 10 characters of limit
- Character limit block (red) when over limit
- Undo/redo support

**REQ-UI-022:** For fields with picklists (material, voltage, certifications), show a dropdown with valid options from the Iksula KB. Free text entry is allowed but flagged: "Custom value — not in picklist".

**REQ-UI-023:** After editing any field, show a brief confirmation: "Saved" + the field's status changes to "Human edited" with a small pencil icon.

### 19.5 Batch Processing UX

**REQ-UI-024:** When processing a batch of items, the content team sees:
- A list view of all items in the batch with completion status
- Click into any item to see the 7-stage view
- Quick stats: "12 items complete · 3 in review · 1 blocked"
- Sort/filter by: status, stage, number of items needing review

**REQ-UI-025:** "Fast track" mode for batches — when most items are standard, the user can:
- "Approve all high-confidence items" — auto-approves all items with 0 amber/red fields across all stages
- Then work through only the items that need attention

### 19.6 Design System

**REQ-UI-005:** Tailwind CSS for all styling.

**REQ-UI-006:** Colour semantics:

| Colour | Meaning | Content team reads it as |
|---|---|---|
| Green | Pass, approved, high confidence | "This is fine — move on" |
| Amber/Yellow | Warning, needs review | "Look at this one" |
| Red | Fail, low confidence | "Must fix this" |
| Blue | Active, in progress | "Working on it" |
| Purple | Validation fail | "Can't proceed until fixed" |
| Grey | Pending, not yet reached | "Not here yet" |

**REQ-UI-007:** Enterprise visual quality — clean, professional, not startup-casual. Think Notion/Linear tier — modern enterprise, not legacy enterprise.

### 19.7 Animation & Feedback

**REQ-UI-008:** All AI processing steps show animated progress:
- Named processing steps (not generic spinners)
- Sequential step animation with realistic timing (500ms–2s per step)
- Completion indicators per step

**REQ-UI-009:** Field population animates — values appear to "fill in" rather than appearing instantly.

**REQ-UI-010:** Confidence indicators animate smoothly.

**REQ-UI-011:** Completeness meter animates from before to after values.

**REQ-UI-026:** Toast notifications for user actions — brief, non-blocking: "Field approved", "Value saved", "Correction queued for KB review".

### 19.8 Enterprise Detail Layer (Expandable)

**REQ-UI-012:** Every AI output includes the enterprise transparency bar — but collapsed by default. Content team sees the simple view. Admin/demo viewers can expand to see model + layer + rule + confidence.

**REQ-UI-013:** Expandable/collapsible panels for detailed breakdowns — default to summary view, expand for detail.

**REQ-UI-014:** Tooltips for all Iksula-specific terminology and model names.

**REQ-UI-027:** A global toggle: "Show technical details" — when on, all enterprise detail is expanded by default. Useful for demos and admin users. Off by default for content team.

### 19.9 Keyboard Shortcuts (Power Users)

**REQ-UI-028:** Keyboard shortcuts for fast processing:

| Shortcut | Action |
|---|---|
| `Tab` | Move to next field needing review |
| `Enter` | Approve current field |
| `E` | Enter edit mode on current field |
| `Shift+Enter` | Approve all & continue to next stage |
| `Esc` | Cancel edit |
| `?` | Show keyboard shortcut help |

### 19.10 Responsive Behaviour

**REQ-UI-015:** Primary target: desktop (1440px+). Must be usable at 1024px. Mobile is not required.

---

## 20. Non-Functional Requirements

### 20.1 Performance

**REQ-NFR-001:** All simulated AI steps should have realistic but not frustrating timing:
- Simple field extraction: 500ms–1s per field
- Classification: 1–2s total
- Dedup match checks: 1–2s per method (4 methods = 4–8s total)
- Enrichment per field: 500ms–1s
- Validation: 1–2s total
- Template mapping animation: 2–3s

**REQ-NFR-002:** UI must remain responsive during simulated processing (no blocking).

### 20.2 Demo Reliability

**REQ-NFR-003:** All demo data is hardcoded. No external API calls. No network dependencies.

**REQ-NFR-004:** Demo must run with a simple `docker-compose up` or `npm run dev` (frontend) + `python -m uvicorn main:app` (backend). Supabase can run locally via `supabase start`.

**REQ-NFR-005:** Demo scenario must be repeatable — same inputs produce same outputs every time.

### 20.3 Data Integrity

**REQ-NFR-006:** Product record state must persist across stage navigation. Going back to Stage 2 and returning to Stage 5 must not lose Stage 5 data.

**REQ-NFR-007:** All fields remain editable until the record is published. Auto-approved fields show a green check but can still be clicked and edited — editing changes the status from "auto_approved" to "human_edited" and triggers re-validation of downstream stages. After publish, records can only be unlocked by Admin for re-editing (creates a new version).

### 20.4 Audit Compliance

**REQ-NFR-008:** Full audit trail per field is mandatory. Every value change — extraction, enrichment, validation, human override — must be logged with timestamp and actor.

**REQ-NFR-009:** Audit trail must be exportable as part of the record export (CSV/JSON/XML).

---

## 21. Glossary

| Term | Definition |
|---|---|
| **PC2** | Product Content Creator — Iksula's AI platform for product data processing |
| **HIL** | Human-in-the-Loop — manual review step for low-confidence AI outputs |
| **DIM** | Dimensions — physical measurements and units of a product |
| **PIM** | Product Information Management — retailer's system for managing product catalog data |
| **THD** | The Home Depot |
| **SiteOne** | SiteOne Landscape Supply |
| **KB** | Knowledge Base — Iksula's proprietary retail domain knowledge base |
| **Dedup** | Deduplication — detecting whether an incoming product already exists in the catalog |
| **SKU** | Stock Keeping Unit |
| **UPC** | Universal Product Code (12-digit barcode) |
| **EAN** | European Article Number (13-digit barcode) |
| **OCR** | Optical Character Recognition |
| **Taxonomy** | Hierarchical classification structure: Department → Category → Class → Sub-class |
| **Picklist** | Controlled vocabulary of accepted values for a given attribute within a product class |
| **Confidence score** | Composite 0–100 metric from source reliability + consistency + completeness |
| **Auto-approved** | Fields with confidence ≥ 85, locked without human review |
| **Iksula IP** | Proprietary Iksula intellectual property — models, taxonomies, templates, rules |
| **Template transformation** | Mapping PC2 internal fields to retailer-specific output format |
| **Supabase** | Open-source Firebase alternative providing PostgreSQL, auth, storage, and realtime subscriptions |
| **pgvector** | PostgreSQL extension for storing and querying vector embeddings for similarity search |
| **FastAPI** | Python web framework for building APIs — async-first, high performance |
| **Model Registry** | Central catalog of all AI/ML models available to the pipeline — Iksula, third-party, and client-provided |
| **Model Adapter** | Standardised interface that wraps any AI model so pipeline stages interact with all models identically |
| **Pipeline Config** | Per-client configuration defining which stages are enabled, their order, and per-stage settings |
| **Stage Processor** | A modular unit implementing one pipeline stage — can be enabled/disabled/replaced independently |
| **Integration Gateway** | Middleware layer handling all external system connections — PIM, supplier portals, AI services |
| **RLS** | Row-Level Security — Supabase/PostgreSQL feature that restricts data access per user role at the database level |
| **Circuit Breaker** | Pattern that disables calls to a failing external service to prevent cascade failures |
| **Webhook** | HTTP callback triggered by system events — allows external systems to react to PC2 state changes |
| **EDI** | Electronic Data Interchange — standard format for B2B data exchange (ANSI X12 / EDIFACT) |

---

*Document generated: 2026-03-22*
*PC2 v2.0 Requirements — Draft*
