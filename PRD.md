# ActuAI Reserve Agent — Product Requirements Document (PRD)

## 1. Product Overview
ActuAI is an interactive, web-based P&C actuarial assistant that guides reserving analysts through a rigorous, ASOP-compliant loss reserving workflow. It bridges Large Language Models (local or cloud) with deterministic actuarial engines (chainladder) to automate calculations, enforce standards, and generate audit-ready reports.

## 2. Architecture: Dual-Agent System
The system utilizes a Producer-Consumer architecture via a shared Blackboard (Session State).

### 2.1 Agent A (The Actuary)
- **Role:** Expert P&C Actuary & Tool Orchestrator.
- **Workflow:** Phases 1-7 (Data Quality -> Uncertainty).
- **Mandate:** Generate 1-2 sentence actuarial justifications ("ACTUARIAL JUDGMENT") for every result.

### 2.2 Agent B (The Writer)
- **Role:** ASOP 41 Technical Writer.
- **Workflow:** Synthesizes the audit log into 6 isolated chunks to form a formal report.
- **Constraints:** No math capabilities, receives only filtered audit log context.

### 2.3 Agent C (The Reviewer)
- **Role:** Critical Auditor.
- **Workflow:** Reads uploaded actuarial reports, summarizes them, and compares content vs ASOP standards one by one.
- **Strategy:** Chunked reading for long documents, local Ollama fallback.

## 3. Functional Requirements
### 3.1 8-Phase Workflow
1. **Data Ingestion:** Accept .xlsx, .csv, .pdf. Extract tables.
2. **Data Quality (ASOP 23):** Score 0-100. Gate: No proceed if score < 60.
3. **Triangle Construction:** Support AY/PY/RY, various dev units.
4. **Diagnostic Testing:** Calendar Year Effects (>20% dev) and Stability (CV > 30%).
5. **LDF Selection:** Volume-weighted, Simple, Medial, Regression.
6. **Tail Factor Fitting:** Curve fitting (Inverse Power, Weibull, Exponential), Bondy, Constant.
7. **IBNR Modeling:** CL, BF, Mack, Benktander, Cape Cod. Require apriori rationale.
8. **Uncertainty (ASOP 43):** Mack Standard Error, CV classification, 75/90/95 intervals.

### 3.2 Visualization & Reporting
- **Heatmaps:** Cumulative, Incremental, and Age-to-Age LDF triangles.
- **ASOP 41 Report:** 8-section Markdown report synthesized from judgments.
- **TTS:** Optional read-out of executive summary.

## 4. Technical Constraints
- **UI:** Chainlit (Async Python).
- **Math Engine:** chainladder.
- **LLM:** OpenRouter (Primary) with fallback to local Ollama (ministral-3:3b, qwen3.5:4b, etc.).
- **Isolation:** Strictly scoped to `cl.user_session`.
