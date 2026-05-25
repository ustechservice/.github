#!/usr/bin/env python3
"""
Rolls out the 3-layer commit-author guard to one or more USTech repos.

For each target repo:
  1. Locate or clone the local checkout under ~/projects/rollout-author-guard/
  2. Audit: check for existing .githooks/, existing verify-author.yml,
     and whether local git user.email is correct.
  3. Drop the three guard files:
       - .githooks/pre-commit
       - scripts/setup-repo.sh
       - .github/workflows/verify-author.yml
  4. chmod, set core.hooksPath, ensure correct user.email.
  5. Commit + push.
  6. Print the GitHub Action run ID for the user to monitor.

Idempotent: if the guard is already installed (any of the three files
exists), the repo is skipped with a SKIP status. Re-run after fixing
the conflict if needed.

Usage:
  python rollout-author-guard.py <repo1> <repo2> ...

Repo names are GitHub repo names under the ustechservice org. The script
honors case (so pass "CoreITService.com", not "coreitservice.com").
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED_EMAIL = "webmaster@ustechservice.com"
WORKDIR = Path.home() / "projects" / "rollout-author-guard"
ORG = "ustechservice"

PRE_COMMIT_BODY = """#!/bin/sh
REQUIRED="webmaster@ustechservice.com"
ACTUAL=$(git config user.email)
if [ "$ACTUAL" != "$REQUIRED" ]; then
  cat <<EOF >&2

  USTECH AUTHOR GUARD - COMMIT BLOCKED

  This repo deploys to Vercel under the USTechService account.
  Every commit must be authored as:  $REQUIRED
  Your current git author email is:  $ACTUAL
  (configured at: $(git config --show-origin user.email | head -1))

  Fix it for this repo:
      git config user.email $REQUIRED

  Then re-run your commit.

EOF
  exit 1
