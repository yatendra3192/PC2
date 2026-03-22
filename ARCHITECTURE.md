# PC2 v2.0 — Technical Architecture

**Version:** 2.0
**Date:** 2026-03-22
**Status:** Draft

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      USERS                                      │
│         Admin · Reviewer · Viewer (Browser)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS
┌────────────────────────┴────────────────────────────────────────┐
│                   FRONTEND — React 18                            │
│                   Tailwind CSS · Vite                            │
│                   Hosted on Vercel / Cloudflare                  │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST API + WebSocket
┌────────────────────────┴────────────────────────────────────────┐
│                   BACKEND — Python FastAPI                       │
│                   Hosted on Railway / AWS ECS                    │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ Pipeline  │ │ Model    │ │ Web      │ │ Job Queue         │  │
│  │ Engine    │ │ Router   │ │ Scraper  │ │ (Celery + Redis)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐
│  Supabase     │ │  Redis      │ │  External   │
│  PostgreSQL   │ │  Cache +    │ │  Services   │
│  pgvector     │ │  Queue      │ │  (AI/PIM/   │
│  Storage      │ │  Broker     │ │   DQ/Web)   │
│  Auth + RLS   │ │             │ │             │
└───────────────┘ └─────────────┘ └─────────────┘
```

**One sentence:** React frontend talks to a FastAPI backend that orchestrates a modular 7-stage pipeline, stores everything in Supabase, and calls external AI models + web scrapers through a unified adapter layer.

---

## 2. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Frontend** | React 18, Tailwind CSS, Vite | Fast dev, component-based, utility CSS |
| **State** | Zustand | Simple global state, no boilerplate |
| **API client** | TanStack Query | Caching, retries, real-time invalidation |
| **Realtime** | Supabase Realtime (WebSocket) | Live progress updates without polling |
| **Backend** | Python 3.12, FastAPI | Async, fast, great for AI/ML workloads |
| **Task queue** | Celery + Redis | Background processing for batches |
| **Database** | Supabase (PostgreSQL 15) | Managed, RLS, realtime built-in |
| **Vector DB** | pgvector (in Supabase) | Embeddings for dedup, no separate service |
| **File storage** | Supabase Storage (S3-compatible) | PDFs, images, exports |
| **Auth** | Supabase Auth + JWT | Roles, RLS, SSO (SAML/OIDC) |
| **Cache** | Redis | Model response cache, rate limiting |
| **Web scraping** | Playwright + BeautifulSoup | JS-rendered pages + HTML parsing |
| **Search API** | SerpAPI | Google search results for enrichment |
| **Deployment** | Docker, Railway / AWS ECS | Containerised, scalable |

---

## 3. Project Structure

```
pc2/
├── frontend/                  # React app
│   ├── src/
│   │   ├── components/        # Shared UI components
│   │   ├── pages/             # Route pages (Dashboard, Upload, Review, Admin...)
│   │   ├── stages/            # Stage 1-7 UI components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── stores/            # Zustand stores
│   │   ├── api/               # API client (TanStack Query)
│   │   └── utils/             # Helpers, formatters
│   ├── public/
│   ├── index.html
│   ├── tailwind.config.js
│   └── package.json
│
├── backend/                   # FastAPI app
│   ├── app/
│   │   ├── main.py            # FastAPI entry point
│   │   ├── config.py          # Settings, env vars
│   │   ├── models/            # Pydantic models (request/response)
│   │   ├── db/                # Supabase client, SQL queries
│   │   ├── auth/              # Auth middleware, role checks
│   │   ├── pipeline/          # Pipeline engine
│   │   │   ├── orchestrator.py    # Runs stages in sequence
│   │   │   ├── base.py            # StageProcessor interface
│   │   │   ├── stage_1_ingest.py
│   │   │   ├── stage_2_classify.py
│   │   │   ├── stage_3_dedup.py
│   │   │   ├── stage_4_enrich.py
│   │   │   ├── stage_5_validate.py
│   │   │   ├── stage_6_transform.py
│   │   │   └── stage_7_review.py
│   │   ├── ai/                # Model integration
│   │   │   ├── router.py          # Model routing + fallback
│   │   │   ├── registry.py        # Model registry (DB-backed)
│   │   │   ├── adapters/          # One adapter per provider
│   │   │   │   ├── openai.py
│   │   │   │   ├── anthropic.py
│   │   │   │   ├── iksula_ocr.py
│   │   │   │   ├── iksula_vision.py
│   │   │   │   ├── iksula_kb.py
│   │   │   │   └── generic_rest.py  # For client custom models
│   │   │   └── prompts/           # Prompt templates (loaded from DB)
│   │   ├── scraper/           # Web attribute extraction
│   │   │   ├── google.py          # SerpAPI search
│   │   │   ├── marketplace.py     # Amazon/retailer scraping
│   │   │   ├── extractor.py       # HTML → structured attributes
│   │   │   └── mapper.py          # Raw scrape → template fields
│   │   ├── dq/                # Data Quality integration
│   │   │   └── client.py         # Athena DQ API client
│   │   ├── integrations/      # PIM, supplier connectors
│   │   │   ├── pim.py
│   │   │   └── supplier.py
│   │   ├── tasks/             # Celery background tasks
│   │   │   ├── batch_processor.py
│   │   │   └── scrape_worker.py
│   │   └── routes/            # API endpoints
│   │       ├── products.py
│   │       ├── batches.py
│   │       ├── review.py
│   │       ├── admin.py
│   │       └── webhooks.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── supabase/                  # Database
│   ├── migrations/            # SQL migration files
│   ├── seed.sql               # Demo data
│   └── config.toml
│
├── docker-compose.yml         # Full local dev stack
└── README.md
```

---

## 4. Database Schema

> **Full schema in [`DATABASE_SCHEMA.md`](./DATABASE_SCHEMA.md)** — 20 tables with complete SQL, examples, and queries.

### The Three-Layer Model (critical concept)

```
Layer 0: Raw Supplier             Layer 1: Iksula Normalised        Layer 2: Client Normalised
(as received, immutable)          (canonical, standardised)          (retailer output)
─────────────────────             ─────────────────────────          ──────────────────────────
"Wt": "0.8 lbs"       ──norm──►  weight_kg = 0.36          ──map──►  Weight (lbs) = "0.79"
"Clr": "GRY"           ──norm──►  colour = "grey"           ──map──►  Product Color = "Gray"
"Op Temp": "32-122F"   ──norm──►  temp_min_c=0, max_c=50   ──map──►  Temp Range = "32–122°F"
```

- **Layer 0:** `product_raw_values` — original supplier data, never modified. Linked via `supplier_field_mappings` to Layer 1.
- **Layer 1:** `product_iksula_values` — normalised, class-specific, enriched. The single source of truth.
- **Layer 2:** `product_client_values` — transformed via `client_field_mappings` + `client_value_mappings`.
- Each layer has its own mapping tables. Mappings are auto-generated, human-correctable, and reusable.

### Table Summary (20 tables)

| Group | Count | Tables |
|---|---|---|
| **Layer 0 — Raw** | 3 | `supplier_templates`, `supplier_field_mappings`, `product_raw_values` |
| **Layer 1 — Iksula** | 4 | `taxonomy_nodes`, `iksula_class_attributes`, `iksula_allowed_values`, `product_iksula_values` |
| **Layer 2 — Client** | 4 | `taxonomy_client_labels`, `client_field_mappings`, `client_value_mappings`, `product_client_values` |
| **Product Core** | 2 | `products`, `product_embeddings` |
| **Operations** | 2 | `batches`, `audit_trail` |
| **Config** | 5 | `clients`, `retailer_templates`, `pipeline_configs`, `model_registry`, `prompt_templates` |

### Row-Level Security

```sql
-- Admins see all products for their client
CREATE POLICY admin_all ON products FOR ALL
  USING (client_id IN (SELECT client_id FROM users WHERE id = auth.uid() AND role = 'admin'));

