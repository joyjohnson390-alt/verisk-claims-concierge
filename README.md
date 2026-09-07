# Verisk Claims Concierge AI — Builder Handoff

> **Context:** Proof-of-concept built for a Salesforce Technical Architect engagement with Verisk Analytics. Demonstrates a unified property claims concierge powered by a LangGraph agent grounded in harmonized Data 360 profiles and federated weather data.

---

## Business Problem

Verisk's Property Estimating Network is expanding through the AccuLynx acquisition, connecting insurers, contractors, adjusters, and policyholders on one workflow. Claim cycle times are slow because contractor and adjuster support reps must look across three systems — legacy PES, AccuLynx, and a weather/property-loss data feed — with no unified view.

**Solution:** A natural-language claims concierge that grounds every response in a unified claim profile (harmonized from PES + AccuLynx) plus federated real-time weather data, served through persona-scoped access for three user types.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOURCE SYSTEMS                           │
│   Legacy PES                    AccuLynx (post-acquisition)     │
│   claim records, adjuster/      contractor estimates,           │
│   claimant profiles             work orders                     │
└──────────┬──────────────────────────────┬───────────────────────┘
           │  HARMONIZED (ingested)       │  HARMONIZED (ingested)
           ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     DATA 360 LAYER                              │
│  Identity resolution across PES + AccuLynx                      │
│  Unified Claim Profile: claim ↔ claimant ↔ adjuster             │
│                          ↔ work order ↔ estimate ↔ evidence      │
│  Calculated insight: claim cycle time (open → resolved)         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
              ┌────────────────┴─────────────────┐
              │                                  │
              ▼                                  ▼
┌───────────────────────┐          ┌─────────────────────────────┐
│  WEATHER / PROPERTY   │          │       LANGGRAPH AGENT        │
│  LOSS DATA API        │◄─────────│  classify_intent             │
│  (NOAA-style feed)    │          │  → retrieve_claim (DB)       │
│                       │          │  → retrieve_weather (API)    │
│  FEDERATED — zero     │          │  → retrieve_estimate         │
│  copy, queried live   │          │  → generate_response (LLM)   │
└───────────────────────┘          └──────────────┬──────────────┘
                                                  │
                                  ┌───────────────┼───────────────┐
                                  ▼               ▼               ▼
                             Claimant        Contractor       Adjuster
                           own claims     assigned claims   full book
```

**Key architectural decisions:**
- **Harmonize vs. federate:** PES + AccuLynx records are ingested and identity-resolved into unified profiles. Weather data is federated (zero-copy) — queried live per claim, never persisted. Rationale: weather changes continuously and is not core identity data.
- **Identity resolution precedence:** PES wins for identity fields (name, email, license ID). AccuLynx wins for estimate values. Conflicts surface in a reconciliation queue.
- **Assisted (not autonomous) agent:** All write actions (work orders, invoices) are staged and require explicit user confirmation before executing. Given claims/financial sensitivity, Phase 1 is read + confirm-before-write only.
- **Graceful degradation:** When the weather API is unavailable, the agent states this explicitly rather than fabricating a weather event. This is tested as the primary validation scenario.

---

## Project Structure

```
verisk-demo/
├── app/
│   ├── web.py              # FastAPI server — REST API for the chat UI
│   ├── web_main.py         # Entry point for web UI (auto-opens browser)
│   ├── main.py             # Entry point for terminal UI
│   ├── demo.py             # Rich terminal REPL (alternative to web UI)
│   └── static/
│       └── index.html      # Browser chat interface (dark theme, no framework)
├── agent/
│   ├── graph.py            # LangGraph StateGraph — nodes + conditional edges
│   ├── nodes.py            # Node functions: classify, retrieve, stage, generate
│   ├── tools.py            # DB query + API call functions (plain Python)
│   ├── prompts.py          # System prompts per persona + intent classifier
│   └── state.py            # VeriskState TypedDict
├── db/
│   ├── models.py           # SQLAlchemy models: Claim, Contractor, Adjuster,
│   │                       #   WorkOrder, Invoice, Evidence, Claimant
│   └── database.py         # SQLite engine + session factory
├── knowledge_base/
│   └── kb.py               # ChromaDB RAG — ingests policy docs, answers
│                           #   general queries with source attribution
├── mock_apis/
│   ├── weather_api.py      # FastAPI :8001 — mock NOAA weather feed
│   │                       #   POST /admin/toggle simulates outage
│   └── acculynx_api.py     # FastAPI :8002 — mock AccuLynx estimates API
├── data/
│   ├── seed_data.py        # Seeds DB: 3 claims, 2 contractors, 2 adjusters
│   └── knowledge_docs/     # RAG source docs (claims policy, contractor
│                           #   guidelines, adjuster handbook)
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
└── DEMO_INSTRUCTIONS.md    # Full 20-min demo script + Q&A prep
```

---

## LangGraph Agent — Graph Topology

```
START
  └─► classify_intent  (LLM: intent + claim_id extraction)
        ├─► retrieve_claim       (intent has claim_id)
        │     ├─► retrieve_weather   (check_status)
        │     │     └─► retrieve_estimate ─► generate_response ─► END
        │     ├─► stage_write_action (upload_evidence | submit_work_order |
        │     │                       submit_invoice | create_work_order)
        │     │     └─► generate_response ─► END
        │     └─► generate_response  (fallback)  ─► END
        └─► search_knowledge_base   (general_query or no claim_id)
              └─► generate_response ─► END
