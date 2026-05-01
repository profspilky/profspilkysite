"""
Runs on the remote FreeBSD server.
Sets TMPDIR to /home/www and streams mysqldump to stdout.

SECURITY: reads credentials from environment variables.
Set DB_USER, DB_PASS, DB_HOST, DB_NAME before running.
"""
import os
import subprocess
import sys

os.environ["TMPDIR"] = "/home/www"

CNF = "/tmp/my_fpsu.cnf"
DB = os.environ["DB_NAME"]

# Write cnf if not exists
from pathlib import Path
if not Path(CNF).exists():
    db_user = os.environ["DB_USER"]
    db_pass = os.environ["DB_PASS"]
    db_host = os.environ.get("DB_HOST", "127.0.0.1")
    Path(CNF).write_text(f"[client]\nuser={db_user}\npassword={db_pass}\nhost={db_host}\n")

TABLES = [
    "zeki2_content",
    "zeki2_categories",
    "zeki2_menu",
    "zeki2_tags",
    "zeki2_contentitem_tag_map",
    "zeki2_contact_details",
    "zeki2_joomgallery",
    "zeki2_joomgallery_catg",
]

cmd = [
    "mysqldump",
    f"--defaults-file={CNF}",
    "--single-transaction",
    "--no-tablespaces",
    DB,
] + TABLES

r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if r.returncode != 0:
    sys.stderr.write(r.stderr.decode(errors="replace"))
    sys.exit(r.returncode)

sys.stdout.buffer.write(r.stdout)
