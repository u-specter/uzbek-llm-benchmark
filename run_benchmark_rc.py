#!/usr/bin/env python3
"""
ULAB — Reading Comprehension Module (RC)
Tests whether models can answer MCQ questions based on real Uzbek banking news passages.

Each question includes a passage (from kun.uz) + 4 answer choices (A/B/C/D).
Scoring is fully automatic — no GPT-4o needed.

Usage:
    python run_benchmark_rc.py              # All questions, all models
    python run_benchmark_rc.py --model gpt-4o
    python run_benchmark_rc.py --type hayot_bank
    python run_benchmark_rc.py --ids RC-P1-Q1,RC-P2-Q3
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

BASE_DIR      = Path(__file__).parent
RC_QUESTIONS  = BASE_DIR / "questions" / "rc_questions.json"
RESULTS_JSON  = BASE_DIR / "results_raw.json"
RESULTS_JS    = BASE_DIR / "website" / "js" / "results.js"

# ─── Models (same as other modules) ──────────────────────────────────────────

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
    {"id": "llama-70b",       "name": "Llama 3.3 70B",      "client_type": "openai_compat", "model": "llama-3.3-70b-versatile",                        "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "qwen3-32b",       "name": "Qwen3 32B",           "client_type": "openai_compat", "model": "qwen/qwen3-32b",                                 "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "gpt-oss-120b",    "name": "GPT OSS 120B",        "client_type": "openai_compat", "model": "openai/gpt-oss-120b",                            "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "llama4-maverick", "name": "Llama 4 Maverick",    "client_type": "openai_compat", "model": "meta-llama/llama-4-maverick-17b-128e-instruct",  "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "llama4-scout",    "name": "Llama 4 Scout",       "client_type": "openai_compat", "model": "meta-llama/llama-4-scout-17b-16e-instruct",      "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "kimi-k2",         "name": "Kimi K2",             "client_type": "openai_compat", "model": "moonshotai/kimi-k2-instruct",                    "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "allam-2-7b",      "name": "Allam 2 7B",          "client_type": "openai_compat", "model": "allam-2-7b",                                     "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
]

ALL_MODELS = COMMERCIAL_MODELS + OPENSOURCE_MODELS

MANUAL_MODEL_IDS = {"gemini-pro", "mistral-large", "deepseek-v3", "yandexgpt", "grok-3"}


# ─── Prompt ──────────────────────────────────────────────────────────────────

def build_rc_prompt(passage: str, question: str, choices: dict) -> str:
    choices_str = "\n".join(f"{k}) {v}" for k, v in choices.items())
    return f"""Quyidagi matnni o'qing va savolga javob bering.

Matn:
{passage}

Savol: {question}

Javob variantlari:
{choices_str}

