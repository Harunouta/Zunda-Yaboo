"""Pre-publish hygiene check (no git push). Fails if NO paths look staged/tracked-ready."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def isForbiddenPath(path: str) -> bool:
  lowered = path.lower()
  if lowered.endswith(".gguf") or lowered.endswith(".safetensors"):
    return True
  if lowered == ".env" or (lowered.startswith(".env.") and lowered != ".env.example"):
    return True
  if lowered.startswith("logs/") or lowered == "logs":
    return True
  if lowered.startswith("checkpoints/") or lowered == "checkpoints":
    return True
  if lowered.startswith("data/restricted/"):
    return True
  if lowered.startswith("data/raw/") or lowered.startswith("data/processed/"):
    return not path.endswith("README.md")
  return False

ALLOWED_RESTRICTED = {
  "data/restricted/README.md",
  "data/restricted/.gitignore",
}


def gitLsFiles() -> list[str]:
  try:
    result = subprocess.run(
      ["git", "ls-files"],
      cwd=ROOT,
      capture_output=True,
      text=True,
      check=False,
      shell=False,
    )
  except FileNotFoundError:
    # Windows PATH may omit git.exe for non-interactive shells.
    result = subprocess.run(
      "git ls-files",
      cwd=ROOT,
      capture_output=True,
      text=True,
      check=False,
      shell=True,
    )
  if result.returncode != 0:
    print("git ls-files failed (not a git repo?); skip tracked-file scan")
    return []
  return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
  errors: list[str] = []
  tracked = gitLsFiles()
  for path in tracked:
    if path in ALLOWED_RESTRICTED:
      continue
    if isForbiddenPath(path):
      errors.append(f"tracked NO path: {path}")

  requiredDocs = [
    ROOT / "REDISTRIBUTION.md",
    ROOT / "licenses" / "THIRD_PARTY.md",
    ROOT / "data" / "restricted" / "README.md",
    ROOT / "LICENSE",
  ]
  for doc in requiredDocs:
    if not doc.exists():
      errors.append(f"missing required doc: {doc.relative_to(ROOT)}")

  # Local existence of bibles is OK; committing is not.
  restricted = ROOT / "data" / "restricted"
  if restricted.exists():
    for child in restricted.iterdir():
      if child.name in ("README.md", ".gitignore"):
        continue
      if child.is_file():
        print(f"local_ok_not_for_git: {child.relative_to(ROOT)}")

  if errors:
    print("check_redistribution: FAIL")
    for item in errors:
      print(f"  - {item}")
    return 1
  print(f"check_redistribution: OK tracked={len(tracked)}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
