# Business Requirements Document (BRD)
## Uzbek Language AI Benchmark Platform

| Field | Detail |
|---|---|
| Document ID | BRD-ULAB-2026-001 |
| Version | 1.0 |
| Status | Draft |
| Date | 2026-02-27 |
| Prepared by | Office of the Chairman's Advisor |
| Classification | Internal — Confidential |

---

## 1. Executive Summary

The Bank intends to deploy an AI-powered assistant to serve internal stakeholders across multiple departments in the Uzbek language. Before committing to a language model vendor or open-source solution, the Bank requires an objective, evidence-based comparative evaluation of leading commercial and open-source large language models (LLMs) on Uzbek-language proficiency across three communication registers: colloquial/slang, informal, and formal/banking. This document defines the business requirements for the **Uzbek Language AI Benchmark Platform (ULAB)** — a structured testing environment and reporting dashboard that will produce vendor-agnostic, auditable results to inform the Bank's model selection decision.

---

## 2. Business Objectives

| ID | Objective | Metric | Target |
|---|---|---|---|
| BO-01 | Identify the LLM with the highest Uzbek-language competency across all three registers | Aggregate benchmark score (0–100) | Top model >= 80 |
| BO-02 | Reduce AI model selection risk by replacing subjective judgment with a standardized scoring methodology | % of selection criteria covered by quantitative scoring rubric | >= 90% |
| BO-03 | Produce an auditable benchmark report presentable to the Bank's risk and compliance committees | Report completeness against BRD acceptance criteria | 100% |
| BO-04 | Accelerate AI assistant procurement decision | Time from benchmark completion to Board recommendation | <= 10 business days |
| BO-05 | Establish a reusable benchmarking infrastructure for future AI evaluations at the Bank | Reuse of platform for next AI evaluation project | Within 12 months of ULAB go-live |

---

## 3. Scope

### 3.1 In-Scope
- Design and deployment of a web-based benchmark platform (ULAB) for internal use
- Creation of a curated question bank: 60 questions in Uzbek across three registers (20 per register)
- Integration with APIs of 4 commercial LLMs and deployment/testing of 4 open-source LLMs
- Automated and human-expert scoring of model responses against a defined scoring rubric
- Interactive reporting dashboard accessible to business department heads and the Chairman's office
- Generation of a final comparative benchmark report with model rankings and procurement recommendation
- Secure storage of all prompts, model responses, and scores for audit purposes

### 3.2 Out-of-Scope
- Production deployment or integration of any selected AI model into Bank systems
- Fine-tuning or retraining of any evaluated LLM
- Customer-facing chatbot development
- Evaluation of models in languages other than Uzbek
- Evaluation of speech-to-text or text-to-speech capabilities
- Integration with the Bank's core banking system (CBS), CRM, or AML/KYC platforms
- Security penetration testing of vendor infrastructure

---

## 4. Stakeholders and Roles

| ID | Stakeholder | Role | Responsibilities |
|---|---|---|---|
| S-01 | Chairman's Advisor | Executive Sponsor | Approves BRD, reviews final benchmark report, makes procurement recommendation to Board |
| S-02 | Head of Digital Transformation | Project Owner | Owns delivery, resolves scope disputes, signs off acceptance criteria |
| S-03 | IT Department | Technical Lead | Provisions infrastructure, integrates LLM APIs, ensures platform security |
| S-04 | Risk and Compliance | Compliance Reviewer | Reviews data handling, ensures CBU regulatory alignment, approves audit trail |
| S-05 | Retail Banking Dept Head | Business Stakeholder | Provides use cases for informal/slang register, reviews dashboard |
| S-06 | Corporate Banking Dept Head | Business Stakeholder | Provides use cases for formal/banking register, reviews dashboard |
| S-07 | HR & Internal Comms | Business Stakeholder | Validates informal register scenarios for internal staff communications |
| S-08 | Uzbek Language Expert (external) | Subject Matter Expert | Authors and validates all 60 questions; evaluates model responses |
| S-09 | AI/ML Engineer | Technical Contributor | Deploys open-source models, manages API integrations, runs automated scoring |
| S-10 | QA Engineer | Quality Assurance | Validates platform functionality, scoring pipeline integrity, dashboard accuracy |

