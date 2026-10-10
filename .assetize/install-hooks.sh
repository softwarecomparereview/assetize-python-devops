#!/usr/bin/env bash
# Install the Assetize fork-only git hooks into this clone (.git/hooks).
# Uses a symlink so later updates to .assetize/hooks apply automatically.
# Does not use core.hooksPath, so the repo's pre-commit hooks keep working.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
hooks_dir=$(git -C "$repo_root" rev-parse --git-path hooks)
[[ "$hooks_dir" = /* ]] || hooks_dir="$repo_root/$hooks_dir"
mkdir -p "$hooks_dir"

src="$repo_root/.assetize/hooks/pre-push"
dest="$hooks_dir/pre-push"
chmod +x "$src"

if [[ -e "$dest" || -L "$dest" ]]; then
  if [[ "$(readlink -f "$dest")" == "$(readlink -f "$src")" ]]; then
    echo "pre-push hook already installed"
    exit 0
  fi
  echo "A different pre-push hook already exists at $dest" >&2
  echo "Move it aside (e.g. mv \"$dest\" \"$dest.bak\") and re-run this script." >&2
  exit 1
fi

ln -s "$src" "$dest"
echo "Installed pre-push hook: $dest -> $src"
