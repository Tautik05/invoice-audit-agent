# Autonomous Invoice Audit & ERP Settlement Agent

A production-oriented agentic system for automating invoice auditing and ERP settlement while keeping financial calculations, business rules, and database mutations deterministic and controlled.

The system combines **LLM-based semantic extraction** with **deterministic financial validation**, **agentic ERP tool selection**, **human-in-the-loop approval**, persistent workflow state, and safe ERP mutations.

> 🚧 **Status: Under active development**

---

## Project Overview

Companies receive invoices in many different formats and must verify that:

* invoice data is correctly extracted
* calculations are mathematically valid
* purchase orders match the invoice
* duplicate invoices are not processed
* currency and financial discrepancies are detected
* risky invoices receive human review
* approved invoices are safely settled

This project is designed to automate that workflow using an agentic architecture while maintaining strict control over financial operations.

---

## Architecture

```text
Invoice PDF
     │
     ▼
PDF / OCR Text Extraction
     │
     ▼
LLM Semantic Extraction
     │
     ▼
Pydantic Schema Validation
     │
     ├── Invalid → Reflection / Retry
     │
     ▼
Deterministic Financial Validation
     │
     ▼
Agentic ERP Tool Selection
     │
     ▼
PO Reconciliation
     │
     ▼
Duplicate Detection
     │
     ▼
Decision Engine
     │
     ├── Safe ───────────────► Automatic Settlement
     │
     └── Risky
           │
           ▼
     Human-in-the-Loop
           │
           ▼
     PostgreSQL Checkpoint
           │
           ▼
     Human Approval / Rejection
           │
           ▼
     Resume Workflow
           │
           ▼
     Controlled ERP Settlement
```

---

## Core Design Philosophy

The system deliberately separates **LLM reasoning from deterministic financial operations**.

### LLM

Used for:

* semantic invoice understanding
* structured information extraction
* schema-constrained output
* tool selection
* reflection and extraction recovery

### Python

Used for:

* arithmetic calculations
* tax calculations
* financial validation
* variance calculations
* business rules
* authorization policies
* settlement safety checks

### Pydantic

Used for:

* data contracts
* schema validation
* structured LLM outputs
* tool argument validation

### LangGraph

Used for:

* workflow orchestration
* state management
* conditional routing
* retry loops
* tool execution
* human-in-the-loop interruption
* workflow resumption

### PostgreSQL

Used for:

* persistent business data
* workflow state
* human review records
* audit logs
* idempotency records
* LangGraph checkpointing

The LLM never receives direct database access or generates raw SQL.

```text
LLM
 │
 ▼
Typed Tool
 │
 ▼
Pydantic Validation
 │
 ▼
Authorization / Policy
 │
 ▼
Application Service
 │
 ▼
Parameterized SQL
 │
 ▼
PostgreSQL
```

---

## Current Implementation

### Phase 1 — Foundation

* [x] Project structure
* [x] Configuration management
* [x] Environment variable support
* [x] Pydantic invoice schemas
* [x] Domain schemas
* [x] Initial automated tests
* [x] Git repository
* [x] `.gitignore`

### Phase 2 — Invoice Extraction

* [x] PDF text extraction
* [x] LLM structured extraction
* [x] Pydantic extraction schema
* [x] Response normalization
* [x] Decimal-based financial values
* [x] Currency normalization
* [x] Optional identifier normalization
* [x] Gemini model fallback
* [x] LLM retry handling
* [x] Circuit breaker
* [x] Extraction benchmark infrastructure

### Phase 3 — Extraction Evaluation

* [x] Synthetic invoice generation
* [x] Multiple invoice templates
* [x] Controlled financial corruptions
* [x] Curated 22-document evaluation set
* [x] Ground-truth dataset
* [x] Field-level accuracy metrics
* [x] Category-level evaluation
* [x] Latency measurement
* [x] Provider/model tracking
* [x] Persistent benchmark results

### Current Benchmark

The extraction pipeline was evaluated on **22 synthetic invoices** covering:

| Category          | Documents |
| ----------------- | --------: |
| Clean             |         7 |
| Tax mismatch      |         3 |
| Subtotal mismatch |         3 |
| Total mismatch    |         3 |
| Missing PO        |         3 |
| Currency mismatch |         3 |
| **Total**         |    **22** |

### Post-fix benchmark results

| Metric                     |     Result |
| -------------------------- | ---------: |
| Documents evaluated        |    22 / 22 |
| Failed documents           |          0 |
| Overall field accuracy     | **100.0%** |
| Invoice number             |       100% |
| Vendor                     |       100% |
| PO number                  |       100% |
| Currency                   |       100% |
| Line items                 |       100% |
| Subtotal                   |       100% |
| Tax rate                   |       100% |
| Tax                        |       100% |
| Total                      |       100% |
| Average extraction latency |     26.42s |

