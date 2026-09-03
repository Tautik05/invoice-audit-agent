# Autonomous Invoice Audit & ERP Settlement Agent

A production-oriented agentic invoice auditing system built with Python, Pydantic, LangGraph, FastAPI, and PostgreSQL.

The system is designed to automate invoice processing while keeping financial calculations and database mutations deterministic and controlled.

## Planned Architecture

```text
Invoice PDF
    ↓
Semantic Extraction
    ↓
Pydantic Schema Validation
    ↓
Reflection / Retry
    ↓
Deterministic Financial Validation
    ↓
Agentic ERP Tool Selection
    ↓
PO Reconciliation
    ↓
Decision Engine
    ├── Safe → Automatic Settlement
    └── Risky → Human-in-the-Loop
                    ↓
               Human Approval
                    ↓
               Resume Workflow
                    ↓
               ERP Settlement
```

## Key Features

* LLM-based semantic invoice extraction
* Strict Pydantic schemas
* Reflection-based extraction retry
* Deterministic financial validation
* Agentic tool selection
* Mock ERP service
* Purchase-order reconciliation
* Duplicate invoice detection
* Human-in-the-Loop workflow interruption
* PostgreSQL persistence and LangGraph checkpointing
* Audit trail and workflow observability
* Idempotent ERP mutations
* FastAPI backend
* Automated testing

## Current Status

🚧 Under active development.

### Phase 1 — Foundation

* [x] Project structure
* [x] Pydantic invoice schema
* [x] Initial schema tests
* [x] Git repository
* [x] `.gitignore`
* [ ] Extraction pipeline
* [ ] LangGraph workflow
* [ ] ERP tools
* [ ] HITL workflow
* [ ] Database
* [ ] Evaluation
* [ ] Deployment
