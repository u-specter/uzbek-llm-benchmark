#!/usr/bin/env python3
"""
ULAB — Template Generator
Создаёт пустой JSON-шаблон для ручного заполнения ответов модели.

Использование:
    python create_template.py --model gemini
    python create_template.py --model mistral
    python create_template.py --model deepseek
    python create_template.py --model yandexgpt
    python create_template.py --model grok3

    # Для расширенных модулей:
    python create_template.py --model gemini --module cl
    python create_template.py --model grok3 --module cl
"""

import json
import argparse
from pathlib import Path

BASE_DIR     = Path(__file__).parent
QUESTIONS    = BASE_DIR / "questions" / "questions.json"
CL_QUESTIONS = BASE_DIR / "questions" / "cl_questions.json"
RB_QUESTIONS = BASE_DIR / "questions" / "rb_questions.json"
FK_QUESTIONS = BASE_DIR / "questions" / "fk_questions.json"
RC_QUESTIONS = BASE_DIR / "questions" / "rc_questions.json"

URLS = {
    "gemini":    "https://gemini.google.com",
    "mistral":   "https://chat.mistral.ai",
    "deepseek":  "https://chat.deepseek.com",
    "yandexgpt": "https://ya.ru/ai/gpt",
    "grok3":     "https://grok.com",
}

NAMES = {
    "gemini":    "Gemini 2.5 Pro",
    "mistral":   "Mistral Large 2",
    "deepseek":  "DeepSeek V3",
    "yandexgpt": "YandexGPT Pro",
    "grok3":     "Grok 3",
}


def create_core_template(model: str):
    """Standard QA template (60 questions)."""
    out_file = BASE_DIR / "responses" / f"{model}_responses.json"

    if out_file.exists():
        print(f"\n  ПРЕДУПРЕЖДЕНИЕ: {out_file.name} уже существует.")
        ans = input("  Перезаписать? (y/n): ").strip().lower()
        if ans != "y":
            print("  Отменено.\n")
            return

    data = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    template = {q["id"]: "" for q in data["questions"]}
    out_file.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")

    name = NAMES[model]
    url  = URLS[model]
    print(f"""
{'═'*60}
  ULAB — Шаблон создан: {out_file.name}
{'═'*60}

  Модель:  {name}
  Сайт:    {url}

  Инструкция:
  1. Откройте {url}
  2. Откройте файл MANUAL_QUESTIONS.txt — там все 60 вопросов
  3. Задавайте КАЖДЫЙ вопрос в НОВОМ чате (важно!)
  4. Скопируйте ответ в файл {out_file.name}
  5. После заполнения запустите:
       python import_manual.py --model {model}
  6. Затем оцените:
       python score_responses.py

  ⚠  Незаполненные ответы ("") будут пропущены при импорте.
{'═'*60}
""")


def create_cl_template(model: str):
    """CL module template — classification (one-word answers)."""
    if not CL_QUESTIONS.exists():
        print(f"  ОШИБКА: {CL_QUESTIONS} не найден.")
        return

    out_file = BASE_DIR / "responses" / f"cl_{model}_manual.json"

    if out_file.exists():
        print(f"\n  ПРЕДУПРЕЖДЕНИЕ: {out_file.name} уже существует.")
        ans = input("  Перезаписать? (y/n): ").strip().lower()
        if ans != "y":
            print("  Отменено.\n")
            return

    cl_data   = json.loads(CL_QUESTIONS.read_text(encoding="utf-8"))
    questions = cl_data["questions"]

    template = {}
    for q in questions:
        choices_str = " / ".join(q["choices"])
        template[q["id"]] = {
            "text":    q["text"],
            "choices": q["choices"],
            "hint":    f"Faqat bitta javob: {choices_str}",
            "response": ""
        }

    out_file.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")

    name = NAMES[model]
    url  = URLS[model]
    print(f"""
{'═'*60}
  ULAB CL — Шаблон создан: {out_file.name}
{'═'*60}

  Модель : {name}
  Сайт   : {url}
  Вопросов: {len(questions)} (sentiment / intent / register)

  Инструкция:
  1. Откройте {url}
  2. Для каждого вопроса введите промпт:
       Matn: "[текст вопроса]"
       Faqat bitta javob yozing: [варианты]
  3. Скопируйте ответ модели в поле "response" нужного ID.
  4. После заполнения запустите:
       python import_manual.py --model {model} --module cl

  ⚠  Ответ должен быть ОДНИМ словом из предложенных вариантов.
  ⚠  Незаполненные ответы ("") будут пропущены.
{'═'*60}
""")