-- Reviewers see products in review status
CREATE POLICY reviewer_review ON products FOR SELECT
  USING (status IN ('review','processing') AND client_id IN (SELECT client_id FROM users WHERE id = auth.uid()));

-- Viewers see published only
CREATE POLICY viewer_published ON products FOR SELECT
  USING (status = 'published' AND client_id IN (SELECT client_id FROM users WHERE id = auth.uid()));
```

---

## 5. API Design

### 5.1 REST Endpoints

All prefixed with `/api/v1`.

**Products**
```
POST   /products                  # Create single product
GET    /products                  # List products (filtered, paginated)
GET    /products/:id              # Get product with Iksula normalised values + provenance
GET    /products/:id/client-values/:client_id  # Get client-transformed values
PATCH  /products/:id              # Update product fields (inline edit)
POST   /products/:id/advance      # Move to next stage
POST   /products/:id/approve-all  # Approve all fields at current stage
POST   /products/:id/publish      # Publish to client PIM
```

**Batches**
```
POST   /batches/upload            # Upload file(s), create batch
GET    /batches                   # List batches
GET    /batches/:id               # Batch detail + item statuses
POST   /batches/:id/retry         # Retry failed batch
DELETE /batches/:id               # Cancel/delete batch
```

**Review (HIL)**
```
GET    /review/queue              # Filterable review queue (cross-product)
POST   /review/approve            # Bulk approve items
POST   /review/reject             # Bulk reject with reasons
POST   /review/:field_id/edit     # Edit + approve single field
POST   /review/:field_id/override # Override DQ failure with reason
```

**Taxonomy & Attributes**
```
GET    /taxonomy/tree             # Full taxonomy hierarchy
GET    /taxonomy/:node_id/attributes  # Iksula class attributes for a node
GET    /taxonomy/:node_id/allowed-values/:attr_id  # Picklist for an attribute
POST   /taxonomy/attributes       # Add new attribute to a class (admin)
PUT    /taxonomy/attributes/:id   # Update attribute definition (admin)
```

**Client Mappings**
```
GET    /mappings/:client_id/:node_id        # Get all field mappings for a class + client
PUT    /mappings/:mapping_id                # Correct/update a field mapping
POST   /mappings/:mapping_id/value-map      # Add/update a value mapping
GET    /mappings/:client_id/unmapped        # Get all unmapped fields for a client
POST   /mappings/auto-generate/:client_id/:node_id  # Auto-generate mappings for a class
```

**Admin**
```
GET    /admin/users               # List users
POST   /admin/users/invite        # Invite new user
PATCH  /admin/users/:id           # Update user role/status
GET    /admin/confidence/:stage   # Get confidence config for stage
PUT    /admin/confidence/:stage   # Update confidence config
GET    /admin/models              # List registered models
POST   /admin/models              # Register new model
GET    /admin/templates           # List retailer templates
PUT    /admin/pipeline            # Update pipeline stage config
GET    /admin/audit               # Query audit logs
```

### 5.2 DQ Integration APIs

PC2 calls the external Athena DQ system. These are the APIs between them.

**PC2 → Athena DQ (outbound calls)**
```
POST   {DQ_URL}/check             # Send stage output for quality check
  Request:
    {
      "product_id": "uuid",
      "stage": 4,
      "client_id": "siteone-uuid",
      "taxonomy_class": "HW-IRR-CTRL-SMART",
      "fields": [
        { "attribute_code": "weight_kg", "value": 0.36, "unit": "kg", "source": "web_google" },
        { "attribute_code": "colour", "value": "grey", "source": "vision" }
      ]
    }
  Response:
    {
      "results": [
        { "attribute_code": "weight_kg", "status": "pass", "message": "Within range" },
        { "attribute_code": "colour", "status": "warning", "message": "Value not in DQ preferred list", "suggestion": "Verify against physical sample" }
      ],
      "overall_status": "pass_with_warnings",
      "dq_version": "2.4.1"
    }

