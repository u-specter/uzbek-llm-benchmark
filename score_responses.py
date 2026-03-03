#!/usr/bin/env python3
"""
ULAB — Auto-Scorer
Uses GPT-4o as a judge to score each model response.
Reads results_raw.json, adds scores, updates website/js/results.js

Usage:
    python score_responses.py
    python score_responses.py --ids SL-01,FRM-03   # score only these questions
"""

import asyncio
import json
import os
import sys
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

BASE_DIR     = Path(__file__).parent
RESULTS_JSON = BASE_DIR / "results_raw.json"
RESULTS_JS   = BASE_DIR / "website" / "js" / "results.js"

REGISTER_NAMES = {
    "slang":            "sleng (ulichniy stil)",
    "informal":         "norasmiy (kundalik)",
    "formal_business":  "rasmiy biznes (bank uslubi)",
}

JUDGE_SYSTEM = """Sen o'zbek tili bo'yicha ekspertsan. Senga AI modelining o'zbekcha savolga bergan javobi ko'rsatiladi.
Sening vazifang — javobni 4 ta mezon bo'yicha baholash (1 dan 5 gacha shkala):

1 = Juda yomon  |  2 = Yomon  |  3 = O'rtacha  |  4 = Yaxshi  |  5 = A'lo

Faqat JSON formatida javob ber. Boshqa hech narsa yozma."""

JUDGE_PROMPT = """SAVOL (uslub: {register}):
{question}

AI JAVOBI:
{response}

Quyidagi mezonlar bo'yicha baholagin:
- D1 (Til to'g'riligi): Grammatika, imlo, morfologiya to'g'rimi?
- D2 (Uslub muvofiqligi): Javob "{register}" uslubiga mosmi? (sleng — ko'cha tili, norasmiy — oddiy muloqot, rasmiy — biznes uslubi)
- D3 (Ma'no to'g'riligi): Savol to'g'ri va to'liq javoblangandi?
- D4 (Tabiiylik): O'zbek ona tilida so'zlashuvchiga tabiiy ko'rinadimi?

Faqat JSON bilan javob ber, namuna:
{{"D1": 4, "D2": 3, "D3": 5, "D4": 4, "izoh": "Qisqa izoh o'zbek tilida"}}"""


async def score_response(client: AsyncOpenAI, q_id: str, question: str, register: str, model_name: str, response_text: str) -> dict:
    """Score a single model response using GPT-4o as judge"""
    prompt = JUDGE_PROMPT.format(
        register=REGISTER_NAMES.get(register, register),
        question=question,
        response=response_text[:2000],  # truncate very long responses
    )
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        scores = json.loads(raw)
        # Validate and clamp to 1-5
        for k in ("D1", "D2", "D3", "D4"):
            scores[k] = max(1, min(5, int(scores.get(k, 3))))
        # Total 0-100: weighted average (D1+D2+D3 each 25%, D4 15%)
        # Max raw = 5*25 + 5*25 + 5*25 + 5*15 = 450; min = 1*90 = 90
        # Scale to 0-100: (raw - 90) / (450 - 90) * 100
        raw = scores["D1"]*25 + scores["D2"]*25 + scores["D3"]*25 + scores["D4"]*15
        total = round((raw - 90) / 360 * 100)
        scores["total"] = total
        return scores
    except Exception as e:
        return {"D1": 0, "D2": 0, "D3": 0, "D4": 0, "total": 0, "izoh": f"Scoring error: {e}"}


async def score_question(client: AsyncOpenAI, q_result: dict) -> dict:
    """Score all model responses for one question"""
    question_id = q_result["id"]
    question_text = q_result["text"]
    register = q_result["register"]
    responses = q_result.get("responses", {})

    tasks = {}
    for model_id, resp_data in responses.items():
        if resp_data.get("error") or not resp_data.get("response"):
            continue
        tasks[model_id] = score_response(
            client, question_id, question_text, register,
            model_id, resp_data["response"]
        )

    if not tasks:
        return q_result

    print(f"  Scoring {question_id} ({len(tasks)} models)...")
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for model_id, score in zip(tasks.keys(), results):
        if isinstance(score, Exception):
            q_result["responses"][model_id]["scores"] = {"error": str(score)}
        else:
            q_result["responses"][model_id]["scores"] = score

    await asyncio.sleep(0.3)  # slight delay to avoid rate limits
    return q_result


