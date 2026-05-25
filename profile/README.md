# USTechService

Independent IT consulting, cybersecurity research, and AI/ML tooling out of Metro Detroit.

We build training resources, niche publisher sites, and internal automation across a 750+ domain portfolio. Code here ships under the USTechService brand and across our [DarkDataLabs](https://github.com/darkdatalabs) projects.

## Conventions every USTech repo follows

- **Commit author:** `webmaster@ustechservice.com`. Three-layer guard enforces this — Claude Code PreToolUse hook, repo-versioned `.githooks/pre-commit`, and the reusable workflow [`verify-author.yml`](./.github/workflows/verify-author.yml). Vercel's deploy pipeline rejects anything else.
- **Default stack:** Next.js + TypeScript + Tailwind on Vercel, FastAPI + Supabase on Railway/Fly, n8n on Contabo for automation.
- **Brand-neutral content:** Editorial / publisher sites do not name vendor products without explicit clearance. Affiliate-readiness is built in from day one.

## Reusable workflows

Drop this into any USTech repo at `.github/workflows/verify-author.yml`:

```yaml
name: Verify commit authors
on:
  push:
    branches: ["**"]
  pull_request:
jobs:
  call:
    uses: ustechservice/.github/.github/workflows/verify-author.yml@v1
```

Update the policy in one place (this repo); every consumer picks it up on next push.

## Scaffold helpers

- [`scripts/setup-repo.sh`](./scripts/setup-repo.sh) — wires `core.hooksPath` + correct git author. Run once after cloning any USTech repo.
- [`templates/pre-commit`](./templates/pre-commit) — drop-in `.githooks/pre-commit` for new repos.
