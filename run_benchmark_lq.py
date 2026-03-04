#!/usr/bin/env python3
"""
ULAB — Legal Q&A Module (LQ)
60 banking/financial/legal questions sourced from wakilai-legal-benchmark-uz.
Models answer in Uzbek; GPT-4o compares against reference answer (0 / 50 / 100).

Scoring scale:
  100 — to'g'ri     (key facts match reference)
   50 — qisman      (partially correct)
    0 — noto'g'ri   (wrong or missing key facts)

Subtypes: moliya, biznes, raqamli, istemolchi, sugurta, audit, valyuta, lombard

Usage:
    python run_benchmark_lq.py
    python run_benchmark_lq.py --model gpt-4o
    python run_benchmark_lq.py --type moliya
    python run_benchmark_lq.py --ids LQ-01,LQ-05
"""

import asyncio
import json
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
import httpx

load_dotenv()

BASE_DIR     = Path(__file__).parent
LQ_QUESTIONS = BASE_DIR / "questions" / "lq_questions.json"
RESULTS_JSON = BASE_DIR / "results_raw.json"
RESULTS_JS   = BASE_DIR / "website" / "js" / "results.js"

# ─── Models ──────────────────────────────────────────────────────────────────

COMMERCIAL_MODELS = [
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "client_type": "openai",
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None,
    },
    {
        "id": "claude-sonnet",
        "name": "Claude Sonnet 4.6",
        "client_type": "anthropic",
        "model": "claude-sonnet-4-6",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": None,
    },
    {
        "id": "gemini-flash",
        "name": "Gemini 2.0 Flash",
        "client_type": "openai_compat",
        "model": "gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
]

