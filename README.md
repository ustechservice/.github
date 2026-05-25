# ustechservice/.github

Org-level community files, scaffolds, and reusable workflows for every repo under the `ustechservice` GitHub organization.

This is GitHub's [special `.github` repo](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file). The contents apply organization-wide.

## What's in here

| Path | Purpose |
|---|---|
| `profile/README.md` | The org landing page shown at github.com/ustechservice |
| `.github/workflows/verify-author.yml` | **Reusable callable workflow.** Any USTech repo can invoke it with 3 lines. Enforces `webmaster@ustechservice.com` author on every commit, server-side. |
| `.github/workflow-templates/verify-author.*` | Starter template — shows up in the "Add workflow" UI as `Verify commit authors (USTech)` so new repos can adopt it in one click. |
| `templates/pre-commit` | Reference `.githooks/pre-commit` to drop into new repos (Layer 2 of the local commit-author guard). |
| `scripts/setup-repo.sh` | Reference clone-time setup script — wires `core.hooksPath` and the correct git author. |

## How to use the reusable workflow in a USTech repo

Create `.github/workflows/verify-author.yml`:

```yaml
name: Verify commit authors
on:
  push:
    branches: ["**"]
  pull_request:
jobs:
  call:
    uses: ustechservice/.github/.github/workflows/verify-author.yml@main
```

To override the required email per-repo:

```yaml
    uses: ustechservice/.github/.github/workflows/verify-author.yml@main
    with:
      required_email: ops@ustechservice.com
```

## How the 3-layer commit-author guard works

The full system lives across three layers; this repo holds the **server-side** layer plus the reference scaffolds for the other two.

1. **Claude Code PreToolUse hook** (per-developer, in `~/.claude/hooks/ustech-validate-author.sh`). Blocks `git commit` invocations by the agent if the author email is wrong. Detects USTech repos via origin URL, `.vercel/project.json`, or `CLAUDE.md` mention. **Not versioned here** — it's a global developer-machine config.
2. **Repo `.githooks/pre-commit`** (per-repo, see `templates/pre-commit`). Activated locally by `git config core.hooksPath .githooks` after clone. Blocks the commit in any shell.
3. **GitHub Action** (the reusable workflow in this repo). Cannot be bypassed by `--no-verify` or by any local config. The final hard gate.

## Bootstrapping a new USTech repo

```bash
# 1. Create + scaffold
gh repo create ustechservice/<name> --private --add-readme
git clone https://github.com/ustechservice/<name>
cd <name>

# 2. Add the 3-layer guard
mkdir -p .githooks scripts .github/workflows
curl -fsSL https://raw.githubusercontent.com/ustechservice/.github/main/templates/pre-commit > .githooks/pre-commit
curl -fsSL https://raw.githubusercontent.com/ustechservice/.github/main/scripts/setup-repo.sh > scripts/setup-repo.sh
curl -fsSL https://raw.githubusercontent.com/ustechservice/.github/main/.github/workflow-templates/verify-author.yml > .github/workflows/verify-author.yml
chmod +x .githooks/pre-commit scripts/setup-repo.sh

# 3. Activate locally
sh scripts/setup-repo.sh
```