def create_rb_template(model: str):
    """RB module template — robustness (noisy intent detection, one-word answers)."""
    if not RB_QUESTIONS.exists():
        print(f"  ОШИБКА: {RB_QUESTIONS} не найден.")
        return

    out_file = BASE_DIR / "responses" / f"rb_{model}_manual.json"

    if out_file.exists():
        print(f"\n  ПРЕДУПРЕЖДЕНИЕ: {out_file.name} уже существует.")
        ans = input("  Перезаписать? (y/n): ").strip().lower()
        if ans != "y":
            print("  Отменено.\n")
            return

    rb_data   = json.loads(RB_QUESTIONS.read_text(encoding="utf-8"))
    questions = rb_data["questions"]

    template = {}
    for q in questions:
        choices_str = " / ".join(q["choices"])
        template[q["id"]] = {
            "text":       q["text"],
            "noise_type": q["type"],
            "choices":    q["choices"],
            "hint":       f"Faqat bitta javob: {choices_str}",
            "response":   ""
        }

    out_file.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")

    name = NAMES[model]
    url  = URLS[model]
    print(f"""
{'═'*60}
  ULAB RB — Шаблон создан: {out_file.name}
{'═'*60}

  Модель  : {name}
  Сайт    : {url}
  Вопросов: {len(questions)} (зашумлённые банковские запросы)
  Задача  : определить намерение клиента несмотря на шум

  Инструкция:
  1. Откройте {url}
  2. Откройте MANUAL_RB_QUESTIONS.txt — там все 15 промптов
  3. Задавайте вопросы по порядку в ОДНОМ чате
  4. Скопируйте ответ в поле "response" нужного ID.
  5. После заполнения запустите:
       python import_manual.py --model {model} --module rb

  ⚠  Ответ должен быть ОДНИМ словом из предложенных вариантов.
  ⚠  Незаполненные ответы ("") будут пропущены.
{'═'*60}
""")


def create_fk_template(model: str):
    """FK module template — fact-checking (to'g'ri / noto'g'ri answers)."""
    if not FK_QUESTIONS.exists():
        print(f"  ОШИБКА: {FK_QUESTIONS} не найден.")
        return

    out_file = BASE_DIR / "responses" / f"fk_{model}_manual.json"

    if out_file.exists():
        print(f"\n  ПРЕДУПРЕЖДЕНИЕ: {out_file.name} уже существует.")
        ans = input("  Перезаписать? (y/n): ").strip().lower()
        if ans != "y":
            print("  Отменено.\n")
            return

    fk_data   = json.loads(FK_QUESTIONS.read_text(encoding="utf-8"))
    questions = fk_data["questions"]

    template = {}
    for q in questions:
        template[q["id"]] = {
            "text":     q["text"],
            "type":     q["type"],
            "hint":     "Faqat bitta javob: to'g'ri / noto'g'ri",
            "response": ""
        }

    out_file.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")

    name = NAMES[model]
    url  = URLS[model]
    print(f"""
{'═'*60}
  ULAB FK — Шаблон создан: {out_file.name}
{'═'*60}

  Модель  : {name}
  Сайт    : {url}
  Вопросов: {len(questions)} (факт-чек о Узбекистане и банкинге)
  Задача  : to'g'ri или noto'g'ri

  Инструкция:
  1. Откройте {url}
  2. Откройте MANUAL_FK_QUESTIONS.txt — там все 10 промптов
  3. Задавайте вопросы по порядку в ОДНОМ чате
  4. Скопируйте ответ в поле "response" нужного ID.
  5. После заполнения запустите:
       python import_manual.py --model {model} --module fk

  ⚠  Ответ: только "to'g'ri" или "noto'g'ri".
  ⚠  Незаполненные ответы ("") будут пропущены.
{'═'*60}
""")


def create_rc_template(model: str):
    """RC module template — reading comprehension (MCQ A/B/C/D answers)."""
    if not RC_QUESTIONS.exists():
        print(f"  ОШИБКА: {RC_QUESTIONS} не найден.")
        return

    out_file = BASE_DIR / "responses" / f"rc_{model}_manual.json"

    if out_file.exists():
        print(f"\n  ПРЕДУПРЕЖДЕНИЕ: {out_file.name} уже существует.")
        ans = input("  Перезаписать? (y/n): ").strip().lower()
        if ans != "y":
            print("  Отменено.\n")
            return

    rc_data   = json.loads(RC_QUESTIONS.read_text(encoding="utf-8"))
    questions = rc_data["questions"]

    template = {}
    for q in questions:
        choices_str = " / ".join(f"{k}) {v}" for k, v in q["choices"].items())
        template[q["id"]] = {
            "passage":  q["passage"],
            "question": q["question"],
            "choices":  q["choices"],
            "hint":     f"Faqat bitta harf: A / B / C / D",
            "response": ""
        }

    out_file.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")

    name = NAMES[model]
    url  = URLS[model]
    print(f"""
{'═'*60}
  ULAB RC — Шаблон создан: {out_file.name}
{'═'*60}

  Модель  : {name}
  Сайт    : {url}
  Вопросов: {len(questions)} (понимание текста — 3 отрывка × 3 вопроса)
  Задача  : ответить A, B, C или D

  Инструкция:
  1. Откройте {url}
  2. Откройте MANUAL_RC_QUESTIONS.txt — там все 9 промптов
  3. Задавайте вопросы по порядку в ОДНОМ чате
  4. Скопируйте ответ в поле "response" нужного ID.
  5. После заполнения запустите:
       python import_manual.py --model {model} --module rc

  ⚠  Ответ: только одна буква A, B, C или D.
  ⚠  Незаполненные ответы ("") будут пропущены.
{'═'*60}
""")


def main():
    parser = argparse.ArgumentParser(description="ULAB Template Generator")
    parser.add_argument("--model",  required=True, choices=list(URLS.keys()), help="Модель")
    parser.add_argument("--module", choices=["core", "cl", "rb", "fk", "rc"], default="core", help="Модуль (core / cl / rb / fk / rc)")
    args = parser.parse_args()

    if args.module == "cl":
        create_cl_template(args.model)
    elif args.module == "rb":
        create_rb_template(args.model)
    elif args.module == "fk":
        create_fk_template(args.model)
    elif args.module == "rc":
        create_rc_template(args.model)
    else:
        create_core_template(args.model)


if __name__ == "__main__":
    main()