OPENSOURCE_MODELS = [
    {"id": "llama-70b",       "name": "Llama 3.3 70B",    "client_type": "openai_compat", "model": "llama-3.3-70b-versatile",                       "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "qwen3-32b",       "name": "Qwen3 32B",         "client_type": "openai_compat", "model": "qwen/qwen3-32b",                                "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "gpt-oss-120b",    "name": "GPT OSS 120B",      "client_type": "openai_compat", "model": "openai/gpt-oss-120b",                           "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "llama4-maverick", "name": "Llama 4 Maverick",  "client_type": "openai_compat", "model": "meta-llama/llama-4-maverick-17b-128e-instruct", "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "llama4-scout",    "name": "Llama 4 Scout",     "client_type": "openai_compat", "model": "meta-llama/llama-4-scout-17b-16e-instruct",     "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "kimi-k2",         "name": "Kimi K2",           "client_type": "openai_compat", "model": "moonshotai/kimi-k2-instruct",                   "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "allam-2-7b",      "name": "Allam 2 7B",        "client_type": "openai_compat", "model": "allam-2-7b",                                    "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
]

ALL_MODELS = COMMERCIAL_MODELS + OPENSOURCE_MODELS

MANUAL_MODEL_IDS = {"gemini-pro", "mistral-large", "deepseek-v3", "yandexgpt", "grok-3"}

JUDGE_MODEL = "gpt-4o"


# ─── Prompts ──────────────────────────────────────────────────────────────────

def build_lq_prompt(question: str) -> str:
    return f"""Sen O'zbek tilida moliyaviy va yuridik masalalar bo'yicha maslahat beruvchi assistantsan.

Savol: {question}

O'zbek tilida aniq va qisqa javob ber. Faqat savolga javob ber."""


def build_judge_prompt(question: str, reference: str, model_answer: str) -> str:
    return f"""Sen O'zbek tilidagi yuridik/moliyaviy javoblarni baholaydigan ekspertsan.

SAVOL: {question}

ETALON JAVOB: {reference}

MODEL JAVOBI: {model_answer}

Model javobi etalon javobga nisbatan qanchalik to'g'ri?

Faqat bitta so'z yoz (boshqa hech narsa yozma):
- togri    → asosiy faktlar to'g'ri va to'liq
- qisman   → ba'zi faktlar to'g'ri, lekin muhim ma'lumotlar yetishmaydi yoki noto'g'ri
- notogri  → asosiy faktlar noto'g'ri yoki umuman javob yo'q"""


# ─── Scoring ──────────────────────────────────────────────────────────────────

def parse_judge_verdict(verdict: str) -> dict:
    v = verdict.strip().lower()
    if "notogri" in v or "noto'g'ri" in v or "noto`g`ri" in v:
        return {"score": 0,   "parsed": "notogri",  "correct": False}
    if "qisman" in v:
        return {"score": 50,  "parsed": "qisman",   "correct": False}
    if "togri" in v or "to'g'ri" in v or "to`g`ri" in v:
        return {"score": 100, "parsed": "togri",     "correct": True}
    return {"score": 0, "parsed": None, "correct": False}


def check_lq_response(model_answer: str, verdict_raw: str) -> dict:
    """Used by import_manual.py — verdict is the raw GPT-4o string."""
    return parse_judge_verdict(verdict_raw)


# ─── API Callers ──────────────────────────────────────────────────────────────

def strip_thinking(text: str) -> str:
    import re
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


async def call_openai(model_cfg: dict, prompt: str, max_tokens: int = 1024) -> dict:
    key = os.getenv(model_cfg["api_key_env"], "")
    if not key:
        return {"error": f"No API key: {model_cfg['api_key_env']}"}
    client = AsyncOpenAI(api_key=key)
    start = time.time()
    try:
        resp = await client.chat.completions.create(
            model=model_cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0,
        )
        return {
            "response":   strip_thinking(resp.choices[0].message.content.strip()),
            "latency_ms": int((time.time() - start) * 1000),
            "tokens":     resp.usage.total_tokens if resp.usage else None,
        }
    except Exception as e:
        return {"error": str(e), "latency_ms": int((time.time() - start) * 1000)}


async def call_anthropic(model_cfg: dict, prompt: str) -> dict:
    key = os.getenv(model_cfg["api_key_env"], "")
    if not key:
        return {"error": f"No API key: {model_cfg['api_key_env']}"}
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model_cfg["model"],
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            data = resp.json()
            text = strip_thinking(data["content"][0]["text"].strip())
            return {
                "response":   text,
                "latency_ms": int((time.time() - start) * 1000),
                "tokens":     data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
            }
    except Exception as e:
        return {"error": str(e), "latency_ms": int((time.time() - start) * 1000)}


async def call_model(model_cfg: dict, prompt: str) -> dict:
    t = model_cfg["client_type"]
    if t == "openai":
        return await call_openai(model_cfg, prompt)
    elif t == "anthropic":
        return await call_anthropic(model_cfg, prompt)
    elif t == "openai_compat":
        key = os.getenv(model_cfg["api_key_env"], "")
        if not key:
            return {"error": f"No API key: {model_cfg['api_key_env']}"}
        client_tmp = AsyncOpenAI(api_key=key, base_url=model_cfg["base_url"])
        start = time.time()
        try:
            resp = await client_tmp.chat.completions.create(
                model=model_cfg["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                temperature=0,
            )
            return {
                "response":   strip_thinking(resp.choices[0].message.content.strip()),
                "latency_ms": int((time.time() - start) * 1000),
                "tokens":     resp.usage.total_tokens if resp.usage else None,
            }
        except Exception as e:
            return {"error": str(e), "latency_ms": int((time.time() - start) * 1000)}
    return {"error": f"Unknown client_type: {t}"}


async def judge_answer(question: str, reference: str, model_answer: str) -> dict:
    """Call GPT-4o to compare model answer against reference."""
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_key:
        return {"score": 0, "parsed": None, "correct": False, "verdict_raw": "no_key"}

    judge_cfg = {"api_key_env": "OPENAI_API_KEY", "model": JUDGE_MODEL}
    prompt = build_judge_prompt(question, reference, model_answer)
    result = await call_openai(judge_cfg, prompt, max_tokens=16)

    if result.get("error"):
        return {"score": 0, "parsed": None, "correct": False, "verdict_raw": result["error"]}

    verdict_raw = result["response"]
    parsed = parse_judge_verdict(verdict_raw)
    return {**parsed, "verdict_raw": verdict_raw}


# ─── Core logic ───────────────────────────────────────────────────────────────

async def run_question(q: dict, models: list) -> dict:
    question  = q["question"]
    reference = q["reference_answer"]
    prompt    = build_lq_prompt(question)

    # Step 1: collect model answers (parallel)
    tasks = {m["id"]: call_model(m, prompt) for m in models}
    raw   = await asyncio.gather(*tasks.values(), return_exceptions=True)

    responses = {}
    judge_inputs = []

    for model_id, result in zip(tasks.keys(), raw):
        if isinstance(result, Exception):
            result = {"error": str(result)}
        if result.get("error"):
            responses[model_id] = {"error": result["error"], "score": 0, "correct": False}
        else:
            responses[model_id] = {
                "response":   result["response"],
                "latency_ms": result.get("latency_ms"),
                "tokens":     result.get("tokens"),
            }
            judge_inputs.append(model_id)

    # Step 2: judge all valid answers via GPT-4o (parallel)
    if judge_inputs:
        judge_tasks = [
            judge_answer(question, reference, responses[mid]["response"])
            for mid in judge_inputs
        ]
        judgments = await asyncio.gather(*judge_tasks, return_exceptions=True)

        for model_id, judgment in zip(judge_inputs, judgments):
            if isinstance(judgment, Exception):
                judgment = {"score": 0, "parsed": None, "correct": False, "verdict_raw": str(judgment)}
            responses[model_id].update(judgment)

    return {**q, "responses": responses}


def compute_lq_leaderboard(lq_results: list, model_ids: list) -> dict:
    subtypes = ["moliya", "biznes", "raqamli", "istemolchi", "sugurta", "audit", "valyuta", "lombard"]
    scores = {m: {"overall": [], **{s: [] for s in subtypes}} for m in model_ids}

    for q in lq_results:
        q_type = q.get("type", "")
        for model_id, resp in q.get("responses", {}).items():
            if model_id not in scores:
                continue
            s = resp.get("score", 0)
            scores[model_id]["overall"].append(s)
            if q_type in scores[model_id]:
                scores[model_id][q_type].append(s)

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    return {
        m: {k: avg(v) for k, v in data.items()}
        for m, data in scores.items()
    }


def export_results_js(data: dict):
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    js  = f"// Auto-generated {ts}\n"
    js += "window.BENCHMARK_RESULTS = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js, encoding="utf-8")


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="ULAB — LQ Benchmark (Legal Q&A)")
    parser.add_argument("--model", help="Run only this model ID")
    parser.add_argument("--type",  help="Subtype filter: moliya / biznes / sugurta / ...")
    parser.add_argument("--ids",   help="Comma-separated question IDs, e.g. LQ-01,LQ-05")
    parser.add_argument("--force", action="store_true", help="Re-run even if response already exists")
    args = parser.parse_args()

    if not LQ_QUESTIONS.exists():
        print(f"ERROR: {LQ_QUESTIONS} not found.")
        sys.exit(1)
    if not RESULTS_JSON.exists():
        print(f"ERROR: {RESULTS_JSON} not found. Run run_benchmark.py first.")
        sys.exit(1)

    lq_data   = json.loads(LQ_QUESTIONS.read_text(encoding="utf-8"))
    questions = lq_data["questions"]

    if args.ids:
        id_set    = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in id_set]
    if args.type:
        questions = [q for q in questions if q["type"] == args.type]

    models = [m for m in ALL_MODELS if m["id"] not in MANUAL_MODEL_IDS]
    if args.model:
        models = [m for m in ALL_MODELS if m["id"] == args.model]
        if not models:
            print(f"ERROR: model '{args.model}' not found.")
            sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"  ULAB — Legal Q&A Benchmark (LQ)")
    print(f"{'═'*60}")
    print(f"  Questions : {len(questions)}")
    print(f"  Models    : {len(models)}")
    print(f"  Judge     : {JUDGE_MODEL}")
    print(f"{'═'*60}\n")

    results     = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    existing_lq = {q["id"]: q for q in results.get("lq_questions", [])}

    for q in questions:
        qid = q["id"]

        if qid in existing_lq and not args.force:
            existing = existing_lq[qid]
            missing  = [m for m in models if m["id"] not in existing.get("responses", {})]
            if not missing:
                print(f"  {qid} — skip (already done)")
                continue
            models_to_run = missing
        else:
            models_to_run = models

        print(f"  {qid} [{q['type']}] — {q['question'][:60]}...")
        q_result = await run_question(q, models_to_run)

        if qid in existing_lq:
            existing_lq[qid].setdefault("responses", {}).update(q_result["responses"])
        else:
            existing_lq[qid] = q_result

        for model_id, resp in q_result["responses"].items():
            if model_id not in [m["id"] for m in models_to_run]:
                continue
            score   = resp.get("score", 0)
            parsed  = resp.get("parsed", "?")
            icon    = "✓" if score == 100 else ("~" if score == 50 else "✗")
            print(f"    {icon} {model_id:<22} → {parsed or 'N/A':<10} ({score})")

        await asyncio.sleep(0.3)

    all_lq      = list(existing_lq.values())
    model_ids   = list({r for q in all_lq for r in q.get("responses", {})})
    lq_lb       = compute_lq_leaderboard(all_lq, model_ids)

    results["lq_questions"]   = all_lq
    results["lq_leaderboard"] = lq_lb

    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    export_results_js(results)

    print(f"\n{'═'*60}")
    print(f"  LQ Leaderboard")
    print(f"{'═'*60}")
    sorted_lb = sorted(lq_lb.items(), key=lambda x: x[1].get("overall") or 0, reverse=True)
    for rank, (mid, s) in enumerate(sorted_lb, 1):
        ov = s.get("overall")
        print(f"  {rank:>2}. {mid:<24} Overall: {str(ov)+'%':>7}")
    print(f"\n  Saved → results_raw.json + website/js/results.js\n")


if __name__ == "__main__":
    asyncio.run(main())
