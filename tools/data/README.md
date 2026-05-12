# tools/data/ — Файли даних для імпорту з Joomla

Ця папка **git-ignored** — великі файли сюди не потрапляють у репозиторій.

Перед запуском `import_all` потрібно покласти відповідні файли сюди.

---

## Список файлів

| Файл | Розмір | Звідки береться | Потрібен для |
|---|---|---|---|
| `fpsu_seo_dump.sql` | ~280 MB | MySQL dump з Joomla сервера | крок 0 (генерація JSON) |
| `cats.tsv` | ~50 KB | MySQL export (see SQL below) | `import_joomla` |
| `articles.tsv` | ~5 MB | MySQL export (see SQL below) | `import_joomla`, `import_images` |
| `content_bodies.json` | ~244 MB | генерується `parse_bodies.py` | `import_bodies`, `import_missing_articles` |
| `menu.tsv` | ~200 KB | MySQL export (see SQL below) | `import_pages`, `import_bodies --pages` |
| `image_paths.txt` | ~1 MB | генерується `_build_image_list.py` | `import_images` |
| `seo_inventory.json` | ~26 MB | генерується `parse_joomla_dump.py` | аналіз SEO |

---

## SQL-запити для генерації TSV файлів

### cats.tsv
```sql
SELECT id, alias, title, path, metadesc, metakey
INTO OUTFILE '/tmp/cats.tsv'
FIELDS TERMINATED BY '\t'
LINES TERMINATED BY '\n'
FROM zeki2_categories
WHERE published = 1;
```

### articles.tsv
```sql
SELECT id, alias, catid, title, metadesc, metakey, images, publish_up
INTO OUTFILE '/tmp/articles.tsv'
FIELDS TERMINATED BY '\t'
LINES TERMINATED BY '\n'
FROM zeki2_content;
```

### menu.tsv
```sql
SELECT id, title, alias, path, link, type, parent_id
INTO OUTFILE '/tmp/menu.tsv'
FIELDS TERMINATED BY '\t'
LINES TERMINATED BY '\n'
FROM zeki2_menu
WHERE published = 1;
```

---

## Порядок підготовки файлів

### 1. Зроби MySQL dump (на Joomla сервері)
```bash
mysqldump -u USER -p DATABASE zeki2_content > fpsu_seo_dump.sql
```

### 2. Скопіюй dump локально через SCP
```bash
scp -P 9092 -i key_dig_priv.pem root@78.27.236.224:/path/to/fpsu_seo_dump.sql tools/data/
```

### 3. Генеруй content_bodies.json
```bash
python tools/parse_bodies.py
# читає: tools/data/fpsu_seo_dump.sql
# пише:  tools/data/content_bodies.json
```

### 4. Отримай TSV файли
Виконай SQL-запити вище в phpMyAdmin або через mysql client, збережи у `tools/data/`.

### 5. Запускай import
```bash
python manage.py import_all
# або крок за кроком:
python manage.py import_joomla
python manage.py import_bodies --rewrite-images
python manage.py import_missing_articles --rewrite-images
python manage.py import_pages
python manage.py import_bodies --pages --rewrite-images
python manage.py seed_section_pages
python manage.py link_article_covers   # потребує articles.tsv
```

---

## Зображення до Cloudinary (ОБОВ'ЯЗКОВО для Render)

Render має ephemeral filesystem — `media/` не зберігається між деплоями.
Усі зображення мають бути завантажені до Cloudinary.

### Крок A. Збери список файлів (локально, потрібна папка `media/`)
```bash
python tools/build_image_paths.py
# → tools/image_paths.txt (44к+ шляхів)
```

### Крок B. Заповни реальні credentials у `.env`
```
CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>
CLOUDINARY_CLOUD_NAME=<cloud_name>
CLOUDINARY_API_KEY=<api_key>
CLOUDINARY_API_SECRET=<api_secret>
```

### Крок C. Завантаж до Cloudinary (локально, ~44к файлів)
```bash
python tools/upload_images_cloudinary.py
# → tools/image_map.json (зберігається і може бути відновлений після збою)
# Прогрес зберігається кожні 50 файлів — безпечно переривати та продовжувати
```

### Крок D. Застосуй map до БД
```bash
python manage.py apply_cloudinary_map
# Оновлює Article.image + переписує body HTML на Cloudinary URLs
```

### Крок E. Закомітити image_map.json
```bash
git add tools/image_map.json
git commit -m "chore: add Cloudinary image map"
git push
```

### На Render після пушу:
```bash
# В Render Shell (один раз):
python manage.py apply_cloudinary_map
```

---

## На Render (Shell консоль)

Якщо файли великі — завантажуй через wget/curl з тимчасового хостингу:

```bash
# В Render Shell:
cd /opt/render/project/src
mkdir -p tools/data

# Завантаж файли (замін URL на свої):
wget -O tools/data/cats.tsv     "https://YOUR_STORAGE/cats.tsv"
wget -O tools/data/articles.tsv "https://YOUR_STORAGE/articles.tsv"
wget -O tools/data/menu.tsv     "https://YOUR_STORAGE/menu.tsv"
wget -O tools/data/content_bodies.json "https://YOUR_STORAGE/content_bodies.json"

# Запуск:
python manage.py import_all
```
