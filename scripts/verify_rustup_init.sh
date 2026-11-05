#!/bin/sh
# Check a downloaded rustup-init binary before it is executed.
set -eu
file=${1:?file}
expected=${2:?expected}
actual=$(sha256sum "$file" | awk '{print $1}')
if [ "$actual" != "$expected" ]; then
  printf 'rustup-init checksum mismatch\n' >&2
  exit 1
fi