fi
exit 0
"""

SETUP_BODY = """#!/bin/sh
set -e
REQUIRED_EMAIL="webmaster@ustechservice.com"
echo "Setting core.hooksPath to .githooks"
git config core.hooksPath .githooks
chmod +x .githooks/* 2>/dev/null || true
ACTUAL_EMAIL=$(git config user.email || echo "")
if [ "$ACTUAL_EMAIL" != "$REQUIRED_EMAIL" ]; then
  echo "Setting local user.email to $REQUIRED_EMAIL (was: $ACTUAL_EMAIL)"
  git config user.email "$REQUIRED_EMAIL"
fi
ACTUAL_NAME=$(git config user.name || echo "")
if [ -z "$ACTUAL_NAME" ]; then
  git config user.name "USTech Webmaster"
fi
echo "Done."
"""

WORKFLOW_BODY = """name: Verify commit authors

# Delegates to the org-wide reusable workflow in ustechservice/.github.

on:
  push:
    branches: ["**"]
  pull_request:

jobs:
  call:
    uses: ustechservice/.github/.github/workflows/verify-author.yml@v1
"""

COMMIT_MESSAGE = """Add 3-layer USTech commit-author guard

Vercel rejects commits not authored as webmaster@ustechservice.com.
Three independent enforcement layers:

- .githooks/pre-commit: blocks the commit locally if author email
  is wrong. Activated by `git config core.hooksPath .githooks`.
- scripts/setup-repo.sh: one-time bootstrap for the local hook
  after a fresh clone.
- .github/workflows/verify-author.yml: server-side gate. Delegates
  to the reusable workflow in ustechservice/.github so policy
  updates land in one place org-wide.

Existing history is not affected; only newly pushed commits are
validated."""


def run(cmd: list[str] | str, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    if isinstance(cmd, list):
        return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True)
    return subprocess.run(cmd, cwd=cwd, check=check, capture_output=True, text=True, shell=True)


def status(name: str, msg: str) -> None:
    print(f"  [{name}] {msg}", flush=True)


def ensure_checkout(repo: str) -> Path:
    """Return path to a clean local checkout. Reuses existing or clones fresh."""
    candidates = [
        Path.home() / "projects" / repo,
        Path("C:/Users/vbono/projects") / repo,
        WORKDIR / repo,
    ]
    for c in candidates:
        if (c / ".git").exists():
            status(repo, f"reusing existing checkout at {c}")
            run(["git", "fetch", "origin"], cwd=c, check=False)
            # Pull main if we're on it; ignore errors (might be on a branch)
            run(["git", "pull", "--ff-only"], cwd=c, check=False)
            return c

    WORKDIR.mkdir(parents=True, exist_ok=True)
    dest = WORKDIR / repo
    if dest.exists():
        shutil.rmtree(dest)
    status(repo, f"cloning fresh into {dest}")
    run(["gh", "repo", "clone", f"{ORG}/{repo}", str(dest)])
    return dest


def audit(repo: str, root: Path) -> tuple[bool, list[str]]:
    """Return (clean_to_apply, list_of_warnings_or_blockers)."""
    issues: list[str] = []
    if (root / ".githooks" / "pre-commit").exists():
        issues.append("EXISTS: .githooks/pre-commit (will skip — manual review needed)")
    if (root / ".github" / "workflows" / "verify-author.yml").exists():
        issues.append("EXISTS: .github/workflows/verify-author.yml (will skip — manual review needed)")
    if (root / "scripts" / "setup-repo.sh").exists():
        issues.append("EXISTS: scripts/setup-repo.sh (will skip — manual review needed)")
    return (len(issues) == 0, issues)


def current_branch(root: Path) -> str:
    r = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    return r.stdout.strip()


def apply_guard(repo: str, root: Path) -> dict:
    """Drop the three files, configure, commit, push. Return result dict."""
    # Ensure local author email is correct before committing.
    cur_email = run(["git", "config", "user.email"], cwd=root, check=False).stdout.strip()
    if cur_email != REQUIRED_EMAIL:
        status(repo, f"setting local user.email {cur_email or '(unset)'} -> {REQUIRED_EMAIL}")
        run(["git", "config", "user.email", REQUIRED_EMAIL], cwd=root)

    # Write files.
    (root / ".githooks").mkdir(exist_ok=True)
    (root / ".githooks" / "pre-commit").write_text(PRE_COMMIT_BODY, newline="\n")
    (root / "scripts").mkdir(exist_ok=True)
    (root / "scripts" / "setup-repo.sh").write_text(SETUP_BODY, newline="\n")
    (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (root / ".github" / "workflows" / "verify-author.yml").write_text(WORKFLOW_BODY, newline="\n")

    # chmod (no-op on Windows but harmless)
    for f in [
        root / ".githooks" / "pre-commit",
        root / "scripts" / "setup-repo.sh",
    ]:
        try:
            f.chmod(f.stat().st_mode | 0o111)
        except Exception:
            pass

    # core.hooksPath
    run(["git", "config", "core.hooksPath", ".githooks"], cwd=root)

    # Stage
    run(["git", "add",
         ".githooks/pre-commit",
         "scripts/setup-repo.sh",
         ".github/workflows/verify-author.yml"],
        cwd=root)

    # Skip the commit if nothing actually changed (e.g. files were
    # already byte-identical from a half-applied prior run).
    diff = run(["git", "diff", "--cached", "--stat"], cwd=root, check=False)
    if not diff.stdout.strip():
        status(repo, "nothing to commit — guard files already byte-identical, skipping push")
        return {"repo": repo, "result": "noop"}

    # Commit
    run(["git", "commit", "-m", COMMIT_MESSAGE], cwd=root)
    new_sha = run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()[:7]
    status(repo, f"committed {new_sha}")

    # Push
    branch = current_branch(root)
    run(["git", "push", "origin", branch], cwd=root)
    status(repo, f"pushed origin/{branch}")

    return {"repo": repo, "result": "ok", "sha": new_sha, "branch": branch}


def process_repo(repo: str) -> dict:
    try:
        root = ensure_checkout(repo)
        clean, issues = audit(repo, root)
        if not clean:
            for i in issues:
                status(repo, i)
            return {"repo": repo, "result": "skipped", "issues": issues}
        return apply_guard(repo, root)
    except subprocess.CalledProcessError as e:
        return {
            "repo": repo,
            "result": "error",
            "stderr": (e.stderr or "")[:600],
            "cmd": e.cmd,
        }
    except Exception as e:
        return {"repo": repo, "result": "error", "stderr": str(e)[:600]}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repos", nargs="+", help="Repo names (case-sensitive) under ustechservice")
    args = p.parse_args()

    results = []
    for r in args.repos:
        print(f"\n=== {r} ===", flush=True)
        results.append(process_repo(r))

    # Summary
    print("\n" + "=" * 60)
    print("ROLLOUT SUMMARY")
    print("=" * 60)
    for r in results:
        label = r["result"].upper()
        extra = ""
        if r["result"] == "ok":
            extra = f" sha={r.get('sha')} branch={r.get('branch')}"
        elif r["result"] == "skipped":
            extra = f" — {len(r.get('issues',[]))} conflict(s)"
        elif r["result"] == "error":
            extra = f" — {r.get('stderr','')[:120]}"
        print(f"  {label:8} {r['repo']}{extra}")
    fail = sum(1 for r in results if r["result"] == "error")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
