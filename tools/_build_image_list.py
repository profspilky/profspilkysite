"""Build tools/image_paths.txt — unique image paths referenced in articles."""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent
img_paths: set[str] = set()

# 1. Body HTML — all <img src="images/...">
bodies = json.loads((BASE / "content_bodies.json").read_text(encoding="utf-8"))
pat = re.compile(r'src=["\'](\S+?)["\']', re.I)
for art in bodies:
    text = (art.get("introtext") or "") + (art.get("fulltext") or "")
    for src in pat.findall(text):
        src = src.strip().lstrip("/")
        if src.startswith("images/"):
            img_paths.add(src)

# 2. Cover images from articles.tsv
for line in (BASE / "articles.tsv").read_text(encoding="utf-8", errors="replace").splitlines():
    parts = line.split("\t")
    if len(parts) < 8:
        continue
    try:
        data = json.loads(parts[6])
        for field in ("image_intro", "image_fulltext"):
            val = (data.get(field) or "").strip().lstrip("/")
            if val.startswith("images/"):
                img_paths.add(val)
    except Exception:
        pass

print(f"Total unique image paths: {len(img_paths)}")
(BASE / "image_paths.txt").write_text("\n".join(sorted(img_paths)), encoding="utf-8")
print("Saved: tools/image_paths.txt")