Model usage during the benchmark:

```text
Gemini 3.6 Flash    17 documents
Gemini 3.7 Flash     5 documents
```

### Debugging-driven improvement

The initial benchmark achieved **86.9% overall field accuracy**.

Field-level analysis identified two systematic issues:

1. Percentage values such as `"18"` were returned by the LLM while the evaluation representation expected `0.18`.
2. Missing purchase orders represented as `"N/A"` were being treated as literal identifiers instead of `None`.

The extraction normalization layer was improved to handle both representations deterministically.

After adding regression tests and rerunning the same 22-document benchmark:

```text
Overall field accuracy
86.9% → 100.0%

Tax-rate accuracy
0% → 100%

PO-number accuracy
81.8% → 100%
```

The project currently has **87 automated tests**, all passing.

---

## Planned System Capabilities

### Deterministic Financial Validation

The system will verify:

```text
Σ(quantity × unit_price) = subtotal

subtotal × tax_rate = tax

subtotal + tax = total
```

Financial calculations use `Decimal` arithmetic rather than binary floating-point arithmetic.

---

### Agentic ERP Tools

The agent will interact with the ERP through typed tools such as:

```text
get_purchase_order()
search_vendor()
get_vendor()
check_duplicate_invoice()
reconcile_invoice()
convert_currency()
commit_invoice()
reject_invoice()
```

The LLM selects appropriate tools, but application-level policies control whether tools are actually allowed to execute.

---

### Purchase Order Reconciliation

The system will compare:

* vendor
* purchase order
* line items
* quantities
* unit prices
* totals
* currency

and calculate relevant variances.

---

### Decision Engine

Business policies will determine whether an invoice can be automatically settled.

Example:

```text
All checks pass
     │
     ▼
AUTO SETTLEMENT
```

while:

```text
Missing PO
Currency mismatch
Large financial variance
Duplicate invoice
Authorization failure
        │
        ▼
   HUMAN REVIEW
```

The LLM will not independently decide whether a financial mutation is permitted.

---

### Human-in-the-Loop

Risky invoices will pause the workflow and wait for human approval.

```text
Workflow
   │
   ▼
Risk detected
   │
   ▼
LangGraph interrupt
   │
   ▼
PostgreSQL checkpoint
   │
   ▼
Human approval
   │
   ▼
Resume workflow
   │
   ▼
Settlement
```

---

### Reliability

Planned reliability mechanisms include:

* idempotency keys
* database-level uniqueness constraints
* transactional settlement
* authorization checks
* audit logging
* limited reflection retries
* controlled tool execution
* persistent workflow checkpoints

---

## Evaluation Plan

Beyond extraction accuracy, the complete system will eventually be evaluated on:

### Extraction

* field accuracy
* schema adherence
* first-pass success rate
* retry success rate
* failure rate

### Discrepancy Detection

* precision
* recall
* F1
* false positives
* false negatives

### Agent Behavior

* tool-selection accuracy
* valid tool-call rate
* invalid tool-call rate

### Performance

* latency
* LLM calls per invoice
* retry count
* token usage
* cost per invoice

### Workflow

* automatic settlement rate
* HITL escalation rate
* human approval rate
* duplicate detection rate
* settlement success rate

---

## Technology Stack

* **Python**
* **PyTorch / ML tooling where applicable**
* **Pydantic**
* **Google Gemini**
* **Groq**
* **LangGraph**
* **LangChain ecosystem**
* **PostgreSQL**
* **SQLAlchemy**
* **FastAPI**
* **Pytest**
* **Docker**
* **Git / GitHub**

---

## Development Roadmap

```text
[x] Foundation
[x] Invoice extraction
[x] Extraction normalization
[x] Extraction evaluation
[ ] Reflection / self-correction
[ ] Deterministic financial validation integration
[ ] PostgreSQL persistence
[ ] ERP repository
[ ] ERP tools
[ ] PO reconciliation
[ ] Duplicate detection
[ ] Decision engine
[ ] LangGraph workflow
[ ] Human-in-the-loop workflow
[ ] Idempotent settlement
[ ] Audit trail
[ ] FastAPI API
[ ] Frontend dashboard
[ ] End-to-end evaluation
[ ] Docker deployment
```

---

## Project Goal

The final system will combine generative AI with conventional software engineering rather than relying on an LLM for every decision.

The target architecture is:

```text
LLM
 ↓
Semantic Understanding
 ↓
Typed Application Interfaces
 ↓
Deterministic Business Logic
 ↓
Policy / Authorization
 ↓
Persistent State
 ↓
Controlled Financial Mutation
```

The goal is to demonstrate how agentic AI can be integrated into a **stateful, auditable, and safety-critical business workflow** rather than building another standalone LLM application.
