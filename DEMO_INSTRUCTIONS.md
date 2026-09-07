# Verisk Claims Concierge AI — Demo Instructions
**TA Panel Interview | ~20 Minutes**

---

## Pre-Demo Setup (Do this 10 minutes before)

```bash
# 1. Add your Anthropic API key to .env
#    Open ~/verisk-demo/.env and set:
ANTHROPIC_API_KEY=sk-ant-your-key-here

# 2. Start the demo from the project root
cd ~/verisk-demo
.venv/bin/python -m app.main
```

You should see:
```
[setup] Database initialized.
✓ Database seeded: 3 claims, 2 contractors, 2 adjusters...
[setup] Knowledge base initialized.
[setup] Mock APIs ready on ports 8001 (Weather) and 8002 (AccuLynx).
```

The terminal will show the Verisk header panel and a command prompt `>`.

**Keep a second terminal tab open** — if anything breaks, you can restart with the same command.

---

## The 20-Minute Flow

| Segment | Time | What You Cover |
|---|---|---|
| Business Problem | 4 min | Who Verisk is, the CDO problem, why it matters |
| Architecture Walkthrough | 8 min | System boundary map, Data 360, LangGraph agent |
| Live Demo | 5 min | 3 scenarios in the terminal |
| Handoff & Risks | 3 min | What's next, open questions |

---

## Segment 1 — Business Problem (4 min)

**Say this:**

> "Verisk is the dominant data analytics partner to the global insurance industry — 90% subscription revenue, heavy ML/AI on claims and weather data. They recently acquired AccuLynx, a contractor estimating platform, which is a textbook CDO problem: two systems, two sets of contractor and claim records, no unified view.
>
> The business problem is this: when a contractor calls about a claim, a support rep has to look in three places — the legacy PES system for the claim record, AccuLynx for the estimate, and a separate weather data feed to validate the loss event. That fragmentation slows cycle time. For Verisk's insurer clients, slow cycle times are a churn signal.
>
> The solution is a unified claims concierge — one agent that knows the claim, the contractor, the estimate, and the weather event, and can answer questions from three different personas: the claimant, the contractor, and the adjuster."

---

## Segment 2 — Architecture Walkthrough (8 min)

Walk through this diagram verbally (draw it live or reference your deck):

```
┌─────────────────────────────────────────────────────────────┐
│                      SOURCE SYSTEMS                          │
│                                                             │
│   Legacy PES              AccuLynx (post-acquisition)       │
│   (claim records,         (contractor estimates,            │
│    adjuster/claimant)      work orders)                     │
└────────────────┬──────────────────┬────────────────────────┘
                 │  HARMONIZED      │  HARMONIZED
                 ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA 360 LAYER                            │
│                                                             │
│   Identity Resolution: contractor/adjuster/claim records    │
│   matched across PES + AccuLynx using name, email,          │
│   license ID, claim number as match keys.                   │
│                                                             │
│   Unified Claim Profile:                                    │
│     claim ↔ claimant ↔ adjuster ↔ work order ↔ estimate     │
│                                                             │
│   Calculated Insight: claim cycle time (open → resolved)    │
└──────────────────────────────┬──────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
┌─────────────────────────┐      ┌──────────────────────────┐
│   WEATHER / PROPERTY    │      │     LANGRAPH AGENT        │
│   LOSS DATA API         │      │                           │
│   (NOAA-style feed)     │◄─────│  classify_intent          │
│                         │      │  → retrieve_claim (DB)    │
│   FEDERATED — zero copy │      │  → retrieve_weather (API) │
│   Not stored in Data 360│      │  → retrieve_estimate      │
│   Queried live per claim│      │  → generate_response      │
└─────────────────────────┘      └──────────────┬────────────┘
                                                │
                               ┌────────────────┼────────────────┐
                               ▼                ▼                ▼
                          Claimant         Contractor        Adjuster
                       (own claims)   (assigned claims)  (full book)
```

