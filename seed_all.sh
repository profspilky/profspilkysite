#!/usr/bin/env bash
# =============================================================================
# seed_all.sh — Повне одноразове заповнення бази даних
# =============================================================================
#
# Що робить:
#   1. Скачує архів з даними (якщо задано DATA_ARCHIVE_URL)
#   2. Запускає seed_production — статичні дані (пріоритети, команда, орг-ції,
#      категорії документів, секційні сторінки)
#   3а. Якщо є tools/data/fixtures.json.gz → loaddata (швидко, ~1-2 хв)
#   3б. Якщо є TSV-файли → import_all (Joomla-пайплайн, fallback)
#
# Env-змінні:
#   DATA_ARCHIVE_URL    — URL tar.gz-архіву з файлами даних (необов'язково)
#   DATA_ARCHIVE_TOKEN  — Bearer-токен для приватних URL (необов'язково)
#   DATA_FORCE          — якщо "1", завантажує навіть якщо статті вже є
#
# Запуск:
#   ./seed_all.sh
#   DATA_ARCHIVE_URL=https://example.com/fpu_data.tar.gz ./seed_all.sh
#   DATA_FORCE=1 ./seed_all.sh
#
# Структура архіву (відносно кореня проекту):
#   tools/data/fixtures.json.gz   ← Django-фікстури (основний метод)
#   tools/gallery_cats.json       ← (legacy, для import_gallery)
#   tools/gallery.json            ← (legacy, для import_gallery)
#
# Як створити архів з db.sqlite3:
#   python manage.py dumpdata \
#       news.category news.article \
#       pages.staticpage \
#       gallery.galleryalbum gallery.galleryphoto \
#       documents.documentcategory documents.document \
#       --natural-foreign \
#       --output tools/data/fixtures.json.gz
#
#   tar -czf fpu_data.tar.gz \
#       tools/data/fixtures.json.gz \
#       tools/gallery_cats.json \
#       tools/gallery.json
#
# Де зберігати архів (безкоштовно):
#   GitHub Releases → Release Asset (до 2 GB)
#   Cloudflare R2   → free tier 10 GB + 10 M reads/month
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DATA_ARCHIVE_URL="${DATA_ARCHIVE_URL:-}"
DATA_ARCHIVE_TOKEN="${DATA_ARCHIVE_TOKEN:-}"
DATA_FORCE="${DATA_FORCE:-0}"
TOOLS_DIR="$SCRIPT_DIR/tools"
DATA_DIR="$TOOLS_DIR/data"
FIXTURES_FILE="$DATA_DIR/fixtures.json.gz"

# ── helpers ───────────────────────────────────────────────────────────────────
log()  { echo ""; echo "  [seed_all] $*"; }
ok()   { echo "  ✓  $*"; }
warn() { echo "  ⚠  $*"; }
fail() { echo ""; echo "  ✗  ERROR: $*" >&2; exit 1; }
hr()   { echo ""; echo "  ════════════════════════════════════════════════════"; }

# ── Step 1: Завантаження архіву ───────────────────────────────────────────────
if [[ -n "$DATA_ARCHIVE_URL" ]]; then
    hr
    log "Завантаження архіву даних …"
    log "URL: $DATA_ARCHIVE_URL"

    ARCHIVE="/tmp/fpu_data.tar.gz"
    CURL_OPTS=(-fsSL --retry 3 --retry-delay 5 -o "$ARCHIVE")

    if [[ -n "$DATA_ARCHIVE_TOKEN" ]]; then
        CURL_OPTS+=(-H "Authorization: Bearer $DATA_ARCHIVE_TOKEN")
    fi

    curl "${CURL_OPTS[@]}" "$DATA_ARCHIVE_URL" || fail "Не вдалося скачати архів. Перевірте DATA_ARCHIVE_URL."
    ok "Завантажено $(du -sh "$ARCHIVE" | cut -f1)"

    log "Розпаковка …"
    mkdir -p "$DATA_DIR"
    tar -xzf "$ARCHIVE" -C "$SCRIPT_DIR" || fail "Помилка розпаковки архіву."
    rm -f "$ARCHIVE"
    ok "Розпаковано до tools/"
