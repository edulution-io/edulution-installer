#!/bin/bash
# Reads release tags on stdin and prints the newest final one, optionally only within one minor version.
# Usage: gh release list ... | newest-release.sh [vX.Y]
set -euo pipefail

if [[ -n ${1:-} ]]
then
  pattern="^${1//./\\.}\.[0-9]+$"
else
  pattern='^v[0-9]+\.[0-9]+\.[0-9]+$'
fi

{ grep -E "$pattern" || true; } | sort -V | tail -n 1