**Key talking points:**

- **Harmonize vs. federate:** "PES and AccuLynx records are harmonized — ingested, identity-resolved, stored. Weather data is federated — queried live, never persisted. That's a deliberate architectural choice: weather data changes constantly and isn't core identity data."

- **Identity resolution:** "The riskiest part of the Data 360 design is contractor identity. A contractor exists in PES with one ID and in AccuLynx with another. We match on name, email, and license ID with a clear source-of-truth precedence: PES wins for identity fields, AccuLynx wins for estimate values."

- **LangGraph agent:** "This is a standard assisted agent, not autonomous. Given the financial sensitivity of claims, every write action — work orders, invoices — is staged and requires explicit confirmation before executing. The graph has a check_status path and a write path, with persona-scoped access enforced at the data retrieval layer."

- **Riskiest assumption:** "The riskiest assumption in this architecture is whether the agent can accurately pull real-time weather data, merge it with the unified claim profile, and surface a coherent answer — without hallucinating a status or estimate when the external API is unavailable. That's exactly what Demo 3 tests."

---

## Segment 3 — Live Demo (5 min)

### Demo 1 — Claimant: Claim Status (1.5 min)

Type at the `>` prompt:
```
:demo1
```

This auto-runs: Robert Chen (CLM-001) asks for a full status on claim CLM-2024-0891.

**What to narrate while the agent responds:**
> "The agent classifies the intent, retrieves the unified claim profile from Data 360, fans out to the weather API for the loss event at that location and date, pulls the AccuLynx estimate, and then grounds the response in all three sources. You'll notice it cites PES, AccuLynx, and the weather feed separately."

**Point out:** The source attribution line below the response — "Sources: Data 360 / Weather API / PES+AccuLynx."

---

### Demo 2 — Contractor: Work Order Update (1.5 min)

Type:
```
:demo2
```

This auto-runs: Jake Morales (CON-001) submits a progress update on work order WO-2024-0891-A.

**What to narrate:**
> "This is the write path. The agent detects the intent, stages the update, and presents it back for confirmation before writing — that's the human-in-the-loop guardrail. For Phase 1, no write action goes to the system without the user explicitly confirming."

**Point out:** The "PENDING ACTION (requires your confirmation)" block in the response, followed by the auto-confirm step in the demo.

---

### Demo 3 — Adjuster + API Outage (2 min)

Type:
```
:demo3
```

**Step 1:** Adjuster Maria Santos (ADJ-001) asks for her full book.
- Agent returns all claims assigned to her from Data 360.

**Step 2:** The demo pauses and shows a red panel: `PRESENTER ACTION REQUIRED`.

At this point, open your second terminal tab and type:
```
:kill-weather
```
(or just type it in the main demo terminal — the REPL accepts it).

You'll see the weather indicator flip from green `●` to red `●`.

**Step 3:** Press Enter to continue. The agent is asked for a full status on CLM-2024-1023, including weather data.

**What to narrate:**
> "The weather API is now down. Watch what happens — the agent does not make up a weather event. It surfaces the claim data it has, then explicitly states: 'Weather data is currently unavailable — I cannot confirm the loss event context.' That's the guardrail working. In a real deployment, we'd surface a degraded indicator in the UI and trigger an alert to the ops team."

**Then restore:**
```
:restore-weather
```

---

## Segment 4 — Handoff & Risks (3 min)

**What to say:**

> "If this were a real engagement, here's what would come next:
>
> First, productionizing the identity resolution rules in Data 360 — the match logic I've shown is simplified. Real contractor records across PES and AccuLynx will have conflicts, and you need explicit reconciliation rules with a source-of-truth precedence order documented before you go live.
>
> Second, moving from assisted to autonomous. Right now every write requires confirmation. As you validate the agent's accuracy on status lookups, you can progressively unlock autonomous writes for lower-risk actions — evidence uploads first, then work order updates, with invoices staying human-reviewed longest given financial sensitivity.
>
> Third, evaluation. I'd instrument every agent response to log which source fed which part of the answer. Sample those against ground-truth data weekly, especially for claims where the weather API was unavailable — that's where hallucination risk is highest."

