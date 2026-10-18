"""Prepare only the source-connection app for Vercel; never package local data/secrets."""

import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / "deploy" / "vercel"
out.mkdir(parents=True, exist_ok=True)
source_files = [
    "apps/__init__.py",
    "apps/vercel/__init__.py",
    "apps/vercel/main.py",
    "apps/vercel/sources.py",
]
source_files += [
    str(p.relative_to(root)).replace("\\", "/")
    for p in (root / "apps/vercel/static").iterdir()
    if p.suffix in {".html", ".css", ".js"}
]
generated = {
    "app.py",
    "requirements.txt",
    "pyproject.toml",
    "vercel.json",
    ".vercelignore",
    ".python-version",
}
allowed = set(source_files) | generated
# Remove stale generated artifacts individually; never touch .vercel project identity.
for existing in out.rglob("*"):
    relative = existing.relative_to(out).as_posix()
    if existing.is_file() and not relative.startswith(".vercel/") and relative not in allowed:
        if not existing.resolve().is_relative_to(out.resolve()):
            raise RuntimeError("Output file escapes deployment directory")
        existing.unlink()
for relative in source_files:
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / relative, target)
(out / "app.py").write_text("from apps.vercel.main import app\n", encoding="utf-8")
requirements = ["fastapi==0.143.1", "pydantic==2.14.1", "uvicorn==0.54.0"]
(out / "requirements.txt").write_text("\n".join(requirements) + "\n", encoding="utf-8")
(out / "pyproject.toml").write_text(
    '[project]\nname="cdip-connections"\nversion="0.2.0"\nrequires-python=">=3.12,<3.13"\ndependencies='
    + json.dumps(requirements)
    + "\n",
    encoding="utf-8",
)
(out / "vercel.json").write_text(
    json.dumps(
        {"$schema": "https://openapi.vercel.sh/vercel.json", "framework": "fastapi"}, indent=2
    ),
    encoding="utf-8",
)
(out / ".vercelignore").write_text(".vercel\n__pycache__\n*.pyc\n.env*\n", encoding="utf-8")
files = [p for p in out.rglob("*") if p.is_file() and ".vercel" not in p.parts]
assert all(p.relative_to(out).as_posix() in allowed for p in files)
size = sum(p.stat().st_size for p in files)
print(f"Prepared {len(files)} files, {size:,} bytes; no analytics/data/secrets.")
