"""
Agentica Secretary Bird Migration Script
Removes all secretary-bird references and replaces with Secretary Bird identity.
Run: python scripts/rebrand_secretary_bird.py
"""
import os
from pathlib import Path

ROOT = Path("d:/_Projects/Agentica")

# Exact replacements: (find, replace)
REPLACEMENTS = [
    # Emoji
    ("🦅", "🦅"),
    # Text references
    ("Secretary Bird Standard", "Secretary Bird Standard"),
    ("secretary bird standard", "secretary bird standard"),
    ("Secretary Bird way", "Secretary Bird way"),
    ("secretary bird way", "secretary bird way"),
    ("The Secretary Bird", "The Secretary Bird"),
    ("the secretary bird", "the secretary bird"),
    ("Secretary Bird", "Secretary Bird"),
    ("secretary-bird", "secretary-bird"),
]

EXTENSIONS = {".md", ".py", ".js", ".json", ".yaml", ".yml", ".ps1", ".txt", ".html"}
SKIP_DIRS  = {".git", "node_modules", "__pycache__", ".venv", "shadow_sandbox"}

changed_files = []

for file_path in ROOT.rglob("*"):
    # Skip dirs and non-target extensions
    if file_path.is_dir():
        continue
    if any(skip in file_path.parts for skip in SKIP_DIRS):
        continue
    if file_path.suffix.lower() not in EXTENSIONS:
        continue

    try:
        original = file_path.read_text(encoding="utf-8", errors="ignore")
        modified = original
        for find, replace in REPLACEMENTS:
            modified = modified.replace(find, replace)
        if modified != original:
            file_path.write_text(modified, encoding="utf-8")
            changed_files.append(str(file_path.relative_to(ROOT)))
            print(f"  [OK] {file_path.relative_to(ROOT)}")
    except Exception as e:
        print(f"  [SKIP] {file_path.name}: {e}")

print(f"\nDone. Modified {len(changed_files)} files.")