GET    {DQ_URL}/rules/:class_code  # Get DQ rules for a class (for display in admin)
GET    {DQ_URL}/stats              # Get DQ pass rates and trends
```

**Athena DQ → PC2 (inbound webhooks)**
```
POST   /api/v1/webhooks/dq/rule-update    # DQ notifies PC2 when rules change
POST   /api/v1/webhooks/dq/recheck        # DQ requests re-check of specific products
```

**PC2 Override API (internal)**
```
POST   /api/v1/dq/override
  Request:
    {
      "product_id": "uuid",
      "attribute_code": "weight_kg",
      "dq_result_id": "uuid",
      "override_reason": "supplier_confirmed",
      "override_note": "Confirmed with Orbit spec sheet — lightweight electronic unit"
    }
  Response:
    { "status": "overridden", "audit_id": "uuid" }

GET    /api/v1/dq/stats                   # DQ stats for admin dashboard
GET    /api/v1/dq/overrides               # List all overrides (audit)
GET    /api/v1/dq/config                  # Get DQ integration config
PUT    /api/v1/dq/config                  # Update DQ integration config
```

### 5.3 PIM Integration APIs

PC2 publishes records to retailer PIM systems.

**PC2 → SiteOne PIM**
```
POST   {SITEONE_PIM_URL}/products/stage    # Push record to staging catalog
  Request:
    {
      "template_version": "2.4",
      "product": {
        "Product Short Title": "Orbit Smart Irrigation Controller",
        "SKU": "B-0624W",
        "Weight (lbs)": "0.79",
        "Zone Count": "6",
        ...all client_field_mappings applied
      },
      "metadata": {
        "pc2_product_id": "uuid",
        "overall_confidence": 93,
        "fields_human_edited": 1,
        "published_by": "reviewer@iksula.com"
      }
    }
  Response:
    { "status": "accepted", "siteone_item_id": "SO-12345", "catalog": "staging" }

