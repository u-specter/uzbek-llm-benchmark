#!/usr/bin/env python3
"""
ULAB — Classification Module (CL)
Tests models on sentiment, intent, and register classification.
Scoring is fully automatic — no GPT-4o needed.

Usage:
    python run_benchmark_cl.py              # All questions, all models
    python run_benchmark_cl.py --model gpt-4o
    python run_benchmark_cl.py --type sentiment
    python run_benchmark_cl.py --ids CL-S-01,CL-I-03
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
CL_QUESTIONS  = BASE_DIR / "questions" / "cl_questions.json"
RESULTS_JSON  = BASE_DIR / "results_raw.json"
RESULTS_JS    = BASE_DIR / "website" / "js" / "results.js"

# ─── Models (same as run_benchmark.py) ───────────────────────────────────────

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
    {"id": "llama-70b",      "name": "Llama 3.3 70B",      "client_type": "openai_compat", "model": "llama-3.3-70b-versatile",                         "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "qwen3-32b",      "name": "Qwen3 32B",           "client_type": "openai_compat", "model": "qwen/qwen3-32b",                                  "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "gpt-oss-120b",   "name": "GPT OSS 120B",        "client_type": "openai_compat", "model": "openai/gpt-oss-120b",                             "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "llama4-maverick","name": "Llama 4 Maverick",    "client_type": "openai_compat", "model": "meta-llama/llama-4-maverick-17b-128e-instruct",   "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "llama4-scout",   "name": "Llama 4 Scout",       "client_type": "openai_compat", "model": "meta-llama/llama-4-scout-17b-16e-instruct",       "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "kimi-k2",        "name": "Kimi K2",             "client_type": "openai_compat", "model": "moonshotai/kimi-k2-instruct",                     "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "allam-2-7b",     "name": "Allam 2 7B",          "client_type": "openai_compat", "model": "allam-2-7b",                                      "api_key_env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
]

ALL_MODELS = COMMERCIAL_MODELS + OPENSOURCE_MODELS

# Manual-only models (imported via import_manual.py --module cl)
MANUAL_MODEL_IDS = {"gemini-pro", "mistral-large", "deepseek-v3", "yandexgpt", "grok-3"}


# ─── Prompt ──────────────────────────────────────────────────────────────────

def build_prompt(text: str, choices: list) -> str:
    choices_str = " / ".join(choices)
    return f"""Quyidagi matnni o'qing va uni tasniflang.

Matn: "{text}"

Faqat bitta javob yozing: {choices_str}

Boshqa hech narsa yozmang. Faqat bitta so'z."""


# ─── Auto-scoring ─────────────────────────────────────────────────────────────

def check_response(response: str, answer: str, choices: list) -> dict:
    """Returns score (0 or 100) and whether it was parsed correctly."""
    resp = response.strip().lower()
    ans  = answer.lower()

    # Exact match
    if resp == ans:
        return {"score": 100, "parsed": ans, "correct": True}

    # Check if response starts with the answer (model added explanation)
    if resp.startswith(ans):
        return {"score": 100, "parsed": ans, "correct": True}

    # Check if any choice appears in the response (first word priority)
    first_word = resp.split()[0] if resp.split() else ""
    if first_word in [c.lower() for c in choices]:
        parsed = first_word
        return {"score": 100 if parsed == ans else 0, "parsed": parsed, "correct": parsed == ans}

    # Scan response for any valid choice label
    for choice in choices:
        if choice.lower() in resp:
            parsed = choice.lower()
            return {"score": 100 if parsed == ans else 0, "parsed": parsed, "correct": parsed == ans}

    # Could not parse a valid label
    return {"score": 0, "parsed": None, "correct": False}


# ─── API Callers (same pattern as run_benchmark.py) ──────────────────────────