---

## 5. Functional Requirements

| ID | Requirement | Description | Priority |
|---|---|---|---|
| FR-01 | Question Bank Management | Store and version-control 60 benchmark questions categorized by register with metadata | Must Have |
| FR-02 | Model Registry | Maintain registry of evaluated models (name, version, provider, API endpoint, evaluation date) | Must Have |
| FR-03 | Automated Prompt Submission | Auto-submit all 60 questions to each model via API; capture raw text responses | Must Have |
| FR-04 | Response Storage | Store all model responses in structured, tamper-evident format with timestamps | Must Have |
| FR-05 | Automated Scoring Engine | Apply automated metrics (BLEU, semantic similarity via multilingual embeddings) as baseline scores | Must Have |
| FR-06 | Human Expert Scoring Interface | Secure interface for Uzbek Language Expert to score responses and enter qualitative comments | Must Have |
| FR-07 | Score Aggregation | Calculate weighted composite scores per model per register and overall | Must Have |
| FR-08 | Model Comparison Dashboard | Interactive dashboard showing scores by model, register, and scoring dimension | Must Have |
| FR-09 | Benchmark Report Export | Generate downloadable PDF/XLSX report with scores, rankings, and executive summary | Must Have |
| FR-10 | Role-Based Access Control | Enforce RBAC for Executive, Business, Expert, and Admin roles | Must Have |
| FR-11 | Audit Log | Log all user actions and system events with timestamps | Must Have |
| FR-12 | Re-run Capability | Support re-running benchmark for a specific model without disrupting historical results | Should Have |
| FR-13 | Question Randomization | Randomized question ordering per model submission to eliminate positional bias | Should Have |
| FR-14 | Latency Measurement | Record and report response latency (ms) per model-question pair | Should Have |
| FR-15 | Notifications | Notify stakeholders on benchmark completion, scoring completion, and report generation | Could Have |

---

## 6. Non-Functional Requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Security | All data in transit encrypted via TLS 1.2+; all data at rest encrypted via AES-256 |
| NFR-02 | Security | No benchmark data transmitted to third parties beyond evaluated model API endpoints |
| NFR-03 | Security | MFA required for all user roles |
| NFR-04 | Availability | 99% uptime during benchmark execution period (~4 weeks) |
| NFR-05 | Performance | Full benchmark pipeline (60Q × 8 models + scoring) completes within 4 hours |
| NFR-06 | Scalability | Architecture supports addition of up to 10 additional LLMs without code refactoring |
| NFR-07 | Data Retention | All benchmark data retained for minimum 3 years per Bank's data governance policy |
| NFR-08 | Compliance | Platform complies with CBU regulations and Bank's internal information security policy |
| NFR-09 | Usability | Dashboard operable by non-technical users after 1-hour orientation |
| NFR-10 | Auditability | Immutable audit trail sufficient to reconstruct any scoring decision for regulatory review |
| NFR-11 | Deployment | Deployable on Bank's on-premises or private cloud infrastructure (data sovereignty) |

---

## 7. Benchmark Methodology Requirements

### 7.1 Model Selection

**Commercial Models (4):**

| # | Model | Provider |
|---|---|---|
| 1 | GPT-4o | OpenAI |
| 2 | Claude Sonnet 4.6 | Anthropic |
| 3 | Gemini 2.0 Flash | Google DeepMind |
| 4 | Grok 2 | xAI |

**Open-Source Models (4):**

| # | Model | Deployment |
|---|---|---|
| 1 | Qwen3-235B-A22B | Alibaba (self-hosted) |
| 2 | DeepSeek-V3 | DeepSeek AI (self-hosted) |
| 3 | Llama 4 Maverick | Meta (self-hosted) |
| 4 | Mixtral 8x22B | Mistral AI (self-hosted) |