POST   {SITEONE_PIM_URL}/products/publish  # Promote staging → production
GET    {SITEONE_PIM_URL}/products/:id/status  # Check acceptance status
GET    {SITEONE_PIM_URL}/catalog/export    # Pull existing catalog for dedup matching
```

**PC2 → THD PIM**
```
POST   {THD_PIM_URL}/items/submit          # Submit batch of records
  Request:
    {
      "format": "xml",
      "template_version": "6.1",
      "items": [ ...client-transformed product records... ]
    }
  Response:
    { "submission_id": "THD-2026-0322-001", "status": "queued", "estimated_review": "2h" }

GET    {THD_PIM_URL}/items/:submission_id/status  # Check submission status
```

**PIM → PC2 (inbound webhooks)**
```
POST   /api/v1/webhooks/pim/status-update
  -- PIM notifies PC2 when a submitted record is accepted/rejected
  Request:
    {
      "pc2_product_id": "uuid",
      "pim_status": "accepted",           -- or "rejected"
      "pim_item_id": "SO-12345",
      "rejection_reason": null,           -- or "Missing mandatory field: ..."
      "timestamp": "2026-03-22T15:00:00Z"
    }

POST   /api/v1/webhooks/pim/catalog-update
  -- PIM notifies PC2 when catalog changes (for dedup sync)
```

### 5.4 WebSocket Events

Frontend subscribes to Supabase Realtime for live updates:

```
products:stage_update     -- Product moved to next stage
products:field_update     -- A field was enriched/validated
products:dq_result        -- DQ check completed for a product
products:pim_status       -- PIM accepted/rejected a record
batches:progress          -- Batch processing progress %
review:new_item           -- New item added to review queue
mappings:corrected        -- A field mapping was corrected (re-transform needed)
```

---

## 6. Pipeline Engine

### 6.1 How It Works

```python
# backend/app/pipeline/orchestrator.py

class PipelineOrchestrator:

    async def run(self, product_id: str):
        product = await db.get_product(product_id)
        config = await db.get_pipeline_config(product.client_id)

        for stage_num in config.active_stages:    # e.g. [1, 2, 3, 4, 5, 6, 7]
            processor = self.get_processor(stage_num)

            # Run stage
            result = await processor.process(product, config.stage_configs[stage_num])

            # Save output
            product.stage_data[stage_num] = result.output
            product.field_provenance.update(result.provenance)
            product.current_stage = stage_num
            await db.save_product(product)

            # Run DQ check (if enabled for this stage)
            if config.dq_enabled(stage_num):
                dq_result = await dq_client.check(product, stage_num)
                product.dq_results[stage_num] = dq_result
                await db.save_product(product)

            # Emit realtime update
            await realtime.emit('products:stage_update', product.id, stage_num)

            # Check if HIL review needed
            if result.has_items_needing_review():
                product.status = 'review'
                await db.save_product(product)
                return  # Pause — human reviews, then calls /advance to continue

        # All stages done
        product.status = 'review'  # Final review before publish
        await db.save_product(product)
```

### 6.2 Stage Processor Interface

Every stage implements this:

```python
# backend/app/pipeline/base.py

class StageProcessor(ABC):

    @abstractmethod
    async def process(self, product: Product, config: dict) -> StageResult:
        """Run this stage. Return output fields + provenance."""
        pass

    @abstractmethod
    def required_models(self) -> list[str]:
        """Which AI models does this stage need?"""
        pass
