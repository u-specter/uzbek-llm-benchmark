# 🇺🇿 ULAB — Uzbek Language AI Benchmark

> **The first open benchmark for evaluating AI language models on Uzbek**, focused on banking and financial communication. 14 models tested across 5 modules.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-0969da?style=flat-square&logo=github)](https://u-specter.github.io/uzbek-llm-benchmark/)
[![Models](https://img.shields.io/badge/Models%20tested-14-22c55e?style=flat-square)](#models-tested)
[![Questions](https://img.shields.io/badge/Questions-114%20total-f59e0b?style=flat-square)](#modules)
[![License: MIT](https://img.shields.io/badge/License-MIT-94a3b8?style=flat-square)](LICENSE)

---

## What is ULAB?

ULAB measures how well modern AI models understand and generate **Uzbek text** across five test modules.
Each module targets a real skill needed in Uzbek banking customer service.

The benchmark covers:
- **Language quality** — grammar, spelling, naturalness of Uzbek
- **Register matching** — formal / everyday / colloquial speech styles
- **Task accuracy** — text classification, fact verification, reading comprehension
- **Noise robustness** — handling typos, missing apostrophes, Cyrillic–Latin mix

👉 **[Open live leaderboard](https://u-specter.github.io/uzbek-llm-benchmark/)**
Or simply open `website/index.html` locally — no server needed.

---

## Modules

| # | Module | Questions | Task | Scoring |
|---|--------|-----------|------|---------|
| — | **Core Q&A** | 60 | Answer in 3 Uzbek speech styles | GPT-4o judge (4 criteria, 1–5 scale) |
| CL | **Classification** | 20 | Detect sentiment / intent / register of client messages | Automatic (exact match) |
| RB | **Robustness** | 15 | Understand intent despite noise (typos, Cyrillic, no apostrophes) | Automatic (exact match) |
| FK | **Fact-checking** | 10 | Verify true/false statements about Uzbekistan & banking | Automatic (`to'g'ri` / `noto'g'ri`) |
| RC | **Reading Comprehension** | 9 | MCQ (A/B/C/D) on real banking news passages from kun.uz | Automatic (letter match) |

**Total: 114 questions · 14 models · 5 modules**

---

## Core Q&A — 3 Speech Registers

| Register | Description | Count |
|----------|-------------|-------|
| `formal_business` | Official banking documents, letters, contracts | 20 |
| `informal` | Everyday conversation, requests, explanations | 20 |
| `slang` | Colloquial, youth speech, informal expressions | 20 |

### Scoring criteria (GPT-4o judge)

| Criterion | Weight | Description |
|-----------|--------|-------------|
| D1 — Accuracy | 35% | Complete and correct answer to the question |
| D2 — Language quality | 30% | Grammar, spelling, Uzbek correctness |
| D3 — Style match | 20% | Response matches the required speech register |
| D4 — Naturalness | 15% | Sounds like a real person, not machine translation |

Final score per response is normalized to **0–100**.

---

## Models Tested

### Commercial (via API)
| Model | Provider |
|-------|----------|
| GPT-4o | OpenAI |
| Claude Sonnet 4.6 | Anthropic |
| Gemini 2.0 Flash | Google |
| Gemini 1.5 Pro *(manual)* | Google |
| Mistral Large *(manual)* | Mistral AI |
| DeepSeek V3 *(manual)* | DeepSeek |
| Grok 3 *(manual)* | xAI |
| YandexGPT *(manual)* | Yandex |

### Open-Source (via Groq)
| Model | Provider |
|-------|----------|
| Llama 3.3 70B | Meta |
| Qwen3 32B | Alibaba |
| GPT OSS 120B | OpenAI |
| Llama 4 Maverick | Meta |
| Llama 4 Scout | Meta |
| Kimi K2 | Moonshot AI |

---

## Project Structure

```
uzbek-llm-benchmark/
│
├── questions/                    # Benchmark question banks
│   ├── questions.json            #   Core Q&A — 60 questions
│   ├── cl_questions.json         #   Classification — 20 questions
│   ├── rb_questions.json         #   Robustness — 15 questions
│   ├── fk_questions.json         #   Fact-checking — 10 questions
│   └── rc_questions.json         #   Reading Comprehension — 9 questions
│
├── responses/                    # Raw manual model responses (JSON)
│
├── website/                      # Static dashboard (no server needed)
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── app.js                #   Dashboard logic & charts
│       └── results.js            #   Compiled results (auto-generated)
│
├── data/
│   ├── models.json               # Model registry (names, colors, providers)
│   └── scoring_rubric.json       # GPT-4o scoring rubric
│
├── docs/
│   └── BRD_Uzbek_Language_AI_Benchmark_Platform.md
│
├── MANUAL_QUESTIONS.txt          # All 60 core questions for copy-paste testing
├── MANUAL_CL_QUESTIONS.txt       # CL module prompts
├── MANUAL_RB_QUESTIONS.txt       # RB module prompts
├── MANUAL_FK_QUESTIONS.txt       # FK module prompts
├── MANUAL_RC_QUESTIONS.txt       # RC module prompts (with full passages)
│
├── run_benchmark.py              # Run Core Q&A (all API models, async)
├── run_benchmark_cl.py           # Run Classification module
├── run_benchmark_rb.py           # Run Robustness module
├── run_benchmark_fk.py           # Run Fact-checking module
├── run_benchmark_rc.py           # Run Reading Comprehension module
│
├── score_responses.py            # GPT-4o scoring for Core Q&A responses
├── create_template.py            # Generate fill-in JSON for manual models
├── import_manual.py              # Import manually collected responses
│
├── requirements.txt
└── .env                          # API keys — never commit this!
```

---

## Quickstart

### 1. Clone & install

```bash
git clone https://github.com/u-specter/uzbek-llm-benchmark.git
cd uzbek-llm-benchmark
pip install -r requirements.txt
```

### 2. Configure API keys

Create `.env` in the project root:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
GROQ_API_KEY=gsk_...
```

### 3. Run the benchmark

```bash
# Core Q&A — all API models (async, ~5 min)
python run_benchmark.py

# Score with GPT-4o (~10–15 min)
python score_responses.py

# Extra modules — fully automatic, no GPT-4o needed
python run_benchmark_cl.py
python run_benchmark_rb.py
python run_benchmark_fk.py
python run_benchmark_rc.py
```

### 4. View results

```bash
open website/index.html    # macOS
# or just double-click the file
```

---

## Adding a Manual Model (no API)

For models accessible only via web chat (Gemini, Mistral, Grok, YandexGPT, etc.):

```bash
# Step 1 — Generate a fill-in template
python create_template.py --model gemini --module core

# Step 2 — Open MANUAL_QUESTIONS.txt, copy each question to the model's chat
#           Fill responses into: responses/gemini_responses.json

# Step 3 — Import into the database
python import_manual.py --model gemini --module core

# Step 4 — Score with GPT-4o
python score_responses.py

# For extra modules (CL / RB / FK / RC) — same flow, change --module
python create_template.py --model gemini --module cl
python import_manual.py   --model gemini --module cl
```

---

## Key Findings (March 2026)

- **GPT-4o** leads overall with the highest formal business style score
- **Slang/colloquial Uzbek** is the hardest register for all models — average ~15 points below formal
- **Open-source models** (Qwen3, Llama 4) are competitive on classification and fact-checking
- **Fact-checking reveals hallucinations**: several models state that Uzbekistan's currency is the Tenge, or that the Central Bank is located in Samarkand

---

## Running Specific Models or Questions

Each benchmark script supports filtering:

```bash
# Run only one model
python run_benchmark_cl.py --model qwen3-32b

# Run only specific question IDs
python run_benchmark_rc.py --ids RC-P1-Q1,RC-P2-Q3

# Force re-run even if result exists
python run_benchmark_fk.py --force
```

---

## License

MIT © 2026 — free to use, extend, and cite.

---

## Citation

```bibtex
@misc{ulab2026,
  title  = {ULAB: Uzbek Language AI Benchmark for Banking},
  author = {u-specter},
  year   = {2026},
  url    = {https://github.com/u-specter/uzbek-llm-benchmark}
}
```
