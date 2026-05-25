#!/bin/sh
# scripts/setup-repo.sh — Run once after `git clone`.
# Wires the repo to use the versioned .githooks/ directory and verifies
# the git author email is set correctly for USTech / Vercel deploys.

set -e

REQUIRED_EMAIL="webmaster@ustechservice.com"
REQUIRED_NAME="USTech Webmaster"

echo "→ Setting core.hooksPath to .githooks"
git config core.hooksPath .githooks
chmod +x .githooks/* 2>/dev/null || true

ACTUAL_EMAIL=$(git config user.email || echo "")
ACTUAL_NAME=$(git config user.name || echo "")

if [ "$ACTUAL_EMAIL" != "$REQUIRED_EMAIL" ]; then
  echo "→ Setting local user.email to $REQUIRED_EMAIL (was: $ACTUAL_EMAIL)"
  git config user.email "$REQUIRED_EMAIL"
fi

if [ "$ACTUAL_NAME" != "$REQUIRED_NAME" ]; then
  echo "→ Setting local user.name to $REQUIRED_NAME (was: $ACTUAL_NAME)"
  git config user.name "$REQUIRED_NAME"
fi

echo ""
echo "✓ Done. Verify:"
echo "    git config --show-origin user.email"
echo "    git config --show-origin user.name"
echo "    git config --show-origin core.hooksPath"
echo ""
echo "Note: pushes are also validated server-side by .github/workflows/verify-author.yml,"
echo "which calls ustechservice/.github/.github/workflows/verify-author.yml@main."