Faqat bitta harf yozing: A, B, C yoki D.
Boshqa hech narsa yozmang."""


# ─── Auto-scoring ─────────────────────────────────────────────────────────────

def check_rc_response(response: str, answer: str) -> dict:
    """
    Check MCQ response — look for the correct letter (A/B/C/D).
    First check if response starts with the letter, then scan the full text.
    """
    resp = response.strip().upper()
    ans  = answer.upper()

    # Most likely: model returns just "C" or "C)" or "C."
    if resp and resp[0] == ans:
        return {"score": 100, "parsed": ans, "correct": True}

    # Scan for standalone letter
    import re
    match = re.search(r'\b([ABCD])\b', resp)
    if match:
        found = match.group(1)
        return {
            "score":   100 if found == ans else 0,
            "parsed":  found,
            "correct": found == ans,
        }

    return {"score": 0, "parsed": None, "correct": False}


# ─── API Callers ──────────────────────────────────────────────────────────────

def strip_thinking(text: str) -> str:
    import re
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


async def call_openai(model_cfg: dict, prompt: str) -> dict:
    key = os.getenv(model_cfg["api_key_env"], "")
    if not key:
        return {"error": f"No API key: {model_cfg['api_key_env']}"}
    client = AsyncOpenAI(api_key=key)
    start = time.time()
    try:
        resp = await client.chat.completions.create(
            model=model_cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0,
        )
        text = strip_thinking(resp.choices[0].message.content.strip())
        return {
            "response":   text,
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


# ─── Core benchmark logic ─────────────────────────────────────────────────────

async def run_question(q: dict, models: list) -> dict:
    prompt = build_rc_prompt(q["passage"], q["question"], q["choices"])
    tasks  = {m["id"]: call_model(m, prompt) for m in models}
    raw    = await asyncio.gather(*tasks.values(), return_exceptions=True)

    responses = {}
    for model_id, result in zip(tasks.keys(), raw):
        if isinstance(result, Exception):
            result = {"error": str(result)}

        if result.get("error"):
            responses[model_id] = {"error": result["error"], "score": 0, "correct": False}
            continue

        check = check_rc_response(result["response"], q["answer"])
        responses[model_id] = {
            "response":     result["response"],
            "latency_ms":   result.get("latency_ms"),
            "tokens":       result.get("tokens"),
            "parsed":       check["parsed"],
            "correct":      check["correct"],
            "score":        check["score"],
            "auto_checked": True,
        }

    return {**q, "responses": responses}


def compute_rc_leaderboard(rc_results: list, model_ids: list) -> dict:
    subtypes = ["hayot_bank", "kredit_freeze", "pul_otkazma"]
    scores = {m: {"overall": [], **{s: [] for s in subtypes}} for m in model_ids}

    for q in rc_results:
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
        m: {
            "overall":       avg(data["overall"]),
            "hayot_bank":    avg(data["hayot_bank"]),
            "kredit_freeze": avg(data["kredit_freeze"]),
            "pul_otkazma":   avg(data["pul_otkazma"]),
        }
        for m, data in scores.items()
    }


def export_results_js(data: dict):
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    js  = f"// Auto-generated {ts}\n"
    js += "window.BENCHMARK_RESULTS = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js, encoding="utf-8")


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="ULAB — RC Benchmark")
    parser.add_argument("--model",  help="Run only this model ID")
    parser.add_argument("--type",   help="Subtype: hayot_bank / kredit_freeze / pul_otkazma")
    parser.add_argument("--ids",    help="Comma-separated question IDs, e.g. RC-P1-Q1,RC-P2-Q3")
    parser.add_argument("--force",  action="store_true", help="Re-run even if response already exists")
    args = parser.parse_args()

    if not RC_QUESTIONS.exists():
        print(f"ERROR: {RC_QUESTIONS} not found.")
        sys.exit(1)
    if not RESULTS_JSON.exists():
        print(f"ERROR: {RESULTS_JSON} not found. Run run_benchmark.py first.")
        sys.exit(1)

    rc_data   = json.loads(RC_QUESTIONS.read_text(encoding="utf-8"))
    questions = rc_data["questions"]

    if args.ids:
        id_set    = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in id_set]
    if args.type:
        questions = [q for q in questions if q["type"] == args.type]

    models = ALL_MODELS
    if args.model:
        models = [m for m in ALL_MODELS if m["id"] == args.model]
        if not models:
            print(f"ERROR: model '{args.model}' not found. Available: {[m['id'] for m in ALL_MODELS]}")
            sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"  ULAB — Reading Comprehension Benchmark (RC)")
    print(f"{'═'*60}")
    print(f"  Questions : {len(questions)}")
    print(f"  Models    : {len(models)}")
    print(f"{'═'*60}\n")

    results     = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    existing_rc = {q["id"]: q for q in results.get("rc_questions", [])}

    for q in questions:
        qid = q["id"]

        if qid in existing_rc and not args.force:
            existing = existing_rc[qid]
            missing_models = [m for m in models if m["id"] not in existing.get("responses", {})]
            if not missing_models:
                print(f"  {qid} — skip (already done)")
                continue
            models_to_run = missing_models
        else:
            models_to_run = models

        print(f"  {qid} [{q['type']}] — {len(models_to_run)} models...")
        q_result = await run_question(q, models_to_run)

        if qid in existing_rc:
            existing_rc[qid].setdefault("responses", {}).update(q_result["responses"])
        else:
            existing_rc[qid] = q_result

        for model_id, resp in q_result["responses"].items():
            if model_id not in [m["id"] for m in models_to_run]:
                continue
            icon   = "✓" if resp.get("correct") else "✗"
            parsed = resp.get("parsed", "?")
            print(f"    {icon} {model_id:<20} → {parsed or 'N/A':<4} (expected: {q['answer']})")

        await asyncio.sleep(0.2)

    all_rc_results = list(existing_rc.values())
    all_model_ids  = list({r for q in all_rc_results for r in q.get("responses", {})})
    rc_leaderboard = compute_rc_leaderboard(all_rc_results, all_model_ids)

    results["rc_questions"]   = all_rc_results
    results["rc_leaderboard"] = rc_leaderboard

    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    export_results_js(results)

    print(f"\n{'═'*60}")
    print(f"  RC Leaderboard")
    print(f"{'═'*60}")
    sorted_lb = sorted(rc_leaderboard.items(), key=lambda x: x[1]["overall"] or 0, reverse=True)
    for rank, (model_id, s) in enumerate(sorted_lb, 1):
        ov = s["overall"]
        h  = s["hayot_bank"]
        k  = s["kredit_freeze"]
        p  = s["pul_otkazma"]
        print(f"  {rank:>2}. {model_id:<22} Overall: {str(ov)+'%':>6}  |  HayotBank: {str(h)+'%':>6}  Freeze: {str(k)+'%':>6}  Otkazma: {str(p)+'%':>6}")
    print(f"\n  Saved → results_raw.json + website/js/results.js\n")


if __name__ == "__main__":
    asyncio.run(main())