> Model versions shall be frozen at benchmark initiation date and recorded in the Model Registry.

---

### 7.2 Register Definitions

| Register | Definition | Example Context |
|---|---|---|
| Slang / Street | Highly colloquial Uzbek including youth slang, code-switching with Russian, informal internet vocabulary | Peer-to-peer messaging, social media |
| Informal | Standard spoken Uzbek used in everyday professional interactions; relaxed grammar, no slang | Internal staff communications, casual client conversations |
| Formal / Banking | Written Uzbek conforming to banking and financial services standards; precise terminology, regulatory language | Credit decisions, regulatory filings, committee minutes |

---

### 7.3 Question Bank Specification

- **Total**: 60 questions (20 per register)
- **Authored by**: Uzbek Language Expert (S-08) in consultation with S-05, S-06, S-07
- **Approval**: Sign-off from Project Owner before benchmark initiation

**Slang Register — 20 Questions (Topic Distribution):**

| Topic Area | Count |
|---|---|
| Understanding youth/street slang terms | 6 |
| Code-switching scenarios (Uzbek/Russian mix) | 5 |
| Translating slang to formal Uzbek | 4 |
| Contextual meaning in informal dialogue | 3 |
| Identifying offensive vs. neutral slang | 2 |

**Informal Register — 20 Questions:**

| Topic Area | Count |
|---|---|
| Everyday banking transaction dialogue | 5 |
| Internal team communication scenarios | 5 |
| Customer service conversational replies | 4 |
| HR and administrative correspondence | 3 |
| General knowledge Q&A in spoken Uzbek | 3 |

**Formal / Banking Register — 20 Questions:**

| Topic Area | Count |
|---|---|
| Banking product descriptions (loans, deposits) | 5 |
| Formal client correspondence drafting | 4 |
| Regulatory and compliance terminology | 4 |
| Financial statement interpretation | 4 |
| Legal/contractual clause explanation | 3 |

---

### 7.4 Scoring Rubric

| Dim | Dimension | Description | Weight |
|---|---|---|---|
| D1 | Linguistic Accuracy | Grammatical correctness, morphology, syntax | 25% |
| D2 | Register Appropriateness | Correct vocabulary, tone, and formality level | 25% |
| D3 | Semantic Correctness | Response correctly and factually answers the question | 25% |
| D4 | Fluency and Naturalness | Reads as natural Uzbek to a native speaker | 15% |
| D5 | Response Completeness | Addresses all sub-components; no truncation (automated) | 10% |

**Scale:** 0 (Fail) · 1 (Poor) · 2 (Acceptable) · 3 (Good) · 4 (Excellent)

**Composite Score Formula:**
```
Question Score (0–100) = [(D1×0.25) + (D2×0.25) + (D3×0.25) + (D4×0.15) + (D5×0.10)] × 25
Register Score        = Average of 20 Question Scores for that register
Overall Model Score   = (Slang Score + Informal Score + Formal/Banking Score) / 3
```

**Model Tier Classification:**

| Tier | Score Range | Recommendation |
|---|---|---|
| S | 90–100 | Production Ready for Banking Use |
| A | 75–89 | Ready with Minor Supervision |
| B | 60–74 | Usable for Non-Critical Tasks |
| C | 45–59 | Requires Significant Improvement |
| D | 0–44 | Not Recommended |

**Scoring Process:**
1. Automated pipeline runs D5 scoring immediately upon response capture
2. Language Expert scores D1–D4 within 5 business days of response capture
3. Platform calculates weighted composite scores upon expert score submission
4. Project Owner reviews scores for anomalies before report publication

---

## 8. Reporting and Dashboard Requirements

### 8.1 Dashboard Views

