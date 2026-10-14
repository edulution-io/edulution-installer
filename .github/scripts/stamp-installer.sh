#!/bin/bash
# Writes the released image digest and tag into the installer script that get.edulution.io serves.
# Usage: stamp-installer.sh <installer-file> <image-ref> <git-ref>
set -euo pipefail

file=$1
image=$2
ref=$3

# Both values end up in a script that runs as root, so only a digest and a release tag are accepted.
if [[ ! $image =~ @sha256:[0-9a-f]{64}$ ]]
then
  echo "::error::$image is not pinned by digest"
  exit 1
fi
if [[ ! $ref =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]]
then
  echo "::error::$ref is not a release tag"
  exit 1
fi

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
