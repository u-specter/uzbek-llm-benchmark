#!/usr/bin/env python3
"""
ULAB — Universal Manual Import
Merges manually collected responses into results_raw.json

Поддерживаемые модели:
    gemini      — Gemini 2.5 Pro (gemini.google.com)
    mistral     — Mistral Large 2 (chat.mistral.ai)
    deepseek    — DeepSeek V3 (chat.deepseek.com)
    yandexgpt   — YandexGPT Pro (ya.ru/ai/gpt)
    grok3       — Grok 3 (grok.com)

Использование (основной модуль):
    1. Создайте шаблон:  python create_template.py --model gemini
    2. Заполните файл:   gemini_responses.json
    3. Импортируйте:     python import_manual.py --model gemini
    4. Оцените:          python score_responses.py

Использование (CL модуль):
    1. Создайте шаблон:  python create_template.py --model gemini --module cl
    2. Заполните файл:   cl_gemini_manual.json
    3. Импортируйте:     python import_manual.py --model gemini --module cl
    4. Результат уже в results_raw.json (авто-оценка, GPT-4o не нужен)
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

BASE_DIR     = Path(__file__).parent
RESULTS_JSON = BASE_DIR / "results_raw.json"
RESULTS_JS   = BASE_DIR / "website" / "js" / "results.js"
RB_QUESTIONS = BASE_DIR / "questions" / "rb_questions.json"
FK_QUESTIONS = BASE_DIR / "questions" / "fk_questions.json"
RC_QUESTIONS = BASE_DIR / "questions" / "rc_questions.json"
LQ_QUESTIONS = BASE_DIR / "questions" / "lq_questions.json"

# ── Реестр моделей ─────────────────────────────────────────────
MODEL_REGISTRY = {
    "gemini": {
        "id":       "gemini-pro",
        "name":     "Gemini 2.5 Pro",
        "provider": "Google",
        "type":     "commercial",
        "color":    "#4285F4",
        "model":    "gemini-2.5-pro",
        "url":      "gemini.google.com",
    },
    "mistral": {
        "id":       "mistral-large",
        "name":     "Mistral Large 2",
        "provider": "Mistral AI",
        "type":     "commercial",
        "color":    "#FF7000",
        "model":    "mistral-large-2407",
        "url":      "chat.mistral.ai",
    },
    "deepseek": {
        "id":       "deepseek-v3",
        "name":     "DeepSeek V3",
        "provider": "DeepSeek",
        "type":     "commercial",
        "color":    "#4D6BFE",
        "model":    "deepseek-v3",
        "url":      "chat.deepseek.com",
    },
    "yandexgpt": {
        "id":       "yandexgpt",
        "name":     "YandexGPT Pro",
        "provider": "Yandex",
        "type":     "commercial",
        "color":    "#FC3F1D",
        "model":    "yandexgpt-pro",
        "url":      "ya.ru/ai/gpt",
    },
    "grok3": {
        "id":       "grok-3",
        "name":     "Grok 3",
        "provider": "xAI",
        "type":     "commercial",
        "color":    "#1d9bf0",
        "model":    "grok-3",
        "url":      "grok.com",
    },
}


def import_cl(model_key: str, cfg: dict):
    """Import manually filled CL (classification) responses."""
    from run_benchmark_cl import check_response  # reuse auto-scoring logic

    model_id  = cfg["id"]
    resp_file = BASE_DIR / "responses" / f"cl_{model_key}_manual.json"
    cl_file   = BASE_DIR / "questions" / "cl_questions.json"

    if not resp_file.exists():
        print(f"  ОШИБКА: файл {resp_file.name} не найден.")
        print(f"  Сначала создайте шаблон:")
        print(f"    python create_template.py --model {model_key} --module cl\n")
        return

    if not cl_file.exists():
        print(f"  ОШИБКА: questions/cl_questions.json не найден.\n")
        return

    manual   = json.loads(resp_file.read_text(encoding="utf-8"))
    cl_data  = json.loads(cl_file.read_text(encoding="utf-8"))
    results  = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))

    # Build lookup for CL questions
    cl_q_map = {q["id"]: q for q in cl_data["questions"]}

    # Load existing cl_questions or start fresh
    existing_cl = {q["id"]: q for q in results.get("cl_questions", [])}

    merged = 0
    skipped = 0
    empty   = 0

    for qid, entry in manual.items():
        if qid not in cl_q_map:
            skipped += 1
            continue

        response_text = entry.get("response", "") if isinstance(entry, dict) else entry
        if not isinstance(response_text, str) or not response_text.strip():
            empty += 1
            continue

        q = cl_q_map[qid]
        check = check_response(response_text.strip(), q["answer"], q["choices"])

        if qid not in existing_cl:
            existing_cl[qid] = {**q, "responses": {}}

        existing_cl[qid].setdefault("responses", {})[model_id] = {
            "response":     response_text.strip(),
            "latency_ms":   None,
            "tokens":       None,
            "parsed":       check["parsed"],
            "correct":      check["correct"],
            "score":        check["score"],
            "auto_checked": True,
            "manual":       True,
        }
        merged += 1

    results["cl_questions"] = list(existing_cl.values())

    # Recompute CL leaderboard
    all_model_ids = list({r for q in results["cl_questions"] for r in q.get("responses", {})})
    from run_benchmark_cl import compute_cl_leaderboard
    results["cl_leaderboard"] = compute_cl_leaderboard(results["cl_questions"], all_model_ids)

    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    js  = f"// Auto-generated {ts}\n"
    js += "window.BENCHMARK_RESULTS = " + json.dumps(results, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js, encoding="utf-8")

    print(f"  ✓ CL импортировано: {merged}")
    if empty:
        print(f"  ⚠  Пустых ответов: {empty}")
    if skipped:
        print(f"  ⚠  Пропущено:      {skipped}")
    print(f"\n  Авто-оценка применена. GPT-4o не требуется.\n")


def import_rb(model_key: str, cfg: dict):
    """Import manually filled RB (robustness) responses."""
    from run_benchmark_rb import check_response  # reuse auto-scoring logic

    model_id  = cfg["id"]
    resp_file = BASE_DIR / "responses" / f"rb_{model_key}_manual.json"

    if not resp_file.exists():
        print(f"  ОШИБКА: файл {resp_file.name} не найден.")
        print(f"  Сначала создайте шаблон:")
        print(f"    python create_template.py --model {model_key} --module rb\n")
        return

    if not RB_QUESTIONS.exists():
        print(f"  ОШИБКА: questions/rb_questions.json не найден.\n")
        return

    manual   = json.loads(resp_file.read_text(encoding="utf-8"))
    rb_data  = json.loads(RB_QUESTIONS.read_text(encoding="utf-8"))
    results  = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))

    rb_q_map    = {q["id"]: q for q in rb_data["questions"]}
    existing_rb = {q["id"]: q for q in results.get("rb_questions", [])}

    merged  = 0
    skipped = 0
    empty   = 0

    for qid, entry in manual.items():
        if qid not in rb_q_map:
            skipped += 1
            continue

        response_text = entry.get("response", "") if isinstance(entry, dict) else entry
        if not isinstance(response_text, str) or not response_text.strip():
            empty += 1
            continue

        q     = rb_q_map[qid]
        check = check_response(response_text.strip(), q["answer"], q["choices"])

        if qid not in existing_rb:
            existing_rb[qid] = {**q, "responses": {}}

        existing_rb[qid].setdefault("responses", {})[model_id] = {
            "response":     response_text.strip(),
            "latency_ms":   None,
            "tokens":       None,
            "parsed":       check["parsed"],
            "correct":      check["correct"],
            "score":        check["score"],
            "auto_checked": True,
            "manual":       True,
        }
        merged += 1

    results["rb_questions"] = list(existing_rb.values())

    all_model_ids = list({r for q in results["rb_questions"] for r in q.get("responses", {})})
    from run_benchmark_rb import compute_rb_leaderboard
    results["rb_leaderboard"] = compute_rb_leaderboard(results["rb_questions"], all_model_ids)

    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    js  = f"// Auto-generated {ts}\n"
    js += "window.BENCHMARK_RESULTS = " + json.dumps(results, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js, encoding="utf-8")

    print(f"  ✓ RB импортировано: {merged}")
    if empty:
        print(f"  ⚠  Пустых ответов: {empty}")
    if skipped:
        print(f"  ⚠  Пропущено:      {skipped}")
    print(f"\n  Авто-оценка применена. GPT-4o не требуется.\n")


def import_fk(model_key: str, cfg: dict):
    """Import manually filled FK (fact-checking) responses."""
    from run_benchmark_fk import check_fk_response

    model_id  = cfg["id"]
    resp_file = BASE_DIR / "responses" / f"fk_{model_key}_manual.json"

    if not resp_file.exists():
        print(f"  ОШИБКА: файл {resp_file.name} не найден.")
        print(f"  Сначала создайте шаблон:")
        print(f"    python create_template.py --model {model_key} --module fk\n")
        return

    if not FK_QUESTIONS.exists():
        print(f"  ОШИБКА: questions/fk_questions.json не найден.\n")
        return

    manual   = json.loads(resp_file.read_text(encoding="utf-8"))
    fk_data  = json.loads(FK_QUESTIONS.read_text(encoding="utf-8"))
    results  = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))

    fk_q_map    = {q["id"]: q for q in fk_data["questions"]}
    existing_fk = {q["id"]: q for q in results.get("fk_questions", [])}

    merged  = 0
    skipped = 0
    empty   = 0

    for qid, entry in manual.items():
        if qid not in fk_q_map:
            skipped += 1
            continue

        response_text = entry.get("response", "") if isinstance(entry, dict) else entry
        if not isinstance(response_text, str) or not response_text.strip():
            empty += 1
            continue

        q     = fk_q_map[qid]
        check = check_fk_response(response_text.strip(), q["answer"])

        if qid not in existing_fk:
            existing_fk[qid] = {**q, "responses": {}}

        existing_fk[qid].setdefault("responses", {})[model_id] = {
            "response":     response_text.strip(),
            "latency_ms":   None,
            "tokens":       None,
            "parsed":       check["parsed"],
            "correct":      check["correct"],
            "score":        check["score"],
            "auto_checked": True,
            "manual":       True,
        }
        merged += 1

    results["fk_questions"] = list(existing_fk.values())

    all_model_ids = list({r for q in results["fk_questions"] for r in q.get("responses", {})})
    from run_benchmark_fk import compute_fk_leaderboard
    results["fk_leaderboard"] = compute_fk_leaderboard(results["fk_questions"], all_model_ids)

    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    js  = f"// Auto-generated {ts}\n"
    js += "window.BENCHMARK_RESULTS = " + json.dumps(results, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js, encoding="utf-8")

    print(f"  ✓ FK импортировано: {merged}")
    if empty:
        print(f"  ⚠  Пустых ответов: {empty}")
    if skipped:
        print(f"  ⚠  Пропущено:      {skipped}")
    print(f"\n  Авто-оценка применена. GPT-4o не требуется.\n")


def import_rc(model_key: str, cfg: dict):
    """Import manually filled RC (reading comprehension) responses."""
    from run_benchmark_rc import check_rc_response

    model_id  = cfg["id"]
    resp_file = BASE_DIR / "responses" / f"rc_{model_key}_manual.json"

    if not resp_file.exists():
        print(f"  ОШИБКА: файл {resp_file.name} не найден.")
        print(f"  Сначала создайте шаблон:")
        print(f"    python create_template.py --model {model_key} --module rc\n")
        return

    if not RC_QUESTIONS.exists():
        print(f"  ОШИБКА: questions/rc_questions.json не найден.\n")
        return

    manual   = json.loads(resp_file.read_text(encoding="utf-8"))
    rc_data  = json.loads(RC_QUESTIONS.read_text(encoding="utf-8"))
    results  = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))

    rc_q_map    = {q["id"]: q for q in rc_data["questions"]}
    existing_rc = {q["id"]: q for q in results.get("rc_questions", [])}

    merged  = 0
    skipped = 0
    empty   = 0

    for qid, entry in manual.items():
        if qid not in rc_q_map:
            skipped += 1
            continue

        response_text = entry.get("response", "") if isinstance(entry, dict) else entry
        if not isinstance(response_text, str) or not response_text.strip():
            empty += 1
            continue

        q     = rc_q_map[qid]
        check = check_rc_response(response_text.strip(), q["answer"])

        if qid not in existing_rc:
            existing_rc[qid] = {**q, "responses": {}}

        existing_rc[qid].setdefault("responses", {})[model_id] = {
            "response":     response_text.strip(),
            "latency_ms":   None,
            "tokens":       None,
            "parsed":       check["parsed"],
            "correct":      check["correct"],
            "score":        check["score"],
            "auto_checked": True,
            "manual":       True,
        }
        merged += 1

    results["rc_questions"] = list(existing_rc.values())

    all_model_ids = list({r for q in results["rc_questions"] for r in q.get("responses", {})})
    from run_benchmark_rc import compute_rc_leaderboard
    results["rc_leaderboard"] = compute_rc_leaderboard(results["rc_questions"], all_model_ids)

    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    js  = f"// Auto-generated {ts}\n"
    js += "window.BENCHMARK_RESULTS = " + json.dumps(results, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js, encoding="utf-8")

    print(f"  ✓ RC импортировано: {merged}")
    if empty:
        print(f"  ⚠  Пустых ответов: {empty}")
    if skipped:
        print(f"  ⚠  Пропущено:      {skipped}")
    print(f"\n  Авто-оценка применена. GPT-4o не требуется.\n")


def import_lq(model_key: str, cfg: dict):
    """Import manually filled LQ (legal Q&A) responses and score via GPT-4o."""
    import asyncio
    import os
    from openai import AsyncOpenAI

    model_id  = cfg["id"]
    resp_file = BASE_DIR / "responses" / f"lq_{model_key}_manual.json"

    if not resp_file.exists():
        print(f"  ОШИБКА: файл {resp_file.name} не найден.")
        print(f"  Сначала создайте шаблон:")
        print(f"    python create_template.py --model {model_key} --module lq\n")
        return

    if not LQ_QUESTIONS.exists():
        print(f"  ОШИБКА: questions/lq_questions.json не найден.\n")
        return

    from run_benchmark_lq import judge_answer, compute_lq_leaderboard

    manual   = json.loads(resp_file.read_text(encoding="utf-8"))
    lq_data  = json.loads(LQ_QUESTIONS.read_text(encoding="utf-8"))
    results  = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))

    lq_q_map    = {q["id"]: q for q in lq_data["questions"]}
    existing_lq = {q["id"]: q for q in results.get("lq_questions", [])}

    merged  = 0
    skipped = 0
    empty   = 0

    async def score_all():
        nonlocal merged, skipped, empty
        for qid, entry in manual.items():
            if qid not in lq_q_map:
                skipped += 1
                continue

            response_text = entry.get("response", "") if isinstance(entry, dict) else entry
            if not isinstance(response_text, str) or not response_text.strip():
                empty += 1
                continue

            q = lq_q_map[qid]
            print(f"  Оценка {qid}...", end=" ", flush=True)
            judgment = await judge_answer(q["question"], q["reference_answer"], response_text.strip())
            print(f"{judgment['parsed'] or '?'} ({judgment['score']})")

            if qid not in existing_lq:
                existing_lq[qid] = {**q, "responses": {}}

            existing_lq[qid].setdefault("responses", {})[model_id] = {
                "response":     response_text.strip(),
                "latency_ms":   None,
                "tokens":       None,
                "parsed":       judgment["parsed"],
                "correct":      judgment["correct"],
                "score":        judgment["score"],
                "verdict_raw":  judgment.get("verdict_raw"),
                "auto_checked": True,
                "manual":       True,
            }
            merged += 1

    asyncio.run(score_all())

    results["lq_questions"] = list(existing_lq.values())

    all_model_ids = list({r for q in results["lq_questions"] for r in q.get("responses", {})})
    results["lq_leaderboard"] = compute_lq_leaderboard(results["lq_questions"], all_model_ids)

    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    js  = f"// Auto-generated {ts}\n"
    js += "window.BENCHMARK_RESULTS = " + json.dumps(results, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js, encoding="utf-8")

    print(f"  ✓ LQ импортировано и оценено: {merged}")
    if empty:
        print(f"  ⚠  Пустых ответов: {empty}")
    if skipped:
        print(f"  ⚠  Пропущено:      {skipped}")
    print(f"\n  Оценка GPT-4o применена. results.js обновлён.\n")


def main():
    parser = argparse.ArgumentParser(description="ULAB Manual Import")
    parser.add_argument(
        "--model",
        required=True,
        choices=list(MODEL_REGISTRY.keys()),
        help="ID модели для импорта (gemini / mistral / deepseek / yandexgpt / grok3)",
    )
    parser.add_argument(
        "--module",
        choices=["core", "cl", "rb", "fk", "rc", "lq"],
        default="core",
        help="Модуль: core, cl, rb, fk, rc или lq (юридическое Q&A)",
    )
    args = parser.parse_args()

    cfg      = MODEL_REGISTRY[args.model]
    model_id = cfg["id"]

    print(f"\n{'═'*60}")
    print(f"  ULAB — Импорт ответов: {cfg['name']}  [{args.module.upper()}]")
    print(f"{'═'*60}\n")

    if not RESULTS_JSON.exists():
        print(f"  ОШИБКА: {RESULTS_JSON} не найден.")
        print("  Сначала запустите: python run_benchmark.py\n")
        return

    # Route to module-specific importer
    if args.module == "cl":
        import_cl(args.model, cfg)
        return
    if args.module == "rb":
        import_rb(args.model, cfg)
        return
    if args.module == "fk":
        import_fk(args.model, cfg)
        return
    if args.module == "rc":
        import_rc(args.model, cfg)
        return
    if args.module == "lq":
        import_lq(args.model, cfg)
        return

    resp_file = BASE_DIR / "responses" / f"{args.model}_responses.json"

    if not resp_file.exists():
        print(f"  ОШИБКА: файл {resp_file.name} не найден.")
        print(f"  Сначала создайте шаблон:")
        print(f"    python create_template.py --model {args.model}")
        print(f"  Заполните шаблон ответами с {cfg['url']}, затем повторите импорт.\n")
        return

    resp_data = json.loads(resp_file.read_text(encoding="utf-8"))
    results   = json.loads(RESULTS_JSON.read_text(encoding="utf-8"))

    # Добавить модель в реестр (без поля url)
    model_meta = {k: v for k, v in cfg.items() if k != "url"}
    results["models"][model_id] = model_meta

    # Слияние ответов
    merged = 0
    skipped = 0
    empty   = 0

    for q in results["questions"]:
        qid = q["id"]
        if qid not in resp_data:
            skipped += 1
            continue

        resp_text = resp_data[qid]
        if not isinstance(resp_text, str) or not resp_text.strip():
            empty += 1
            continue

        q.setdefault("responses", {})[model_id] = {
            "response":   resp_text.strip(),
            "latency_ms": None,
            "tokens":     None,
        }
        merged += 1

    results[f"{args.model}_imported_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Сохранить
    RESULTS_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    imported_at = results[f"{args.model}_imported_at"]
    js  = f"// Auto-generated — {cfg['name']} imported {imported_at}\n"
    js += "window.BENCHMARK_RESULTS = " + json.dumps(results, ensure_ascii=False, indent=2) + ";\n"
    RESULTS_JS.write_text(js, encoding="utf-8")

    print(f"  ✓ Импортировано ответов: {merged}")
    if empty:
        print(f"  ⚠  Пустых ответов:       {empty}  ← заполните их в {resp_file.name}")
    if skipped:
        print(f"  ⚠  Пропущено (нет ID):   {skipped}")

    print(f"\n  Следующий шаг — оценить ответы:")
    print(f"    python score_responses.py\n")


if __name__ == "__main__":
    main()
