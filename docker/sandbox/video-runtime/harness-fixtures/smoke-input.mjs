import {readFile, writeFile} from "node:fs/promises";
import path from "node:path";

const {build_id: registryBuildId} = JSON.parse(
  await readFile(
    process.env.SURFSENSE_CAPABILITY_INDEX ??
      new URL("../generated/capabilities/index.json", import.meta.url),
    "utf8",
  ),
);
const target = path.resolve(
  process.argv[2] ?? "harness-fixtures/smoke-input.json",
);
const durationSeconds = Number(process.argv[3] ?? 1);
if (![1, 30, 60, 180].includes(durationSeconds)) {
  throw new Error("Fixture duration must be one of: 1, 30, 60, 180 seconds");
}
const durationInFrames = durationSeconds * 30;
const input = {
  schema_version: 1,
  build_id: registryBuildId,
  fps: 30,
  max_duration_seconds: durationSeconds + 30,
  width: 1920,
  height: 1080,
  duration_in_frames: durationInFrames,
  selected_capability_ids: [
    "video.renderer.master",
    "video.component.animated-bar-chart",
    "font.inter",
  ],
  narration_cues: [
    {
      cue_id: "smoke-cue-1",
      start_frame: 0,
      duration_in_frames: Math.max(1, Math.floor(durationInFrames / 2)),
    },
    {
      cue_id: "smoke-cue-2",
      start_frame: Math.floor(durationInFrames / 2),
      duration_in_frames: Math.ceil(durationInFrames / 2),
    },
  ],
  audio_tracks: [
    {
      cue_id: "smoke-cue-1",
      src: "silence.wav",
      start_frame: 0,
      duration_in_frames: Math.max(1, Math.floor(durationInFrames / 2)),
      volume: 1,
    },
    {
      cue_id: "smoke-cue-2",
      src: "silence.wav",
      start_frame: Math.floor(durationInFrames / 2),
      duration_in_frames: Math.ceil(durationInFrames / 2),
      volume: 1,
    },
  ],
  assets: [{id: "silence", path: "silence.wav", kind: "audio"}],
  sample_frames: [
    {frame: 0, reason: "first-content"},
    {frame: Math.floor((durationInFrames - 1) / 2), reason: "even:middle"},
    {frame: durationInFrames - 1, reason: "last-content"},
  ],
  watermark: true,
  seed: "smoke",
};
await writeFile(target, `${JSON.stringify(input, null, 2)}\n`, "utf8");