---

## Q&A Prep — Likely Panel Questions

**"Why federate weather data instead of ingesting it?"**
> Freshness and volume. Weather data is continuously updated and event-scoped — there's no value in storing it at rest in Data 360 when it changes by the hour. We query it live per claim lookup and discard it. If we ingested it, we'd own a stale copy and a sync problem.

**"How does identity resolution handle conflicting contractor records between PES and AccuLynx?"**
> We define a precedence order: PES is system of record for identity fields (name, email, license ID). AccuLynx is system of record for estimate values. If contact info differs, PES wins. We surface conflicts in a reconciliation queue rather than silently overwriting — an analyst reviews flagged records before they're merged into the unified profile.

**"What happens when the weather API is down mid-conversation?"**
> The agent detects the 503 or timeout in the retrieval node, sets `weather_available = False`, and the response generator has an explicit instruction: if weather is unavailable, state that clearly — do not guess. You saw this in Demo 3. The fallback is also packaged: if the live API is down during a real demo or prod incident, I have a recorded trace of a successful run to fall back to.

**"What's the source of truth for claim status if PES and AccuLynx disagree?"**
> PES is the system of record for claim status. AccuLynx owns estimate values only. We make this explicit in the identity resolution rules and surface it in the agent's response attribution — so an adjuster can always trace a status back to PES and an estimate back to AccuLynx.

**"How is the agent prevented from guessing a status when data is missing?"**
> Two layers. First, the prompt explicitly instructs: never fabricate or guess — if data is unavailable, say so. Second, the retrieval nodes return structured error dicts (`{"error": "..."}`) rather than empty data, and the response generator has explicit handling for each error state. The weather fallback message is hardcoded, not LLM-generated, specifically to prevent a creative model from improvising.

**"How are you leveraging AI in your day-to-day?"**
> "I used Claude Code to build this demo — the agent graph, the mock APIs, the seed data, all of it. I treat it like a senior pair programmer: I drive the architecture and the decisions, it handles the implementation. I also use it to stress-test my own assumptions — I'll describe an architecture choice and ask it to argue against it. That's how I validated the federate-vs-harmonize decision on the weather data."

---

## If Something Goes Wrong

| Problem | Fix |
|---|---|
| Agent returns no response | Check `ANTHROPIC_API_KEY` is set in `.env` |
| Weather API unreachable | It starts automatically with `app.main` — restart if needed |
| Import error on startup | Run `.venv/bin/pip install -r requirements.txt` again |
| DB error | Delete `verisk.db` and restart — seed runs fresh |
| ChromaDB error | Delete `chroma_db/` folder and restart — KB re-ingests |

**Emergency fallback:** If the live demo fails entirely, walk through the architecture diagram and Q&A from memory. The architecture is the core of what they're evaluating — the demo is supporting evidence.

---

## File Structure Reference

```
verisk-demo/
├── app/main.py          ← Entry point (run this)
├── app/demo.py          ← Rich terminal REPL
├── agent/graph.py       ← LangGraph StateGraph
├── agent/nodes.py       ← Node functions (classify, retrieve, generate)
├── agent/tools.py       ← DB + API calls
├── mock_apis/
│   ├── weather_api.py   ← Port 8001 — toggle with :kill-weather
│   └── acculynx_api.py  ← Port 8002
├── db/models.py         ← SQLAlchemy models
├── data/seed_data.py    ← 3 claims, 2 contractors, 2 adjusters
├── knowledge_base/kb.py ← ChromaDB RAG for policy docs
└── .env                 ← Add your ANTHROPIC_API_KEY here
```