else
    warn "DATA_ARCHIVE_URL не задано — використовуються наявні файли у tools/"
fi

# ── Step 2: Статичний сід ─────────────────────────────────────────────────────
hr
log "Статичні дані (seed_production) …"
python manage.py seed_production
ok "seed_production виконано"

# ── Step 3: Перевірка ідемпотентності ────────────────────────────────────────
hr
log "Перевірка бази даних …"

ARTICLE_COUNT=$(python manage.py shell -c \
    "from apps.news.models import Article; print(Article.objects.count())" 2>/dev/null \
    || echo "0")

if [[ "$ARTICLE_COUNT" -gt 0 && "$DATA_FORCE" != "1" ]]; then
    warn "Статті вже є в базі ($ARTICLE_COUNT записів) — пропускаю імпорт."
    warn "Щоб переімпортувати: DATA_FORCE=1 ./seed_all.sh"
    hr
    ok "seed_all.sh завершено (дані вже були в БД)"
    exit 0
fi

[[ "$DATA_FORCE" == "1" ]] && warn "DATA_FORCE=1 — повторний імпорт"

# ── Step 4а: loaddata (основний метод) ────────────────────────────────────────
if [[ -f "$FIXTURES_FILE" ]]; then
    hr
    log "Завантаження фікстур (loaddata) …"
    log "Файл: $FIXTURES_FILE ($(du -sh "$FIXTURES_FILE" | cut -f1))"

    # PostgreSQL не приймає NUL-байти (\u0000) у рядках — очищаємо перед завантаженням
    log "Очистка NUL-байтів …"
    python3 -c "
import gzip, sys
path = sys.argv[1]
with gzip.open(path, 'rb') as f:
    raw = f.read()
count = raw.count(b'\\\\u0000')
if count:
    raw = raw.replace(b'\\\\u0000', b'')
    with gzip.open(path, 'wb') as f:
        f.write(raw)
    print(f'  Видалено \\\\u0000: {count}')
else:
    print('  NUL-байтів не знайдено')
" "$FIXTURES_FILE"

    python manage.py load_fixtures "$FIXTURES_FILE" --batch-size 200
    ok "loaddata завершено"

    hr
    ok "seed_all.sh успішно завершено — сайт повністю заповнено даними"
    exit 0
fi

# ── Step 4б: import_all (fallback — якщо є TSV-файли) ────────────────────────
REQUIRED_TSV=(
    "$DATA_DIR/cats.tsv"
    "$DATA_DIR/articles.tsv"
    "$DATA_DIR/content_bodies.json"
    "$DATA_DIR/menu.tsv"
)

MISSING=()
for f in "${REQUIRED_TSV[@]}"; do
    [[ -f "$f" ]] || MISSING+=("$f")
done

if [[ ${#MISSING[@]} -eq 0 ]]; then
    hr
    log "Запуск Joomla-пайплайну (import_all) …"

    GALLERY_CATS="$TOOLS_DIR/gallery_cats.json"
    GALLERY_PHOTOS="$TOOLS_DIR/gallery.json"

    if [[ -f "$GALLERY_CATS" && -f "$GALLERY_PHOTOS" ]]; then
        log "  gallery: знайдено"
        python manage.py import_all
    else
        warn "  gallery: файли не знайдено — галерея пропущена"
        python manage.py import_all --skip-gallery
    fi

    hr
    ok "seed_all.sh успішно завершено — сайт повністю заповнено даними"
    exit 0
fi

# ── Нічого не знайдено ────────────────────────────────────────────────────────
hr
warn "Файли даних не знайдено:"
warn "  очікується: $FIXTURES_FILE"
warn "  або TSV: tools/data/cats.tsv, articles.tsv, content_bodies.json, menu.tsv"
warn ""
warn "Варіанти:"
warn "  1. Задайте DATA_ARCHIVE_URL з посиланням на fpu_data.tar.gz"
warn "  2. Завантажте файли вручну до tools/data/ та запустіть ./seed_all.sh"
hr
ok "seed_all.sh завершено (лише статичні дані)"
