# Document Agent & Intelligent Document Creator – Implementation Plan

## Goals
- Add two new microservices (or modules) without creating new Docker images:
  - **Document Agent**: Generate PSDP Summary and Financial Brief documents using existing stored data (Performance + Finance).
  - **Intelligent Document Creator**: User-driven document generation with reasoning over available data.
- Reuse the existing unified Docker image and fallback-to-monolith logic (like Performance/Finance/CSV).

## Existing Data to Leverage
- **Performance Agent (Chroma)**: milestones, tasks, bottlenecks, requirements, actors, and their details/suggestions.
- **Finance Agent (Chroma)**: transactions, expense/revenue analyses, actor→transaction mappings, anomalies, financial suggestions.

## Document Agent (PSDP Summary & Financial Brief)
- **Data sourcing**:
  - PSDP: pull project metadata + performance entities (milestones/tasks/bottlenecks/requirements/actors + details/suggestions).
  - Financial Brief: pull financial details, transactions (expenses/revenue), analyses, anomalies, actor→transaction mappings.
- **LLM prompts**: strict templates telling the model to return a structured doc section-by-section (project info, key highlights, risks, actions, financial overview).
- **Endpoints**:
  - `POST /document_agent/psdp_summary` (project_id) → generates JSON/HTML, stores doc in Chroma/DB, returns payload.
  - `POST /document_agent/financial_brief` (project_id) → same pattern.
  - `GET /document_agent/documents/<project_id>` → list stored docs; `GET /document_agent/document/<doc_id>` → fetch; `GET /document_agent/document/<doc_id>/download` → PDF/download.
- **UI**:
  - Add a “Document Agent” card on each Project details page with buttons: Generate PSDP Summary, Generate Financial Brief, Download last/generated docs, View list.
  - Render doc preview (HTML) and download link.
- **Fallback**:
  - Try gateway/A2A to fetch performance/finance data; fallback to direct calls when running monolith.

## Intelligent Document Creator (User-defined docs)
- **Worker agents**:
  - **Intent/Reasoner**: classify the user request and decide which data to fetch (e.g., only transactions + requirements).
  - **Retriever**: fetch requested subsets from Performance/Finance (via gateway or direct).
  - **Prompt Builder**: assemble prompt with requested sections + style + constraints.
  - **Generator**: call LLM, produce structured output (JSON/HTML) + summary.
- **Endpoints**:
  - `POST /doc_gen/create` (project_id, user_instructions, scope flags) → returns doc, stores it, provides download link.
  - `GET /doc_gen/documents/<project_id>` / `GET /doc_gen/document/<doc_id>` / `GET /doc_gen/document/<doc_id>/download`.
- **UI**:
  - “Intelligent Document Generator” card on the Document Dashboard (and linked from Project page).
  - Form: user instructions + toggles for data sources (performance: milestones/tasks/requirements/actors; finance: transactions/analyses/mappings).
  - Show preview + download.
- **Fallback**: same gateway/direct pattern as other agents.

## Storage
- Reuse existing Chroma for document storage (new collections: `doc_agent_documents`, `doc_gen_documents`).
- Metadata per doc: project_id, doc_type (psdp_summary/financial_brief/custom), created_at, sections, source data snapshot.

## Docker/Runtime
- **No new Dockerfiles/images.** Reuse the existing unified image and `docker-compose` service model:
  - Add services (commands) for document-agent and doc-gen in compose, each using the shared image and entrypoint override.
  - Maintain monolith fallback logic for local `python app.py`.

## Steps
1) Add Chroma collections for docs (agent + generator).
2) Implement Document Agent service: data fetchers (perf/fin), prompts, endpoints, storage, downloads.
3) Implement Intelligent Document Creator service: worker agents (intent, retriever, prompt builder, generator), endpoints, storage, downloads.
4) UI: project details page “Document Agent” card; Document Dashboard with PSDP/Financial Brief actions and Intelligent Generator card.
5) Wire gateway routes + fallback to monolith.
6) Tests: unit tests for prompt builders and doc storage; smoke tests for endpoints.
7) Reuse existing Docker image; add compose entries only (no new image builds).
