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
  skill_version: "smoke-v1",
  fps: 30,
  width: 1920,
  height: 1080,
  duration_in_frames: durationInFrames,
  selected_capability_ids: [
    "video.renderer.master",
    "video.component.core.primitives",
    "video.component.animated-bar-chart",
    "font.inter",
  ],
  beats: [
    {
      id: "smoke-beat",
      utterance_id: "smoke-utterance",
      start_frame: 0,
      duration_in_frames: durationInFrames,
      background: "#020617",
      layers: [
        {
          id: "smoke-title",
          type: "text",
          from: 0,
          duration_in_frames: durationInFrames,
          x: 240,
          y: 100,
          width: 1440,
          height: 300,
          opacity: 1,
          rotation: 0,
          scale: 1,
          z_index: 1,
          keyframes: [],
          text: "Static capability renderer",
          color: "#f8fafc",
          font_id: "font.inter",
          font_size: 96,
          font_weight: 600,
          align: "center",
        },
        {
          id: "smoke-chart",
          type: "component",
          capability_id: "video.component.animated-bar-chart",
          from: 0,
          duration_in_frames: durationInFrames,
          x: 360,
          y: 420,
          width: 1200,
          height: 500,
          opacity: 1,
          rotation: 0,
          scale: 1,
          z_index: 1,
          keyframes: [],
          props: {
            data: [35, 60, 45, 80],
            labels: ["Q1", "Q2", "Q3", "Q4"],
          },
        },
      ],
    },
  ],
  transitions: [],
  audio_tracks: [
    {
      utterance_id: "smoke-utterance",
      src: "silence.wav",
      start_frame: 0,
      duration_in_frames: durationInFrames,
      volume: 1,
    },
  ],
  captions: [],
  watermark: true,
  seed: "smoke",
};
await writeFile(target, `${JSON.stringify(input, null, 2)}\n`, "utf8");