```

### 6.3 Stage → Component Map

| Stage | Processor | Models Used | Key Action |
|---|---|---|---|
| 1 | `stage_1_ingest.py` | OCR Engine, GPT-4o, Vision | Parse uploaded file → extract fields |
| 2 | `stage_2_classify.py` | Taxonomy Model | Assign dept/cat/class/subclass |
| 3 | `stage_3_dedup.py` | Dedup Model, pgvector | Vector similarity search in catalog |
| 4 | `stage_4_enrich.py` | KB, GPT-4o, Vision, Web Scraper | Fill blanks from KB + LLM + web |
| 5 | `stage_5_validate.py` | DIM Validator | Check units, ranges, mandatory fields |
| 6 | `stage_6_transform.py` | — (rule-based) | Map to retailer template fields |
| 7 | `stage_7_review.py` | — (human) | Final review queue + publish |

---

## 7. Model Router

### How model selection works

```python
# backend/app/ai/router.py

class ModelRouter:

    async def invoke(self, task: str, input: dict, client_id: str) -> ModelOutput:
        """
        1. Check if client has a custom model for this task
        2. Fall back to Iksula default
        3. Fall back to generic (OpenAI/Anthropic)
        4. If all fail → route to HIL
        """
        models = await self.registry.get_models_for_task(task, client_id)

        for model in models:  # Ordered by priority
            try:
                adapter = self.get_adapter(model)
                result = await adapter.invoke(input)

                # Log the call
                await self.log_invocation(model, task, result)

                return result
            except (Timeout, ModelError):
                continue  # Try next in fallback chain

        # All models failed
        return ModelOutput(status='failed', route_to_hil=True)
```

### Adapter pattern

```python
# Every AI provider gets one adapter file

class OpenAIAdapter(ModelAdapter):
    async def invoke(self, input: ModelInput) -> ModelOutput:
        response = await openai.chat.completions.create(
            model=self.model_name,
            messages=input.to_messages()
        )
        return ModelOutput(
            value=response.choices[0].message.content,
            model_name=self.model_name,
            tokens_used=response.usage.total_tokens,
            latency_ms=response.response_ms
        )

class GenericRESTAdapter(ModelAdapter):
    """For client-provided models — just hits their REST endpoint."""
    async def invoke(self, input: ModelInput) -> ModelOutput:
        response = await httpx.post(self.endpoint_url, json=input.to_dict(), headers=self.auth_headers)
        return ModelOutput.from_response(response.json())
```

---

## 8. Web Scraper

### Flow

```
Product identifier (SKU/EAN/title)
         │
         ├──► SerpAPI (Google search)
         │         │
         │         ├──► URL 1 → Playwright render → BeautifulSoup parse → extract attrs
         │         ├──► URL 2 → same
         │         └──► URL 3 → same
         │
         └──► Amazon search (via scraper)
                   │
                   ├──► Result 1 → parse title + bullets + specs table
                   ├──► Result 2 → same
                   └──► ... up to 10

All extracted attributes → mapper.py → retailer template fields
```

### Key files

```python
# backend/app/scraper/google.py
class GoogleScraper:
    async def search(self, query: str, max_urls: int = 3) -> list[str]:
        """Google search via SerpAPI, return top N URLs."""
        results = await serpapi.search(q=query, num=max_urls)
        return [r['link'] for r in results['organic_results'][:max_urls]]

    async def scrape_url(self, url: str) -> dict:
        """Render page with Playwright, extract structured data."""
        page = await browser.new_page()
        await page.goto(url, timeout=10000)
        html = await page.content()
        return extractor.extract_product_attrs(html)

# backend/app/scraper/extractor.py
class AttributeExtractor:
    def extract_product_attrs(self, html: str) -> dict:
        """Parse HTML, find spec tables, bullet points, product details."""
        soup = BeautifulSoup(html, 'html.parser')
        attrs = {}
        # Find spec tables (<table>, <dl>, key-value divs)
        # Find bullet point lists
        # Find structured data (JSON-LD, schema.org)
        return attrs

