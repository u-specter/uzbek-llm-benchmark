# 🇺🇿 ULAB — Uzbek Language AI Benchmark

> **The first open benchmark for evaluating AI language models on Uzbek**, focused on banking and financial communication.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-0969da?style=flat-square&logo=github)](https://u-specter.github.io/uzbek-llm-benchmark/)
[![Models](https://img.shields.io/badge/Models%20tested-10-22c55e?style=flat-square)](#models-tested)
[![Questions](https://img.shields.io/badge/Questions-60%20real%20legal%2FFinancial-f59e0b?style=flat-square)](#lq-module)
[![License: MIT](https://img.shields.io/badge/License-MIT-94a3b8?style=flat-square)](LICENSE)

---

## Branch overview

| Branch | Description |
|--------|-------------|
| `main` | Original synthetic benchmark — 5 hand-crafted modules (QA, CL, RB, FK, RC), 114 questions |
| **`feature/lq-serious-benchmark`** ← *you are here* | **Real-dataset benchmark** — 60 questions from `wakilai-legal-benchmark-uz`, GPT-4o judge |

> The old modules (QA / CL / RB / FK / RC) are intentionally hidden in this branch's UI.
> Their code and data are still present in the repository — nothing was deleted.
> To see them, switch to `main` or un-hide the nav tabs in `website/index.html`.

---

## LQ Module — Legal & Financial Q&A

60 real Uzbek-language questions from the [wakilai-legal-benchmark-uz](https://huggingface.co/datasets/HumbleBeeAI/wakilai-legal-benchmark-uz) dataset (529 questions total, banking-relevant subset selected).

### Scoring

GPT-4o compares each model answer against a reference answer and returns one of three verdicts:

| Verdict | Score | Meaning |
|---------|-------|---------|
| `to'g'ri` | 100 | Key facts match the reference answer |
| `qisman` | 50 | Partially correct, missing details |
| `noto'g'ri` | 0 | Wrong or no answer |

### Question categories

| Category | Label | Count |
|----------|-------|-------|
| `moliya` | Soliq va moliya | 14 |
| `biznes` | Tadbirkorlik | 12 |
| `raqamli` | Raqamli xizmatlar | 9 |
| `istemolchi` | Iste'molchi huquqlari | 8 |
| `sugurta` | Sugʻurta | 7 |
| `audit` | Audit va hisobot | 4 |
| `valyuta` | Valyuta operatsiyalari | 3 |
| `lombard` | Lombard va garov | 3 |

---

## Results (March 2026)

| # | Model | Overall |
|---|-------|---------|
| 1 | Claude Sonnet 4.6 | **65.0%** |
| 2 | GPT OSS 120B | 53.3% |
| 3 | Llama 4 Maverick | 48.3% |
| 4 | GPT-4o | 46.7% |
| 5 | Llama 4 Scout | 42.5% |
| 6 | Kimi K2 | 36.7% |
| 7 | Llama 3.3 70B | 35.0% |
| 8 | Qwen3 32B | 34.2% |
| 9 | Gemini 2.0 Flash | 0% *(parsing issue)* |
| 10 | Allam 2 7B | 0% *(no Uzbek legal knowledge)* |

---

## Models Tested

| Model | Provider | Access |
|-------|----------|--------|
| Claude Sonnet 4.6 | Anthropic | API |
| GPT-4o | OpenAI | API |
| GPT OSS 120B | OpenAI | Groq |
| Llama 4 Maverick | Meta | Groq |
| Llama 4 Scout | Meta | Groq |
| Kimi K2 | Moonshot AI | Groq |
| Llama 3.3 70B | Meta | Groq |
| Qwen3 32B | Alibaba | Groq |
| Gemini 2.0 Flash | Google | API |
| Allam 2 7B | SDAIA | Groq |

---

## Quickstart

```bash
git clone https://github.com/u-specter/uzbek-llm-benchmark.git
cd uzbek-llm-benchmark
git checkout feature/lq-serious-benchmark
pip install -r requirements.txt
```

Create `.env`:
```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...
```

Run:
```bash
python run_benchmark_lq.py
open website/index.html
```

---

## Project Structure (this branch)

```
uzbek-ai-benchmark/
├── questions/
│   └── lq_questions.json          # 60 legal/financial Q&A questions
├── website/
│   ├── index.html                 # Dashboard (LQ tab shown by default)
│   ├── css/style.css
│   └── js/
│       ├── app.js
│       └── results.js             # Auto-generated results
├── run_benchmark_lq.py            # Run LQ benchmark (async, GPT-4o judge)
├── create_template.py             # Generate fill-in JSON for manual models
├── import_manual.py               # Import manually collected responses
└── results_raw.json               # Full results DB (local only, not committed)
```

---

## License

MIT © 2026

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