def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks produced by reasoning models (Qwen3, etc.)."""
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
            max_tokens=512,   # enough for thinking models
            temperature=0,
        )
        text = strip_thinking(resp.choices[0].message.content.strip())
        return {
            "response": text,
            "latency_ms": int((time.time() - start) * 1000),
            "tokens": resp.usage.total_tokens if resp.usage else None,
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
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            data = resp.json()
            text = strip_thinking(data["content"][0]["text"].strip())
            return {
                "response": text,
                "latency_ms": int((time.time() - start) * 1000),
                "tokens": data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
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
        compat_cfg = {**model_cfg, "api_key_env": model_cfg["api_key_env"]}
        client_tmp = AsyncOpenAI(api_key=key, base_url=model_cfg["base_url"])
        start = time.time()
        try:
            resp = await client_tmp.chat.completions.create(
                model=model_cfg["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0,
            )
            return {
                "response": strip_thinking(resp.choices[0].message.content.strip()),
                "latency_ms": int((time.time() - start) * 1000),
                "tokens": resp.usage.total_tokens if resp.usage else None,
            }
        except Exception as e:
            return {"error": str(e), "latency_ms": int((time.time() - start) * 1000)}
    return {"error": f"Unknown client_type: {t}"}


# ─── Core benchmark logic ─────────────────────────────────────────────────────

async def run_question(q: dict, models: list) -> dict:
    """Run one CL question against all models."""
    prompt  = build_prompt(q["text"], q["choices"])
    tasks   = {m["id"]: call_model(m, prompt) for m in models}
    raw     = await asyncio.gather(*tasks.values(), return_exceptions=True)

    responses = {}
    for model_id, result in zip(tasks.keys(), raw):
        if isinstance(result, Exception):
            result = {"error": str(result)}

        if result.get("error"):
            responses[model_id] = {"error": result["error"], "score": 0, "correct": False}
            continue

        check = check_response(result["response"], q["answer"], q["choices"])
        responses[model_id] = {
            "response":    result["response"],
            "latency_ms":  result.get("latency_ms"),
            "tokens":      result.get("tokens"),
            "parsed":      check["parsed"],
            "correct":     check["correct"],
            "score":       check["score"],
            "auto_checked": True,
        }

    return {**q, "responses": responses}


def compute_cl_leaderboard(cl_results: list, model_ids: list) -> dict:
    """Compute per-type and overall F1-like scores for CL."""
    scores = {m: {"overall": [], "sentiment": [], "intent": [], "register": []} for m in model_ids}

    for q in cl_results:
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
            "overall":   avg(data["overall"]),
            "sentiment": avg(data["sentiment"]),
            "intent":    avg(data["intent"]),
            "register":  avg(data["register"]),
        }
        for m, data in scores.items()
    }


def export_results_js(data: dict):
    """Regenerate website/js/results.js from results_raw.json."""
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    js  = f"// Auto-generated {ts}\n"
    js += "window.BENCHMARK_RESULTS = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js, encoding="utf-8")


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="ULAB — CL Benchmark")
    parser.add_argument("--model",  help="Run only this model ID")
    parser.add_argument("--type",   help="Run only this question type: sentiment / intent / register")
    parser.add_argument("--ids",    help="Comma-separated question IDs, e.g. CL-S-01,CL-I-03")
    parser.add_argument("--force",  action="store_true", help="Re-run even if response already exists")
    args = parser.parse_args()

    if not CL_QUESTIONS.exists():
        print(f"ERROR: {CL_QUESTIONS} not found.")
        sys.exit(1)
    if not RESULTS_JSON.exists():
        print(f"ERROR: {RESULTS_JSON} not found. Run run_benchmark.py first.")
        sys.exit(1)

    cl_data  = json.loads(CL_QUESTIONS.read_text(encoding="utf-8"))
    questions = cl_data["questions"]

    # Apply filters
    if args.ids:
        id_set    = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in id_set]
    if args.type:
        questions = [q for q in questions if q["type"] == args.type]

    # Select models
    models = ALL_MODELS
    if args.model:
        models = [m for m in ALL_MODELS if m["id"] == args.model]
        if not models:
            print(f"ERROR: model '{args.model}' not found. Available: {[m['id'] for m in ALL_MODELS]}")
            sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"  ULAB — Classification Benchmark (CL)")
    print(f"{'═'*60}")
    print(f"  Questions : {len(questions)}")
    print(f"  Models    : {len(models)}")
    print(f"{'═'*60}\n")

    # Load existing results
    results = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    existing_cl = {q["id"]: q for q in results.get("cl_questions", [])}

    all_cl_results = []

    for q in questions:
        qid = q["id"]

        # Skip if already done and not --force
        if qid in existing_cl and not args.force:
            existing = existing_cl[qid]
            # Only run missing models
            missing_models = [m for m in models if m["id"] not in existing.get("responses", {})]
            if not missing_models:
                print(f"  {qid} — skip (already done)")
                all_cl_results.append(existing)
                continue
            models_to_run = missing_models
        else:
            models_to_run = models

        print(f"  {qid} [{q['type']}] — {len(models_to_run)} models...")
        q_result = await run_question(q, models_to_run)

        # Always merge: update only the models we just ran, keep others intact
        if qid in existing_cl:
            existing_cl[qid].setdefault("responses", {}).update(q_result["responses"])
        else:
            existing_cl[qid] = q_result

        # Print results
        for model_id, resp in q_result["responses"].items():
            if model_id not in [m["id"] for m in models_to_run]:
                continue
            icon = "✓" if resp.get("correct") else "✗"
            parsed = resp.get("parsed", "?")
            print(f"    {icon} {model_id:<20} → {parsed or 'N/A':<20} (expected: {q['answer']})")

        await asyncio.sleep(0.2)

    all_cl_results = list(existing_cl.values())

    # Compute leaderboard
    all_model_ids = list({r for q in all_cl_results for r in q.get("responses", {})})
    cl_leaderboard = compute_cl_leaderboard(all_cl_results, all_model_ids)

    # Update results_raw.json
    results["cl_questions"]   = all_cl_results
    results["cl_leaderboard"] = cl_leaderboard

    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    export_results_js(results)

    # Summary
    print(f"\n{'═'*60}")
    print(f"  CL Leaderboard")
    print(f"{'═'*60}")
    sorted_lb = sorted(cl_leaderboard.items(), key=lambda x: x[1]["overall"] or 0, reverse=True)
    for rank, (model_id, scores) in enumerate(sorted_lb, 1):
        overall = scores["overall"]
        sent    = scores["sentiment"]
        intent  = scores["intent"]
        reg     = scores["register"]
        print(f"  {rank:>2}. {model_id:<22} Overall: {overall or '—':>5}  |  Sentiment: {sent or '—':>5}  Intent: {intent or '—':>5}  Register: {reg or '—':>5}")
    print(f"\n  Saved → results_raw.json + website/js/results.js\n")


if __name__ == "__main__":
    asyncio.run(main())