# backend/app/scraper/mapper.py
class TemplateMapper:
    async def map_to_template(self, raw_attrs: dict, template_id: str) -> dict:
        """Map scraped raw values to retailer template fields."""
        template = await db.get_template(template_id)
        mapped = {}
        for raw_key, raw_value in raw_attrs.items():
            field = self.match_field(raw_key, template.field_mappings)
            if field:
                mapped[field] = self.normalise_value(raw_value, template.field_formats[field])
        return mapped
```

---

## 9. Background Jobs

### What runs in the background (Celery + Redis)

| Job | Trigger | What it does |
|---|---|---|
| `process_batch` | File upload | Parse file, create product records, run pipeline per item |
| `scrape_product` | Stage 4 starts | Google search + Amazon scrape for one product |
| `run_dq_check` | Stage completes | Call Athena DQ API, store results |
| `generate_embeddings` | Stage 1 completes | Generate vector embedding for dedup |
| `export_records` | User clicks export | Generate CSV/XML/JSON file, store in Supabase Storage |

### Worker setup

```python
# backend/app/tasks/batch_processor.py

@celery.task
def process_batch(batch_id: str):
    batch = db.get_batch(batch_id)
    items = parser.parse_file(batch.file_path, batch.file_type)

    for item_data in items:
        product = db.create_product(batch_id=batch_id, raw_data=item_data)
        pipeline.run.delay(product.id)  # Each item runs async

    batch.status = 'processing'
    db.save_batch(batch)
```

---

## 10. Auth & Roles

### How it works

```
User logs in → Supabase Auth → JWT token with role claim
                                    │
Frontend includes JWT in every API call
                                    │
