"""Explicit one-time native test DB provisioning via local postgres OS account.

Run as root on a local Linux test machine. Only creates quant_m0 role/database.
Refuses existing objects rather than altering a database owned by another project.
"""
import os
from pathlib import Path
import subprocess
from urllib.parse import urlparse

if os.geteuid() != 0:
    raise SystemExit("Run as root on the local Linux test host")
root = Path(__file__).resolve().parents[2]
values = dict(line.split("=", 1) for line in (root / ".env").read_text().splitlines() if "=" in line)
url = urlparse(values["DATABASE_URL"])
if url.username != "quant_m0" or url.path != "/quant_m0" or not url.password:
    raise SystemExit("Only generated quant_m0 demo configuration supported")
if not all(c in "0123456789abcdef" for c in url.password):
    raise SystemExit("Use generated hexadecimal database password")
query = "SELECT EXISTS(SELECT FROM pg_roles WHERE rolname='quant_m0') OR EXISTS(SELECT FROM pg_database WHERE datname='quant_m0');"
existing = subprocess.check_output(["runuser", "-u", "postgres", "--", "psql", "-Atc", query], text=True).strip()
if existing != "f":
    raise SystemExit("quant_m0 exists; no changes made")
sql = f"CREATE ROLE quant_m0 LOGIN PASSWORD '{url.password}';\nCREATE DATABASE quant_m0 OWNER quant_m0;\n"
subprocess.run(["runuser", "-u", "postgres", "--", "psql", "-v", "ON_ERROR_STOP=1"], input=sql, text=True, check=True)
print("Created isolated quant_m0 database and role")