| View ID | Name | Description | Audience |
|---|---|---|---|
| DV-01 | Executive Scorecard | Overall rankings, top 3 highlighted, recommendation flag | Chairman's Advisor, Dept Heads |
| DV-02 | Register Breakdown | Radar chart: each model's performance across 3 registers | All business stakeholders |
| DV-03 | Dimension Heatmap | 8 models × 5 dimensions; highlights per-model strengths/weaknesses | Project Owner, IT Lead |
| DV-04 | Question-Level Drill-Down | Filterable table with raw response + score per question | Language Expert, QA |
| DV-05 | Latency Comparison | Response latency by model; annotated with cost implications | IT Department |
| DV-06 | Commercial vs. Open-Source | Aggregate score comparison between model groups | All stakeholders |

### 8.2 Report Export (FR-09)
Contents of PDF/XLSX export:
1. Executive summary with ranked model table and top recommendation
2. Methodology (register definitions, question bank summary, scoring rubric)
3. Full score matrix (8 models × 3 registers × 5 dimensions)
4. Per-register qualitative commentary from Language Expert
5. Latency and operational performance summary
6. Appendix: all 60 questions, verbatim model responses, individual question scores

Classification marking: **"Internal — Confidential"** watermark on all pages.

---

## 9. Success Criteria

| ID | Criterion | Measurement |
|---|---|---|
| SC-01 | All 60 questions approved before benchmark initiation | Sign-off from Project Owner and Language Expert |
| SC-02 | All 8 models respond to all 60 questions | 0 unanswered question-model pairs |
| SC-03 | Expert scoring complete within SLA | 100% complete within 5 business days |
| SC-04 | Dashboard functional for all defined roles | UAT sign-off from Project Owner + 2 business stakeholders |
| SC-05 | Final report approved by Executive Sponsor | Signed approval from Chairman's Advisor |
| SC-06 | Clear model recommendation with quantitative justification produced | Recommendation section present in final report |
| SC-07 | Audit log complete and reviewable by Compliance | Compliance sign-off on audit trail completeness |

---

## 10. Risks and Mitigations

| ID | Risk | Prob | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | API throttling by commercial vendor during benchmark run | Med | High | Pre-negotiate rate limits; fallback to manual submission |
| R-02 | Language Expert scoring bias across models | Med | High | Scoring rubric with worked examples; 10% inter-rater reliability check |
| R-03 | Open-source model infrastructure underperformance | Med | Med | GPU provision 2 weeks early; pilot question load test; 60-sec timeout policy |
| R-04 | Questions inadvertently favor specific training corpora | Low | High | Neutrality review by Language Expert + two departmental stakeholders |
| R-05 | Platform data breach exposing question bank or responses | Low | High | Isolated internal network; MFA; API keys restricted to service account |
| R-06 | Vendor updates model weights during benchmark period | Med | High | Freeze model versions at initiation; include version and date in all reports |
| R-07 | Stakeholder disagreement on rubric weights post-publication | Low | Med | Written stakeholder sign-off on rubric before initiation; changes require formal CR |
| R-08 | Project timeline overrun delays Board recommendation | Med | Med | Phased milestones with buffer; escalation to Executive Sponsor if milestone missed >3 days |

---

## 11. Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-01 | All 60 questions submitted to all 8 models with no data loss |
| AC-02 | Automated (D5) and expert (D1–D4) scoring complete for 100% of 480 question-model pairs |
| AC-03 | Composite scores correctly calculated; verified by QA spot-check on ≥20 random pairs |
| AC-04 | Dashboard displays accurate data for all 6 views; all filters functional |
| AC-05 | Report exported in PDF and XLSX; reviewed by Project Owner for completeness |
| AC-06 | Audit log captures all events from benchmark initiation to report export with no gaps |
| AC-07 | Risk and Compliance sign-off on data handling and audit trail |
| AC-08 | Executive Sponsor reviews, approves, and signs final benchmark report |
| AC-09 | All source data archived per 3-year retention policy |
| AC-10 | Formal procurement recommendation memo submitted to the Board |

---

*Revision History:*

| Rev | Date | Author | Change |
|---|---|---|---|
| 1.0 | 2026-02-27 | Office of Chairman's Advisor | Initial draft |
