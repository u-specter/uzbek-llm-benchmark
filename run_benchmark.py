#!/usr/bin/env python3
"""
ULAB — Uzbek Language AI Benchmark
Runs all 60 questions against 8 AI models (4 commercial + 4 open-source)
Saves results to website/js/results.js for the dashboard

Usage:
    python run_benchmark.py              # All questions, all models
    python run_benchmark.py --register slang
    python run_benchmark.py --model gpt-4o
    python run_benchmark.py --ids SL-01,SL-02,FRM-01
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

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
QUESTIONS  = BASE_DIR / "questions" / "questions.json"
RESULTS_JS = BASE_DIR / "website" / "js" / "results.js"
RESULTS_JSON = BASE_DIR / "results_raw.json"

# ─── Model Definitions ───────────────────────────────────────────────────────
COMMERCIAL_MODELS = [
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "OpenAI",
        "type": "commercial",
        "color": "#10a37f",
        "client_type": "openai",
        "model": "gpt-4o",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None,
    },
    {
        "id": "claude-sonnet",
        "name": "Claude Sonnet 4.6",
        "provider": "Anthropic",
        "type": "commercial",
        "color": "#cc785c",
        "client_type": "anthropic",
        "model": "claude-sonnet-4-6",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": None,
    },
    {
        "id": "gemini-flash",
        "name": "Gemini 2.0 Flash",
        "provider": "Google",
        "type": "commercial",
        "color": "#4285F4",
        "client_type": "openai_compat",
        "model": "gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    # Grok 2 — manual input. Run import_grok.py after filling grok_responses.json
]

OPENSOURCE_MODELS = [
    {
        "id": "llama-70b",
        "name": "Llama 3.3 70B",
        "provider": "Meta",
        "type": "opensource",
        "color": "#0668E1",
        "client_type": "openai_compat",
        "model": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    {
        "id": "qwen3-32b",
        "name": "Qwen3 32B",
        "provider": "Alibaba",
        "type": "opensource",
        "color": "#FF6B35",
        "client_type": "openai_compat",
        "model": "qwen/qwen3-32b",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    {
        "id": "gpt-oss-120b",
        "name": "GPT OSS 120B",
        "provider": "OpenAI (OSS)",
        "type": "opensource",
        "color": "#8B5CF6",
        "client_type": "openai_compat",
        "model": "openai/gpt-oss-120b",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    {
        "id": "llama4-maverick",
        "name": "Llama 4 Maverick",
        "provider": "Meta",
        "type": "opensource",
        "color": "#EF4444",
        "client_type": "openai_compat",
        "model": "meta-llama/llama-4-maverick-17b-128e-instruct",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    {
        "id": "llama4-scout",
        "name": "Llama 4 Scout",
        "provider": "Meta",
        "type": "opensource",
        "color": "#F97316",
        "client_type": "openai_compat",
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    {
        "id": "kimi-k2",
        "name": "Kimi K2",
        "provider": "Moonshot AI",
        "type": "opensource",
        "color": "#06B6D4",
        "client_type": "openai_compat",
        "model": "moonshotai/kimi-k2-instruct",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    {
        "id": "allam-2-7b",
        "name": "Allam 2 7B",
        "provider": "SDAIA (Saudi)",
        "type": "opensource",
        "color": "#10B981",
        "client_type": "openai_compat",
        "model": "allam-2-7b",
        "api_key_env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
]

ALL_MODELS = COMMERCIAL_MODELS + OPENSOURCE_MODELS


# ─── API Callers ─────────────────────────────────────────────────────────────

async def call_openai(model_cfg: dict, question_text: str) -> dict:
    """Calls OpenAI API"""
    key = os.getenv(model_cfg["api_key_env"], "")
    if not key:
        return {"error": f"No API key: {model_cfg['api_key_env']}"}
    client = AsyncOpenAI(api_key=key)
    start = time.time()
    try:
        resp = await client.chat.completions.create(
            model=model_cfg["model"],
            messages=[{"role": "user", "content": question_text}],
            max_tokens=1024,
            temperature=0.3,
        )
        latency = int((time.time() - start) * 1000)
        return {
            "response": resp.choices[0].message.content.strip(),
            "latency_ms": latency,
            "tokens": resp.usage.total_tokens if resp.usage else None,
        }
    except Exception as e:
        return {"error": str(e), "latency_ms": int((time.time() - start) * 1000)}


async def call_anthropic(model_cfg: dict, question_text: str) -> dict:
    """Calls Anthropic Claude API"""
    key = os.getenv(model_cfg["api_key_env"], "")
    if not key:
        return {"error": f"No API key: {model_cfg['api_key_env']}"}
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=60) as client:
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
                    "messages": [{"role": "user", "content": question_text}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            latency = int((time.time() - start) * 1000)
            return {
                "response": data["content"][0]["text"].strip(),
                "latency_ms": latency,
                "tokens": data.get("usage", {}).get("input_tokens", 0)
                        + data.get("usage", {}).get("output_tokens", 0),
            }
    except Exception as e:
        return {"error": str(e), "latency_ms": int((time.time() - start) * 1000)}


async def call_openai_compat(model_cfg: dict, question_text: str) -> dict:
    """Calls any OpenAI-compatible API (Groq, xAI, Gemini)"""
    key = os.getenv(model_cfg["api_key_env"], "")
    if not key:
        return {"error": f"No API key: {model_cfg['api_key_env']}"}
    client = AsyncOpenAI(api_key=key, base_url=model_cfg["base_url"])
    start = time.time()
    try:
        resp = await client.chat.completions.create(
            model=model_cfg["model"],
            messages=[{"role": "user", "content": question_text}],
            max_tokens=1024,
            temperature=0.3,
        )
        latency = int((time.time() - start) * 1000)
        text = resp.choices[0].message.content or ""
        # DeepSeek R1 may wrap in <think>...</think> — strip it
        if "<think>" in text and "</think>" in text:
            think_end = text.find("</think>")
            text = text[think_end + 8:].strip()
        return {
            "response": text.strip(),
            "latency_ms": latency,
            "tokens": resp.usage.total_tokens if resp.usage else None,
        }
    except Exception as e:
        return {"error": str(e), "latency_ms": int((time.time() - start) * 1000)}


async def call_model(model_cfg: dict, question_text: str) -> dict:
    """Dispatch to correct API caller"""
    if model_cfg["client_type"] == "openai":
        return await call_openai(model_cfg, question_text)
    elif model_cfg["client_type"] == "anthropic":
        return await call_anthropic(model_cfg, question_text)
    else:
        return await call_openai_compat(model_cfg, question_text)


# ─── Main Benchmark Runner ────────────────────────────────────────────────────

async def run_question(question: dict, models: list) -> dict:
    """Run one question against all models concurrently"""
    print(f"  [{question['id']}] {question['text'][:60]}...")
    tasks = {m["id"]: call_model(m, question["text"]) for m in models}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    responses = {}
    for model_id, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            responses[model_id] = {"error": str(result)}
        else:
            responses[model_id] = result
    return {**question, "responses": responses}


async def run_benchmark(questions: list, models: list) -> list:
    """Run all questions sequentially (to avoid rate limit bursts)"""
    results = []
    total = len(questions)
    for i, q in enumerate(questions, 1):
        print(f"\n[{i}/{total}] Register: {q['register'].upper()} | {q['id']}")
        result = await run_question(q, models)
        results.append(result)
        # Small delay between questions to be nice to APIs
        await asyncio.sleep(0.5)
    return results


def save_results(results: list, models: list):
    """Merge new results into existing results_raw.json, then save."""
    new_model_meta = {m["id"]: {k: v for k, v in m.items() if k not in ("api_key_env", "client_type", "base_url")} for m in models}

    # Load existing data if present, otherwise start fresh
    if RESULTS_JSON.exists():
        existing = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    else:
        existing = {"benchmark_date": datetime.now().strftime("%Y-%m-%d %H:%M"), "models": {}, "questions": []}

    # Merge model metadata
    existing["models"].update(new_model_meta)
    existing["benchmark_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Build lookup of existing questions by ID
    existing_q_map = {q["id"]: q for q in existing.get("questions", [])}

    # Merge responses from new run into existing questions
    for new_q in results:
        qid = new_q["id"]
        if qid in existing_q_map:
            # Merge responses (new model responses added, existing kept)
            existing_q_map[qid].setdefault("responses", {}).update(new_q.get("responses", {}))
        else:
            existing_q_map[qid] = new_q

    # Preserve original question order
    all_question_ids = [q["id"] for q in json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]]
    merged_questions = [existing_q_map[qid] for qid in all_question_ids if qid in existing_q_map]
    existing["questions"] = merged_questions
    existing["total_questions"] = len(merged_questions)

    # Save
    RESULTS_JSON.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✓ Raw results saved: {RESULTS_JSON}")

    js_content = f"// Auto-generated by run_benchmark.py — {datetime.now().isoformat()}\n"
    js_content += "window.BENCHMARK_RESULTS = " + json.dumps(existing, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js_content, encoding="utf-8")
    print(f"✓ Website data saved: {RESULTS_JS}")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ULAB Uzbek AI Benchmark Runner")
    parser.add_argument("--register", choices=["slang", "informal", "formal_business"], help="Run only this register")
    parser.add_argument("--model", help="Run only this model ID (e.g. gpt-4o)")
    parser.add_argument("--ids", help="Comma-separated question IDs (e.g. SL-01,FRM-03)")
    args = parser.parse_args()

    # Load questions
    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    questions = data["questions"]

    # Filter questions
    if args.ids:
        ids = set(args.ids.split(","))
        questions = [q for q in questions if q["id"] in ids]
    elif args.register:
        questions = [q for q in questions if q["register"] == args.register]

    # Filter models
    models = ALL_MODELS
    if args.model:
        models = [m for m in models if m["id"] == args.model]

    # Check which API keys are available
    print("\n" + "═" * 60)
    print("  ULAB — Uzbek Language AI Benchmark")
    print("═" * 60)
    print(f"\n  Questions : {len(questions)}")
    print(f"  Models    : {len(models)}")
    print()

    available = []
    skipped = []
    for m in models:
        key = os.getenv(m["api_key_env"], "")
        if key:
            available.append(m)
            print(f"  ✓ {m['name']:<25} ({m['provider']})")
        else:
            skipped.append(m)
            print(f"  ✗ {m['name']:<25} — no {m['api_key_env']} in .env")

    if skipped:
        print(f"\n  ⚠  {len(skipped)} model(s) skipped (add keys to .env to include)")

    if not available:
        print("\n  ERROR: No API keys found. Check your .env file.\n")
        sys.exit(1)

    print(f"\n  Starting benchmark...\n" + "─" * 60)
    start = time.time()

    results = asyncio.run(run_benchmark(questions, available))
    save_results(results, available)

    elapsed = int(time.time() - start)
    print(f"\n✓ Done in {elapsed}s")
    print(f"  Open website/index.html in your browser to see results.\n")


if __name__ == "__main__":
    main()