FastAPI middleware verifies JWT, extracts role
                                    │
                      ┌─────────────┴─────────────┐
                      │                           │
              API-level checks              DB-level checks
              (FastAPI depends)             (Supabase RLS)
              e.g. only admin               e.g. viewer only
              can POST /admin/*             sees published rows
```

### Role → Permissions

| Action | Admin | Reviewer | Viewer |
|---|---|---|---|
| Upload batches | Yes | No | No |
| Configure pipeline/models/confidence | Yes | No | No |
| Manage users | Yes | No | No |
| Review + approve/edit fields | Yes | Yes | No |
| Override DQ failures | Yes | Yes | No |
| View published records | Yes | Yes | Yes |
| Export data | Yes | Yes | Yes |

---

## 11. Data Flow — End to End

Here's one product going through the entire system:

```
1. Admin uploads "Orbit_Catalog.csv" via /batches/upload
   → File stored in Supabase Storage
   → Batch record created (status: queued)
   → Celery task: process_batch(batch_id)

2. Batch processor parses CSV → 142 product rows
   → Creates 142 product records (status: draft)
   → Queues pipeline.run(product_id) for each

3. Stage 1 — Ingest
   → OCR/CSV parser extracts fields
   → Saves to product.stage_data["1"]
   → Logs provenance per field
   → DQ check → pass
   → Fields with confidence ≥ 90 auto-approved
   → Product advances to Stage 2

4. Stage 2 — Classify
   → Taxonomy model assigns dept/cat/class/subclass
   → Confidence 94% → auto-approved
   → DQ check → pass
   → Advances to Stage 3

5. Stage 3 — Dedup
   → Generate embedding → pgvector similarity search
   → 78% match found → "Possible variant"
   → status = 'review' → PAUSED
   → Reviewer gets notification in HIL queue
   → Reviewer clicks "Keep as variant" → /products/:id/advance
   → Advances to Stage 4

6. Stage 4 — Enrich
   → KB lookup fills 3 fields
   → LLM inference fills 1 field
   → Web scraper: Google (3 URLs) + Amazon (10 results)
   → Scraped attrs mapped to SiteOne template
   → Multi-source agreement boosts confidence
   → 1 field at 72% confidence → needs review
   → DQ check → pass
   → status = 'review' → PAUSED
   → Reviewer approves the 72% field → /advance
   → Advances to Stage 5

7. Stage 5 — Validate
   → Unit normalisation (lbs→kg, °F→°C)
   → Range checks pass
   → Shipping weight MISSING → mandatory fail
   → DQ check → fail (weight below minimum)
   → status = 'review' → PAUSED
   → Reviewer enters shipping weight + overrides DQ
   → Advances to Stage 6

8. Stage 6 — Transform
   → Map all fields to SiteOne Template v2.4
   → 98% auto-mapped, 2 need manual mapping
   → Reviewer maps 2 fields → /advance
   → Advances to Stage 7

9. Stage 7 — Final Review
   → Shows complete record, all provenance
   → Reviewer clicks "Publish to SiteOne Staging"
   → POST /products/:id/publish
   → Record exported as CSV → pushed to SiteOne PIM API
   → status = 'published'
   → Audit trail complete
```

---

## 12. Deployment

### Local development

```bash
# Start everything
docker-compose up

# This runs:
# - Supabase (PostgreSQL + Auth + Storage + Realtime) on :54321
# - Redis on :6379
# - FastAPI backend on :8000
# - Celery worker (connects to Redis)
# - React frontend on :5173 (Vite dev server)
```

### docker-compose.yml (simplified)

```yaml
services:
  supabase-db:
    image: supabase/postgres:15
    ports: ["54322:5432"]
    environment:
      POSTGRES_PASSWORD: postgres
    volumes:
      - ./supabase/migrations:/docker-entrypoint-initdb.d

  supabase-api:
    image: supabase/gotrue
    depends_on: [supabase-db]
    ports: ["54321:8080"]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [supabase-db, redis]
    environment:
      DATABASE_URL: postgresql://postgres:postgres@supabase-db:5432/postgres
      REDIS_URL: redis://redis:6379
      SUPABASE_URL: http://supabase-api:8080
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      SERPAPI_KEY: ${SERPAPI_KEY}

  celery-worker:
    build: ./backend
    command: celery -A app.tasks worker --loglevel=info
    depends_on: [backend, redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]
```

### Production deployment

```
Frontend  → Vercel (or Cloudflare Pages)
Backend   → AWS ECS (or Railway) — auto-scaling containers
Supabase  → Supabase Cloud (managed) — Pro plan
Redis     → Upstash Redis (serverless) or AWS ElastiCache
Celery    → Same ECS cluster, separate service
CDN       → Cloudflare (for frontend assets)
```

### Environment variables

```
# Database
DATABASE_URL=postgresql://...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# AI Models
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Web scraping
SERPAPI_KEY=...
SCRAPER_PROXY_URL=...

# DQ Integration
ATHENA_DQ_URL=https://dq.iksula.com/api/v2
ATHENA_DQ_API_KEY=...

# Queue
REDIS_URL=redis://...

# PIM Integration
SITEONE_PIM_URL=...
SITEONE_PIM_KEY=...
THD_PIM_URL=...
THD_PIM_KEY=...
```

---

## 13. Security

| Concern | Solution |
|---|---|
| Auth | Supabase Auth with JWT. SSO via SAML/OIDC for enterprise. |
| API keys | Never in frontend. Backend only. Stored in env vars / secret manager. |
| Data access | Row-Level Security in PostgreSQL. Users only see their client's data. |
| File uploads | Scanned for malware. Size limits enforced. Signed URLs for access. |
| API rate limiting | Per-user rate limits via Redis. |
| Audit | Every action logged with user, timestamp, old/new values. Append-only. |
| Encryption | TLS in transit. Supabase encrypts at rest. |
| CORS | Frontend domain only. |

---

## 14. Scaling Considerations

| Bottleneck | Solution |
|---|---|
| Large batch (1000+ items) | Celery workers process items in parallel. Auto-scale workers based on queue depth. |
| AI model latency | Model response caching in Redis. Parallel model calls where independent. |
| Web scraping speed | Scrape URLs in parallel (3 concurrent). Proxy rotation for rate limits. |
| Vector search (dedup) | pgvector with IVFFlat index. For >10M products, consider HNSW index or dedicated vector DB. |
| File storage | Supabase Storage is S3-backed. No practical limit. |
| Concurrent users | FastAPI is async. Handles 1000+ concurrent connections per instance. |

---

## 15. Monitoring

| What | Tool |
|---|---|
| API health + latency | Sentry (errors) + Datadog or PostHog (metrics) |
| Background job status | Celery Flower dashboard |
| Database performance | Supabase Dashboard (built-in) |
| AI model costs | Custom logging → dashboard (tokens used, cost per call) |
| DQ pass rates | Athena DQ dashboard + PC2 admin panel |
| Uptime | Better Uptime or similar |

---

*Document generated: 2026-03-22*
*PC2 v2.0 Technical Architecture — Draft*