def compute_leaderboard(questions: list, model_ids: list) -> dict:
    """Compute overall and per-register scores for the leaderboard"""
    leaderboard = {m: {"overall": [], "slang": [], "informal": [], "formal_business": []} for m in model_ids}

    for q in questions:
        register = q.get("register", "")
        for model_id, resp in q.get("responses", {}).items():
            scores = resp.get("scores", {})
            total = scores.get("total")
            if total and isinstance(total, (int, float)):
                leaderboard[model_id]["overall"].append(total)
                if register in leaderboard[model_id]:
                    leaderboard[model_id][register].append(total)

    summary = {}
    for model_id, data in leaderboard.items():
        summary[model_id] = {
            "overall":         round(sum(data["overall"]) / len(data["overall"]), 1) if data["overall"] else None,
            "slang":           round(sum(data["slang"]) / len(data["slang"]), 1) if data["slang"] else None,
            "informal":        round(sum(data["informal"]) / len(data["informal"]), 1) if data["informal"] else None,
            "formal_business": round(sum(data["formal_business"]) / len(data["formal_business"]), 1) if data["formal_business"] else None,
        }
    return summary


async def run_scoring(filter_ids=None, force=False):
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        print("ERROR: OPENAI_API_KEY not found in .env — needed to run GPT-4o judge.")
        sys.exit(1)

    if not RESULTS_JSON.exists():
        print(f"ERROR: {RESULTS_JSON} not found. Run run_benchmark.py first.")
        sys.exit(1)

    data = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))
    questions = data["questions"]

    if filter_ids:
        ids = set(filter_ids.split(","))
        # Clear scores for the selected questions if --force
        if force:
            for q in questions:
                if q["id"] in ids:
                    for resp in q.get("responses", {}).values():
                        resp.pop("scores", None)
        target_questions = [q for q in questions if q["id"] in ids]
    elif force:
        # Clear ALL existing scores and re-score everything
        print("  --force: clearing all existing scores...")
        for q in questions:
            for resp in q.get("responses", {}).values():
                resp.pop("scores", None)
        target_questions = [
            q for q in questions
            if any("response" in resp for resp in q.get("responses", {}).values())
        ]
    else:
        # Only score questions that have responses but no scores yet
        target_questions = [
            q for q in questions
            if any(
                "response" in resp and not resp.get("scores")
                for resp in q.get("responses", {}).values()
            )
        ]

    if not target_questions:
        print("No questions need scoring (all already scored, or run run_benchmark.py first).")
        return

    print(f"\n{'═'*60}")
    print(f"  ULAB — Auto-Scorer (GPT-4o as judge)")
    print(f"{'═'*60}")
    print(f"  Questions to score: {len(target_questions)}\n")

    client = AsyncOpenAI(api_key=key)
    start = time.time()

    # Score questions one at a time (models scored in parallel per question)
    for q in target_questions:
        scored_q = await score_question(client, q)
        # Update the question in the main list
        for i, orig_q in enumerate(questions):
            if orig_q["id"] == scored_q["id"]:
                questions[i] = scored_q
                break

    # Compute leaderboard
    model_ids = list(data["models"].keys())
    leaderboard = compute_leaderboard(questions, model_ids)
    data["leaderboard"] = leaderboard
    data["scored_at"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
    data["questions"] = questions

    # Save updated results
    RESULTS_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    js_content = f"// Auto-generated by score_responses.py — {data['scored_at']}\n"
    js_content += "window.BENCHMARK_RESULTS = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js_content, encoding="utf-8")

    elapsed = int(time.time() - start)
    print(f"\n✓ Scoring done in {elapsed}s")
    print(f"✓ Results saved. Open website/index.html in your browser.\n")

    # Print quick leaderboard
    print("  LEADERBOARD (overall score):")
    ranked = sorted(leaderboard.items(), key=lambda x: x[1]["overall"] or 0, reverse=True)
    for rank, (model_id, scores) in enumerate(ranked, 1):
        model_name = data["models"].get(model_id, {}).get("name", model_id)
        overall = scores["overall"]
        print(f"  #{rank} {model_name:<25} Overall: {overall}")


def main():
    parser = argparse.ArgumentParser(description="ULAB Auto-Scorer")
    parser.add_argument("--ids", help="Score only specific question IDs (comma-separated)")
    parser.add_argument("--force", action="store_true", help="Re-score all responses, overwriting existing scores")
    args = parser.parse_args()
    asyncio.run(run_scoring(args.ids, force=args.force))


if __name__ == "__main__":
    main()
