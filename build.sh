#!/usr/bin/env bash
# =============================================================================
# build.sh — Render build hook (запускається при кожному деплої)
# =============================================================================
set -o errexit
set -o nounset
set -o pipefail

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py compilemessages

# ── Сідування даних ───────────────────────────────────────────────────────────
# seed_all.sh є ідемпотентним:
#   - якщо є tools/data/fixtures.json.gz (в репо) → одразу завантажує його
#   - якщо задано DATA_ARCHIVE_URL → спочатку скачує архів, потім завантажує
#   - якщо дані вже є в БД → пропускає імпорт
# ─────────────────────────────────────────────────────────────────────────────
echo "Запуск seed_all.sh …"
chmod +x seed_all.sh
./seed_all.sh
