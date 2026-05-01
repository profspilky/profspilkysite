"""
Runs on the remote server. Creates MySQL config, lists tables,
then dumps the needed tables to /tmp/fpsu_full_dump.sql

SECURITY: credentials are read from environment variables, not hardcoded.
Set DB_USER, DB_PASS, DB_HOST, DB_NAME before running.
"""
import os
import subprocess
import sys
from pathlib import Path

DB_USER = os.environ["DB_USER"]
DB_PASS = os.environ["DB_PASS"]
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_NAME = os.environ["DB_NAME"]

CNF_PATH = "/tmp/my_fpsu.cnf"
DUMP_PATH = "/tmp/fpsu_full_dump.sql"

TABLES = [
    "zeki2_content",
    "zeki2_categories",
    "zeki2_menu",
    "zeki2_tags",
    "zeki2_contentitem_tag_map",
]


def write_cnf() -> None:
    Path(CNF_PATH).write_text(
        f"[client]\nuser={DB_USER}\npassword={DB_PASS}\nhost={DB_HOST}\n"
    )


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("STDERR:", r.stderr[:500], file=sys.stderr)
    return r.stdout


def list_tables() -> None:
    out = run(["mysql", f"--defaults-file={CNF_PATH}", DB_NAME, "-e", "SHOW TABLES;"])
    print(out)


def dump_tables() -> None:
    cmd = [
        "mysqldump",
        f"--defaults-file={CNF_PATH}",
        "--single-transaction",
        "--no-tablespaces",
        DB_NAME,
    ] + TABLES
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        print("DUMP ERROR:", r.stderr.decode()[:500], file=sys.stderr)
        sys.exit(1)
    Path(DUMP_PATH).write_bytes(r.stdout)
    size_mb = len(r.stdout) / 1_048_576
    print(f"Dump saved: {DUMP_PATH}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    write_cnf()
    print("=== Tables in DB ===")
    list_tables()
    print("=== Dumping tables ===")
    dump_tables()
