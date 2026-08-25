#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

cd "${ROOT}"
CAPABILITY_INDEX="${SURFSENSE_CAPABILITY_INDEX:-${ROOT}/generated/capabilities/index.json}"
if [[ ! -f "${ROOT}/bundle/index.html" || ! -f "${ROOT}/generated/VideoRenderInput.mjs" || ! -f "${CAPABILITY_INDEX}" ]]; then
  npm run build
fi
node harness-fixtures/smoke-input.mjs "${WORK}/input.json"
node render.mjs --bundle-dir "${ROOT}/bundle" --preflight "${WORK}/input.json"
node render.mjs --bundle-dir "${ROOT}/bundle" --stills "${WORK}/input.json" "${WORK}/stills"
node render.mjs --bundle-dir "${ROOT}/bundle" "${WORK}/input.json" "${WORK}/smoke.mp4"

test -s "${WORK}/smoke.mp4"
test -s "${WORK}/smoke.mp4.render.json"
test -s "${WORK}/stills/contact-sheet.png"
test ! -e "${ROOT}/src/scenes"
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height \
  -of default=noprint_wrappers=1 "${WORK}/smoke.mp4" | \
  grep -Eq 'codec_name=h264'
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name \
  -of default=noprint_wrappers=1 "${WORK}/smoke.mp4" | \
  grep -Eq 'codec_name=aac'
