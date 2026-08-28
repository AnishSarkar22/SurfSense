#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT

cd "${ROOT}"
CAPABILITY_INDEX="${SURFSENSE_CAPABILITY_INDEX:-${ROOT}/generated/capabilities/index.json}"
if [[ ! -f "${ROOT}/generated/VideoRenderInput.mjs" || ! -f "${CAPABILITY_INDEX}" ]]; then
  npm run generate
fi
node harness-fixtures/smoke-input.mjs "${WORK}/input.json"
mkdir -p "${WORK}/public"
DURATION_SECONDS="$(
  node -e 'const i=require(process.argv[1]); console.log(i.duration_in_frames / i.fps)' \
    "${WORK}/input.json"
)"
node harness-fixtures/write-silence.mjs \
  "${WORK}/public/silence.wav" "${DURATION_SECONDS}"
node scripts/bundle-job.mjs \
  --source-dir "${ROOT}/harness-fixtures/job-source" \
  --out-dir "${WORK}/job"
node scripts/finalize-job.mjs \
  --job-dir "${WORK}/job" \
  --public-dir "${WORK}/public"
node render.mjs --job-dir "${WORK}/job" "${WORK}/input.json" "${WORK}/smoke.mp4"

test -s "${WORK}/smoke.mp4"
test -s "${WORK}/smoke.mp4.render.json"
test -s "${WORK}/job/job.json"
node -e '
  const fs = require("node:fs");
  const job = JSON.parse(fs.readFileSync(process.argv[1]));
  const receipt = JSON.parse(fs.readFileSync(process.argv[2]));
  if (job.source_sha256 !== receipt.source_sha256 || job.bundle_sha256 !== receipt.bundle_sha256) {
    throw new Error("Render receipt hashes do not match the prepared job");
  }
' "${WORK}/job/job.json" "${WORK}/smoke.mp4.render.json"
test ! -e "${ROOT}/src/scenes"
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height \
  -of default=noprint_wrappers=1 "${WORK}/smoke.mp4" | \
  grep -Eq 'codec_name=h264'
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name \
  -of default=noprint_wrappers=1 "${WORK}/smoke.mp4" | \
  grep -Eq 'codec_name=aac'
