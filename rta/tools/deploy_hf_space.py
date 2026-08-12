#!/usr/bin/env python3
"""Deploy the Ṛta Streamlit workspace to a Hugging Face Space.

Builds a *curated subset* of the repository (the files the Streamlit app
actually needs at runtime) into ``build/hf_space`` and uploads it to a
Hugging Face Space. The GitHub monorepo is never modified.

NOTE (2026): Hugging Face's free tier no longer accepts new Streamlit
Spaces (sdk=streamlit is rejected and docker-backed Spaces require a PRO
subscription). This script still works for PRO accounts; the free path for
this app is Streamlit Community Cloud (deploy from the public GitHub repo,
main file ``legacy/streamlit/app.py``).

Prerequisites
-------------
- ``huggingface_hub`` installed:  ``pip install huggingface_hub``
- An HF access token. Set ``HF_TOKEN`` (or run ``huggingface-cli login``
  once so the token is cached).

Usage
-----
    python rta/tools/deploy_hf_space.py                    # space: <user>/rta-constraint-intelligence
    python rta/tools/deploy_hf_space.py --space my-name    # space: <user>/my-name
    python rta/tools/deploy_hf_space.py --local-only       # build build/hf_space, do not upload

The live app is served at  https://<user>-<space>.hf.space
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # rta/tools -> repo root
STAGING = os.path.join(REPO_ROOT, "build", "hf_space")

# Root-level shim modules the app imports through (engine shims live in rta/).
# Everything else at the repo root (*.py not starting with "_") is copied too.
ROOT_PY_EXCLUDE = {"smoke_test.py", "cli.py"}  # CLI/self-test scripts, not needed by the app

SPACE_FRONT_MATTER = """---
title: Ṛta — Constraint Intelligence
emoji: ◆
colorFrom: indigo
colorTo: purple
sdk: streamlit
sdk_version: 1.56.0
app_file: legacy/streamlit/app.py
pinned: false
---

# Ṛta — Constraint Intelligence

Deterministic SDC validation, generation, and pre-STA readiness review.

- **Checker** — SDC quality rules (errors / warnings / info)
- **Generator** — constraint generation with multi-corner management
- **Linter · Converter · Diff · Coverage · Clock Relations · Readiness**
- Optional **netlist-aware** cross-checks (block-level RTL / gate-level)

Run an SDC through the app or use the 🧪 Test Drive tab for samples.
Full documentation: https://github.com/RAMA-L7/rta-constraint-intelligence
"""


def _copytree_clean(src: str, dst: str) -> None:
    """Copy a directory tree, skipping caches / VCS / secrets."""
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".git", ".gitignore", ".pytest_cache",
            "*.egg-info", ".streamlit", "graphify-out", "*.log",
        ),
    )


def build_staging() -> str:
    """Assemble the deployable subset under build/hf_space. Returns its path."""
    if os.path.exists(STAGING):
        shutil.rmtree(STAGING)
    os.makedirs(STAGING)

    # 1. Space README (YAML front matter selects the Streamlit entry point).
    with open(os.path.join(STAGING, "README.md"), "w", encoding="utf-8") as f:
        f.write(SPACE_FRONT_MATTER)

    # 2. requirements.txt (Streamlit + PyYAML are the only runtime deps).
    shutil.copy2(os.path.join(REPO_ROOT, "requirements.txt"), STAGING)

    # 3. The full rta/ package (engine + branding + knowledge; shims re-export from it).
    _copytree_clean(os.path.join(REPO_ROOT, "rta"), os.path.join(STAGING, "rta"))

    # 4. The Streamlit app itself.
    _copytree_clean(os.path.join(REPO_ROOT, "legacy"), os.path.join(STAGING, "legacy"))

    # 5. Sample SDCs used by the Test Drive / sample pickers.
    _copytree_clean(os.path.join(REPO_ROOT, "samples"), os.path.join(STAGING, "samples"))

    # 6. Root-level shim modules + example custom rules.
    for name in sorted(os.listdir(REPO_ROOT)):
        if name.endswith(".py") and not name.startswith("_") and name not in ROOT_PY_EXCLUDE:
            shutil.copy2(os.path.join(REPO_ROOT, name), os.path.join(STAGING, name))
    shutil.copy2(
        os.path.join(REPO_ROOT, "custom_rules_example.yaml"),
        os.path.join(STAGING, "custom_rules_example.yaml"),
    )

    return STAGING


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--space", default="rta-constraint-intelligence",
                        help="Space name (default: rta-constraint-intelligence)")
    parser.add_argument("--local-only", action="store_true",
                        help="Only build build/hf_space; do not upload.")
    parser.add_argument("--public", action="store_true", default=True,
                        help="Create the Space as public if it does not exist (default).")
    args = parser.parse_args()

    staging = build_staging()
    print(f"[1/3] Staged deployable subset at {staging}")

    if args.local_only:
        print("[local-only] Done. Inspect the staging dir, then re-run without --local-only.")
        return 0

    try:
        from huggingface_hub import HfApi, login
    except ImportError:  # pragma: no cover
        print("error: huggingface_hub is not installed — run `pip install huggingface_hub`",
              file=sys.stderr)
        return 2

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if token:
        login(token=token)

    api = HfApi()
    who = api.whoami()
    username = who.get("name") or who.get("fullname")
    repo_id = f"{username}/{args.space}"
    print(f"[2/3] Uploading to space {repo_id} (user: {username})")

    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="streamlit",
            private=not args.public,
            exist_ok=True,
        )
    except Exception as exc:  # pragma: no cover
        print(f"error: could not create/find space {repo_id}: {exc}", file=sys.stderr)
        return 3

    api.upload_folder(folder_path=staging, repo_id=repo_id, repo_type="space")
    print(f"[3/3] Deployed. Live at https://{username}-{args.space}.hf.space")
    print(f"      Space page: https://huggingface.co/spaces/{repo_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
