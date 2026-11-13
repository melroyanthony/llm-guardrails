#!/bin/sh
# Poll a URL until it returns HTTP 200, or fail.
# A connection error is retried until the deadline. Any other HTTP status
# fails immediately. Nothing here pushes an image.
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: docker_health_smoke.sh URL TIMEOUT_SECONDS" >&2
  exit 2
fi

url=$1
timeout=$2
case "$timeout" in
  ''|*[!0-9]*)
    echo "timeout must be a whole number of seconds" >&2
    exit 2
    ;;
esac

deadline=$(( $(date +%s) + timeout ))
body=$(mktemp)
trap 'rm -f "$body"' EXIT

while :; do
  now=$(date +%s)
  if [ "$now" -ge "$deadline" ]; then
    echo "timed out waiting for HTTP 200 from ${url}" >&2
    exit 1
  fi
  code=$(curl -sS -o "$body" -w '%{http_code}' --max-time 5 "$url" || true)
  if [ "$code" = "200" ]; then
    exit 0
  fi
  case "$code" in
    ""|000)
      sleep 1
      ;;
    *)
      echo "health returned HTTP ${code}" >&2
      exit 1
      ;;
  esac
done
