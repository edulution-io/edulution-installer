#!/bin/bash
# Writes the released image digest and tag into the installer script that get.edulution.io serves.
# Usage: stamp-installer.sh <installer-file> <image-ref> <git-ref>
set -euo pipefail

file=$1
image=$2
ref=$3

replace() {
  local pattern="^$1=\"[^\"]*\"\$"
  local count
  count=$(grep -c "$pattern" "$file" || true)
  if [[ $count != 1 ]]
  then
    echo "::error::$file has $count default lines for $1, expected exactly one"
    exit 1
  fi
  sed -i "s|$pattern|$1=\"$2\"|" "$file"
  grep -qFx "$1=\"$2\"" "$file" || { echo "::error::$1 was not stamped"; exit 1; }
}

replace EDULUTION_INSTALLER_IMAGE "$image"
replace EDULUTION_INSTALLER_REF "$ref"