```

**Intents handled:**
| Intent | Persona | Action |
|---|---|---|
| `check_status` | Any | Read claim + weather + estimate, grounded response |
| `upload_evidence` | Claimant | Stage evidence write, confirm, create Evidence record |
| `submit_work_order` | Contractor | Stage WO status update, confirm, update WorkOrder |
| `submit_invoice` | Contractor | Stage invoice, confirm, create Invoice record |
| `create_work_order` | Adjuster | Stage new WO, confirm, create WorkOrder record |
| `general_query` | Any | RAG search over policy/guideline docs |

---

## Data Model

| Table | Key Fields | Source System |
|---|---|---|
| `claims` | id, status, property_address, loss_lat/lon, loss_date, estimate_amount, source_pes_id, source_acculynx_id | PES (harmonized) |
| `claimants` | id, name, email, phone | PES (harmonized) |
| `contractors` | id, name, company, license_id, source_pes_id, source_acculynx_id | PES + AccuLynx (identity-resolved) |
| `adjusters` | id, name, email, region | PES (harmonized) |
| `work_orders` | id, claim_id, contractor_id, status, description, notes | PES (harmonized) |
| `invoices` | id, work_order_id, amount, status | AccuLynx (harmonized) |
| `evidence` | id, claim_id, filename, description, uploaded_by | PES (harmonized) |

**Identity resolution demo:** `contractors` table carries both `source_pes_id` and `source_acculynx_id` — demonstrating cross-system reconciliation. `CLM-2024-1023` has no `source_acculynx_id` (partial match scenario, not yet in AccuLynx).

---

## Persona Access Control

Enforced in `agent/tools.py → get_claim()` at the data retrieval layer:

| Persona | Access Rule |
|---|---|
| Claimant | Only claims where `claimant_id == user_id` |
| Contractor | Only claims with a `WorkOrder` assigned to `contractor_id == user_id` |
| Adjuster | Only claims where `adjuster_id == user_id` |

---

## Setup

### Prerequisites
- Python 3.9+
- Anthropic API key (workspace-scoped — create at `console.anthropic.com` inside a workspace)

### Install
```bash
git clone https://github.com/joyjohnson390-alt/verisk-claims-concierge.git
cd verisk-claims-concierge
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configure
```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY
# Optional: set ANTHROPIC_WORKSPACE_ID if your key requires it
```

### Run (web UI — recommended)
```bash
python -m app.web_main
# Opens http://localhost:8000 automatically
```

### Run (terminal UI — alternative)
```bash
python -m app.main
```

---

## Demo Scenarios

| Scenario | Persona | What It Shows |
|---|---|---|
| **Demo 1** | Claimant (Robert Chen) | Unified claim status — PES data + AccuLynx estimate + NOAA weather event in one grounded response |
| **Demo 2** | Contractor (Jake Morales) | Write path — work order update staged, confirmed, written to DB |
| **Demo 3** | Adjuster (Maria Santos) | Book review, then weather API killed mid-demo to demonstrate graceful degradation |

Full narration script and Q&A prep: see **[DEMO_INSTRUCTIONS.md](./DEMO_INSTRUCTIONS.md)**

---

## Riskiest Assumption & Validation

**Assumption:** The agent can accurately merge real-time weather data with the unified claim profile without hallucinating a status or estimate when the external API is unavailable.

**Validation (Demo 3):**
- Kill the weather API mid-conversation via the UI toggle
- Agent responds: *"Weather data is currently unavailable — I cannot confirm the loss event context"*
- It does NOT fabricate a weather event
- Source: `agent/prompts.py` — explicit instruction in system prompt; `agent/nodes.py` — hardcoded fallback message bypasses LLM generation for the weather unavailable case

---

## What Stays Outside Salesforce and Why

| System | Owns | Why It Stays External |
|---|---|---|
| AccuLynx | Estimate creation/editing workflow | Specialized tool with its own UX — Salesforce consumes the output, not the workflow |
| Weather/property-loss API | Real-time severe weather truth | Continuously updated, high volume, not core identity data — federated read-only is the right pattern |

---

## Next Steps for Production

1. **Identity resolution hardening** — replace simplified match logic with full reconciliation rules and a conflict queue for adjuster review
2. **Move to Agentforce** — this LangGraph PoC maps directly to Agentforce topics/actions; the agent graph topology → topic definitions, nodes → actions, persona guards → permission scopes
3. **Data 360 wiring** — replace SQLite with actual Data Cloud unified profiles and data graph retriever
4. **Evaluation pipeline** — instrument every agent response with source attribution logging; sample weekly against ground-truth data; flag weather-unavailable sessions for manual review
5. **Autonomous write unlock** — progressively enable autonomous writes: evidence uploads first, then WO updates, with invoices staying human-reviewed

---

## Open Architecture Questions

- How does identity resolution handle conflicting contractor contact info between PES and AccuLynx at scale?
- What's the SLA for weather data freshness — is 503 a hard failure or should the agent queue and retry?
- When PES and AccuLynx disagree on claim status (edge case post-sync), which wins and how is the discrepancy surfaced?
- What's the MuleSoft integration pattern for the weather API callout vs. direct REST — does the integration team have a preferred standard?
