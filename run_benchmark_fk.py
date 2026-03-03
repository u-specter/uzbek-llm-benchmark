#!/usr/bin/env python3
"""
ULAB — Fact-checking Module (FK)
Tests whether models hallucinate or correctly verify facts about
Uzbekistan (capital, independence, currency) and banking terms.

Model answers "to'g'ri" (true) or "noto'g'ri" (false) for each statement.
Scoring is fully automatic — no GPT-4o needed.

Usage:
    python run_benchmark_fk.py              # All questions, all models
    python run_benchmark_fk.py --model gpt-4o
    python run_benchmark_fk.py --type country
    python run_benchmark_fk.py --ids FK-C-01,FK-B-03
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
FK_QUESTIONS  = BASE_DIR / "questions" / "fk_questions.json"
RESULTS_JSON  = BASE_DIR / "results_raw.json"
RESULTS_JS    = BASE_DIR / "website" / "js" / "results.js"

# ─── Models (same as run_benchmark_cl.py) ────────────────────────────────────

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

MANUAL_MODEL_IDS = {"gemini-pro", "mistral-large", "deepseek-v3", "yandexgpt", "grok-3"}


# ─── Prompt ──────────────────────────────────────────────────────────────────

def build_fk_prompt(text: str) -> str:
    return f"""Quyidagi bayonot to'g'rimi yoki noto'g'rimi?

Bayonot: "{text}"

Faqat bitta javob yozing: to'g'ri / noto'g'ri

Boshqa hech narsa yozmang. Faqat bitta javob."""


# ─── Auto-scoring ─────────────────────────────────────────────────────────────

def check_fk_response(response: str, answer: str) -> dict:
    """
    Check true/false response.
    IMPORTANT: scan for "noto'g'ri" BEFORE "to'g'ri" because
    "to'g'ri" is a substring of "noto'g'ri".
    """
    resp = response.strip().lower()
    ans  = answer.lower()

    # Ordered scan: noto'g'ri must come first
    for label in ["noto'g'ri", "to'g'ri"]:
        if label in resp:
            return {
                "score":   100 if label == ans else 0,
                "parsed":  label,
                "correct": label == ans,
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
            max_tokens=512,
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
                    "max_tokens": 512,
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
                max_tokens=512,
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
    prompt = build_fk_prompt(q["text"])
    tasks  = {m["id"]: call_model(m, prompt) for m in models}
    raw    = await asyncio.gather(*tasks.values(), return_exceptions=True)

    responses = {}
    for model_id, result in zip(tasks.keys(), raw):
        if isinstance(result, Exception):
            result = {"error": str(result)}

        if result.get("error"):
            responses[model_id] = {"error": result["error"], "score": 0, "correct": False}
            continue

        check = check_fk_response(result["response"], q["answer"])
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


def compute_fk_leaderboard(fk_results: list, model_ids: list) -> dict:
    subtypes = ["country", "currency", "banking"]
    scores = {m: {"overall": [], **{s: [] for s in subtypes}} for m in model_ids}

    for q in fk_results:
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
            "overall":  avg(data["overall"]),
            "country":  avg(data["country"]),
            "currency": avg(data["currency"]),
            "banking":  avg(data["banking"]),
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
    parser = argparse.ArgumentParser(description="ULAB — FK Benchmark")
    parser.add_argument("--model",  help="Run only this model ID")
    parser.add_argument("--type",   help="Subtype: country / currency / banking")
    parser.add_argument("--ids",    help="Comma-separated question IDs, e.g. FK-C-01,FK-B-03")
    parser.add_argument("--force",  action="store_true", help="Re-run even if response already exists")
    args = parser.parse_args()

    if not FK_QUESTIONS.exists():
        print(f"ERROR: {FK_QUESTIONS} not found.")
        sys.exit(1)
    if not RESULTS_JSON.exists():
        print(f"ERROR: {RESULTS_JSON} not found. Run run_benchmark.py first.")
        sys.exit(1)

    fk_data   = json.loads(FK_QUESTIONS.read_text(encoding="utf-8"))
    questions = fk_data["questions"]

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
    print(f"  ULAB — Fact-checking Benchmark (FK)")
    print(f"{'═'*60}")
    print(f"  Questions : {len(questions)}")
    print(f"  Models    : {len(models)}")
    print(f"{'═'*60}\n")

    results     = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    existing_fk = {q["id"]: q for q in results.get("fk_questions", [])}

    for q in questions:
        qid = q["id"]

        if qid in existing_fk and not args.force:
            existing = existing_fk[qid]
            missing_models = [m for m in models if m["id"] not in existing.get("responses", {})]
            if not missing_models:
                print(f"  {qid} — skip (already done)")
                continue
            models_to_run = missing_models
        else:
            models_to_run = models

        print(f"  {qid} [{q['type']}] — {len(models_to_run)} models...")
        q_result = await run_question(q, models_to_run)

        if qid in existing_fk:
            existing_fk[qid].setdefault("responses", {}).update(q_result["responses"])
        else:
            existing_fk[qid] = q_result

        for model_id, resp in q_result["responses"].items():
            if model_id not in [m["id"] for m in models_to_run]:
                continue
            icon   = "✓" if resp.get("correct") else "✗"
            parsed = resp.get("parsed", "?")
            print(f"    {icon} {model_id:<20} → {parsed or 'N/A':<12} (expected: {q['answer']})")

        await asyncio.sleep(0.2)

    all_fk_results = list(existing_fk.values())
    all_model_ids  = list({r for q in all_fk_results for r in q.get("responses", {})})
    fk_leaderboard = compute_fk_leaderboard(all_fk_results, all_model_ids)

    results["fk_questions"]   = all_fk_results
    results["fk_leaderboard"] = fk_leaderboard

    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    export_results_js(results)

    print(f"\n{'═'*60}")
    print(f"  FK Leaderboard")
    print(f"{'═'*60}")
    sorted_lb = sorted(fk_leaderboard.items(), key=lambda x: x[1]["overall"] or 0, reverse=True)
    for rank, (model_id, s) in enumerate(sorted_lb, 1):
        ov = s["overall"]
        c  = s["country"]
        u  = s["currency"]
        b  = s["banking"]
        print(f"  {rank:>2}. {model_id:<22} Overall: {str(ov)+'%':>6}  |  Country: {str(c)+'%':>6}  Currency: {str(u)+'%':>6}  Banking: {str(b)+'%':>6}")
    print(f"\n  Saved → results_raw.json + website/js/results.js\n")


if __name__ == "__main__":
    asyncio.run(main())
