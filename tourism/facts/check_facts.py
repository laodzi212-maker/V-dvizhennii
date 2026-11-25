#!/usr/bin/env python3
"""
Сверка текстов «В движении» с единой таблицей фактов (facts.json).

Что проверяет:
  1. Устаревшие и запрещённые формулировки (старая цена в евро, старая ссылка, «9 лет вожу группы» и т. д.)
  2. Даты поездок: диапазон должен быть в утверждённом расписании
  3. Цены в рублях: сумма должна совпадать с ценой поездки из таблицы
  4. Ссылки: только разрешённые домены
  5. Кодовые слова: только из списка, «ГИМАЛАИ» запрещено
  6. Стиль: без восклицательных знаков, эмодзи, запрещённых слов; в субтитрах не больше 6 слов в строке

Коды выхода:
  0 — всё чисто
  1 — есть ошибки: публиковать нельзя
  2 — ошибок нет, но есть расхождения между документами, нужно «да» Никиты

Использование:
  python3 check_facts.py файл1.txt файл2.srt ...        проверить файлы
  python3 check_facts.py --dir папка                    проверить все .txt .md .srt .ass .json в папке
  cat подпись.txt | python3 check_facts.py -            проверить текст из stdin
  python3 check_facts.py --json файл.md                 результат в JSON для агента
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FACTS = json.loads((HERE / "facts.json").read_text(encoding="utf-8"))

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}
DASH = r"[–—\-]"

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\U00002B00-\U00002BFF️]"
)


def approved_ranges():
    """Утверждённые диапазоны дат: {(d1, m1, d2, m2): trip_id}."""
    out = {}
    for t in FACTS["trips"]:
        if t.get("dates"):
            a, b = t["dates"]
            d1, m1 = map(int, a.split("."))
            d2, m2 = map(int, b.split("."))
            out[(d1, m1, d2, m2)] = t["id"]
    for p in FACTS.get("partner_trips_not_in_nine", []):
        for a, b in p.get("dates_2027", []):
            d1, m1 = map(int, a.split("."))
            d2, m2 = map(int, b.split("."))
            out[(d1, m1, d2, m2)] = p["id"]
    return out


def approved_prices():
    prices = {}
    for t in FACTS["trips"]:
        if t.get("price_rub"):
            prices[t["price_rub"]] = t["id"]
    for p in FACTS.get("partner_trips_not_in_nine", []):
        for k in ("price_rub", "early_price_rub"):
            if p.get(k):
                prices[p[k]] = p["id"]
    return prices


def find_ranges(text):
    """Находит диапазоны дат в трёх записях: 30.04–11.05, 12–23.04, «30 апреля — 11 мая», «12–23 апреля»."""
    found = []
    for m in re.finditer(rf"(\d{{1,2}})\.(\d{{2}})\s?{DASH}\s?(\d{{1,2}})\.(\d{{2}})", text):
        d1, m1, d2, m2 = map(int, m.groups())
        found.append(((d1, m1, d2, m2), m.group(0), m.start()))
    for m in re.finditer(rf"(?<![\d.])(\d{{1,2}})\s?{DASH}\s?(\d{{1,2}})\.(\d{{2}})(?!\d*\.\d{{2}}\.)", text):
        d1, d2, mm = map(int, m.groups())
        # исключаем случаи вида 30.04–11.05 (там уже есть пара)
        if not re.match(rf"\d{{1,2}}\.\d{{2}}\s?{DASH}", text[max(0, m.start() - 6):m.end()]):
            found.append(((d1, mm, d2, mm), m.group(0), m.start()))
    months = "|".join(MONTHS)
    for m in re.finditer(rf"(\d{{1,2}})\s+({months})\s?{DASH}\s?(\d{{1,2}})\s+({months})", text, re.I):
        d1, mn1, d2, mn2 = m.groups()
        found.append(((int(d1), MONTHS[mn1.lower()], int(d2), MONTHS[mn2.lower()]), m.group(0), m.start()))
    for m in re.finditer(rf"(?<![\d.])(\d{{1,2}})\s?{DASH}\s?(\d{{1,2}})\s+({months})", text, re.I):
        d1, d2, mn = m.groups()
        found.append(((int(d1), MONTHS[mn.lower()], int(d2), MONTHS[mn.lower()]), m.group(0), m.start()))
    # убрать дубли по позиции
    seen, uniq = set(), []
    for rng, raw, pos in found:
        key = (rng, pos // 3)
        if key not in seen:
            seen.add(key)
            uniq.append((rng, raw, pos))
    return uniq


def find_prices(text):
    out = []
    for m in re.finditer(r"(\d{1,3}(?:[   ]\d{3})+|\d{4,7})\s?(?:₽|руб|р\.)", text):
        val = int(re.sub(r"[^\d]", "", m.group(1)))
        out.append((val, m.group(0), m.start()))
    return out


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def strip_srt(text, path):
    """Для SRT/ASS убираем служебные строки, оставляем реплики; считаем слова в репликах."""
    cues = []
    suf = path.suffix.lower()
    if suf == ".srt":
        for block in re.split(r"\n\s*\n", text.strip()):
            lines = block.strip().splitlines()
            if len(lines) >= 3:
                cues.append(" ".join(lines[2:]))
    elif suf == ".ass":
        for ln in text.splitlines():
            if ln.startswith("Dialogue:"):
                cues.append(re.sub(r"\{[^}]*\}", "", ln.split(",", 9)[-1]).replace("\\N", " "))
    return cues


def check_text(text, name="stdin", path=None):
    findings = []  # (level, rule, message, line)

    def add(level, rule, msg, pos):
        findings.append({"level": level, "rule": rule, "message": msg, "line": line_of(text, pos) if pos is not None else None, "file": name})

    # 1. устаревшее
    for rule in FACTS["stale"]:
        for m in re.finditer(rule["pattern"], text, re.I):
            add("error", "stale", f"«{m.group(0)}»: {rule['why']}", m.start())

    # предупреждения (нужно уточнение, но не запрет)
    for rule in FACTS.get("warn_patterns", []):
        if rule.get("check") == "claims":
            for m in re.finditer(rule["pattern"], text, re.I):
                nums = re.findall(r"\d+", m.group(0))
                if int(nums[0]) != FACTS["claims"]["retreats"] or int(nums[1]) != FACTS["claims"]["countries"]:
                    add("error", "claims", f"«{m.group(0)}»: верно 18 ретритов в 5 странах", m.start())
            continue
        for m in re.finditer(rule["pattern"], text, re.I):
            add("warn", "warn", f"«{m.group(0)}»: {rule['why']}", m.start())

    # иностранные слова: только русский язык в текстах для публикации
    allow = {"instagram","telegram","youtube","metricool","atlantum","whatsapp","reels","ok","pdf"}
    if path is None or path.suffix.lower() in (".txt", ".md", ".srt", ".ass"):
        for m in re.finditer(r"(?<![\w./@-])[A-Za-z]{3,}(?![\w./@-])", text):
            if m.group(0).lower() not in allow:
                add("warn", "latin", f"«{m.group(0)}»: иностранное слово, по возможности по-русски", m.start())

    # конфликты между документами
    conflicts = {c["id"]: c for c in FACTS["conflicts"]}
    conflict_hits = set()
    for cp in FACTS.get("conflict_patterns", []):
        for m in re.finditer(cp["pattern"], text, re.I):
            c = conflicts[cp["conflict"]]
            conflict_hits.add(cp["conflict"])
            add("conflict", cp["conflict"], f"«{m.group(0)}»: расхождение в документах — {c['topic']}. Варианты: " + "; ".join(c["values"]) + f". Решает: {c['decides']}", m.start())

    # 2. даты
    ap = approved_ranges()
    conflict_dates = set()
    for cp in FACTS.get("conflict_patterns", []):
        pass
    for rng, raw, pos in find_ranges(text):
        if rng in ap:
            continue
        # уже отмечено как конфликт?
        window = text[max(0, pos - 2):pos + len(raw) + 2]
        if any(re.search(cp["pattern"], window, re.I) for cp in FACTS.get("conflict_patterns", [])):
            continue
        add("error", "date", f"«{raw}»: такого диапазона нет в утверждённом расписании", pos)

    # 3. цены
    pr = approved_prices()
    for val, raw, pos in find_prices(text):
        if val in pr:
            continue
        if any(re.search(cp["pattern"], raw, re.I) for cp in FACTS.get("conflict_patterns", [])):
            continue
        add("error", "price", f"«{raw.strip()}»: цены {val:,} ₽ нет в таблице фактов".replace(",", " "), pos)

    # 4. ссылки
    allowed = FACTS["allowed_domains"]
    for m in re.finditer(r"(?:https?://)?((?:[a-z0-9-]+\.)+(?:ru|life|com|me|ws|net|org))(?:/[^\s)\]]*)?", text, re.I):
        host = m.group(1).lower()
        if host in allowed or host.endswith(".youretreat.ru"):
            continue
        if re.search(r"\.(?:png|jpg|jpeg|mp4|srt|ass|json|md|txt|py|html)$", host):
            continue
        if host in ("tilda.ws",) or host.endswith(".tilda.ws"):
            continue  # поймает правило stale
        add("warn", "link", f"«{m.group(0)}»: домен не в списке разрешённых ({', '.join(allowed)})", m.start())

    # 5. кодовые слова
    for bc in FACTS.get("banned_codes", []):
        for m in re.finditer(rf"код(?:овое слово)?\s*[:—-]?\s*[«\"]?{bc}", text, re.I):
            add("error", "code", f"кодовое слово {bc} занято: {FACTS['banned_codes_note']}", m.start())

    # 6. стиль
    st = FACTS["style"]
    if st.get("no_exclamations"):
        for m in re.finditer(r"(?<!<)!(?!--)", text):
            add("error", "style", "восклицательный знак: по брендбуку без восклицаний", m.start())
    if st.get("no_emoji"):
        for m in EMOJI_RE.finditer(text):
            add("error", "style", f"эмодзи {m.group(0)}: по брендбуку без эмодзи", m.start())
    for w in st.get("banned_words", []):
        for m in re.finditer(w, text, re.I):
            add("error", "style", f"слово «{m.group(0)}…» запрещено голосом бренда", m.start())

    # субтитры: слов в реплике
    if path is not None and path.suffix.lower() in (".srt", ".ass"):
        lim = st.get("max_words_per_cue", 6)
        for i, cue in enumerate(strip_srt(text, path), 1):
            n = len(cue.split())
            if n > lim:
                findings.append({"level": "warn", "rule": "cue-length", "message": f"реплика {i}: {n} слов, лимит {lim}: «{cue[:50]}»", "line": None, "file": name})

    return findings


def read_any(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    return text


def main():
    ap = argparse.ArgumentParser(description="Сверка текстов с таблицей фактов «В движении»")
    ap.add_argument("files", nargs="*")
    ap.add_argument("--dir")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results = []
    if args.dir:
        for p in sorted(Path(args.dir).rglob("*")):
            if p.is_file() and p.suffix.lower() in (".txt", ".md", ".srt", ".ass", ".json", ".html") and "node_modules" not in p.parts:
                results += check_text(read_any(p), str(p), p)
    for f in args.files:
        if f == "-":
            results += check_text(sys.stdin.read(), "stdin")
        else:
            p = Path(f)
            results += check_text(read_any(p), str(p), p)

    errors = [r for r in results if r["level"] == "error"]
    conflicts = [r for r in results if r["level"] == "conflict"]
    warns = [r for r in results if r["level"] == "warn"]

    if args.json:
        print(json.dumps({"errors": errors, "conflicts": conflicts, "warnings": warns}, ensure_ascii=False, indent=2))
    else:
        for tag, items in (("ОШИБКА", errors), ("РАСХОЖДЕНИЕ", conflicts), ("ВНИМАНИЕ", warns)):
            for r in items:
                loc = f"{r['file']}:{r['line']}" if r["line"] else r["file"]
                print(f"[{tag}] {loc}  {r['message']}")
        if not results:
            print("Чисто: расхождений с таблицей фактов нет.")
        else:
            print(f"\nИтого: ошибок {len(errors)}, расхождений между документами {len(conflicts)}, замечаний {len(warns)}.")

    sys.exit(1 if errors else (2 if conflicts else 0))


if __name__ == "__main__":
    main()
