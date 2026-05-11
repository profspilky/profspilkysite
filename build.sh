#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py compilemessages

# Seed essential static data only if not yet present (idempotent).
# SiteSettings, пріоритети, команда, члени — команди використовують
# update_or_create, тому повторний запуск безпечний.
python manage.py seed_priorities || true
python manage.py seed_team || true
python manage.py seed_member_organizations || true
python manage.py seed_document_categories || true
