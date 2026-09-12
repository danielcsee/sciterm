#!/usr/bin/env bash
#
# Run the latest release of aiutils (github.com/danielcsee/aiutils).
#
# Checks the newest tag on every invocation and downloads it only when the
# cached binary is a different version, so "latest" costs one API call rather
# than a 7 MB download per command. Every argument is forwarded:
#
#   scripts/aiutils.sh check
#   scripts/aiutils.sh test
#   scripts/aiutils.sh claude-to-codex
#
# The repository is private, so this uses `gh`, which already holds your
# credentials. Set AIUTILS_BIN to run a local build instead.

set -euo pipefail

REPO="${AIUTILS_REPO:-danielcsee/aiutils}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE="${AIUTILS_CACHE:-$ROOT/.aiutils/bin}"

die() { echo "aiutils.sh: $*" >&2; exit 1; }

if [ -n "${AIUTILS_BIN:-}" ]; then
  exec "$AIUTILS_BIN" "$@"
fi

command -v gh >/dev/null 2>&1 || die "gh is required to reach the private $REPO (brew install gh && gh auth login)"

case "$(uname -s)" in
  Darwin) os=darwin ;;
  Linux)  os=linux ;;
  *) die "unsupported OS $(uname -s); build from source and set AIUTILS_BIN" ;;
esac
case "$(uname -m)" in
  arm64|aarch64) arch=arm64 ;;
  x86_64|amd64)  arch=amd64 ;;
  *) die "unsupported architecture $(uname -m); build from source and set AIUTILS_BIN" ;;
esac
asset="aiutils-${os}-${arch}"

tag="$(gh release view --repo "$REPO" --json tagName -q .tagName)" \
  || die "could not read the latest release of $REPO (try: gh auth status)"
binary="$CACHE/aiutils-$tag"

if [ ! -x "$binary" ]; then
  echo "aiutils.sh: fetching $tag ($asset)" >&2
  mkdir -p "$CACHE"
  # Download beside the target and rename, so an interrupted fetch never
  # leaves a half-written binary that looks cached.
  tmp="$(mktemp "$CACHE/.download.XXXXXX")"
  trap 'rm -f "$tmp"' EXIT
  gh release download "$tag" --repo "$REPO" --pattern "$asset" --output "$tmp" --clobber
  chmod 755 "$tmp"
  mv "$tmp" "$binary"
  trap - EXIT
  # Old versions are not ours to keep: this script exists to run the newest.
  find "$CACHE" -maxdepth 1 -name 'aiutils-*' ! -name "aiutils-$tag" -delete
fi

exec "$binary" "$@"
