import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import {
  assertDurationLimit,
  neutralSampleFrames,
  resolvedCapabilityIds,
} from "../render-utils.mjs";

const {VideoRenderInputSchema} = await import("../generated/VideoRenderInput.mjs");
const root = path.resolve(import.meta.dirname, "..");
const index = JSON.parse(
  await readFile(
    process.env.SURFSENSE_CAPABILITY_INDEX ??
      path.join(root, "generated/capabilities/index.json"),
    "utf8",
  ),
);
const trustedIds = new Set(index.capabilities.map(({id}) => id));
const hostSource = await readFile(path.join(root, "src/TrustedVideoHost.tsx"), "utf8");
const publicSource = await readFile(
  path.join(root, "src/generated/public-capabilities.ts"),
  "utf8",
);
const authoringSource = await readFile(path.join(root, "src/authoring.tsx"), "utf8");
const contractSource = await readFile(
  path.join(root, "src/authoring-contract.ts"),
  "utf8",
);
const contextSource = await readFile(
  path.join(root, "src/authoring-context.tsx"),
  "utf8",
);
const registrySource = await readFile(
  path.join(root, "src/generated/capability-registry.ts"),
  "utf8",
);
const renderSource = await readFile(path.join(root, "render.mjs"), "utf8");

const validInput = {
  schema_version: 1,
  build_id: index.build_id,
  fps: 30,
  max_duration_seconds: 210,
  width: 1920,
  height: 1080,
  duration_in_frames: 90,
  selected_capability_ids: [
    "video.renderer.master",
    "font.inter",
    "video.component.animated-bar-chart",
  ],
  narration_cues: [
    {cue_id: "cue-1", start_frame: 0, duration_in_frames: 45},
    {cue_id: "cue-2", start_frame: 45, duration_in_frames: 45},
  ],
  audio_tracks: [
    {
      cue_id: "cue-1",
      src: "silence.wav",
      start_frame: 0,
      duration_in_frames: 45,
      volume: 1,
    },
    {
      cue_id: "cue-2",
      src: "silence.wav",
      start_frame: 45,
      duration_in_frames: 45,
      volume: 1,
    },
  ],
  assets: [{id: "silence", path: "silence.wav", kind: "audio"}],
  sample_frames: [
    {frame: 0, reason: "first-content"},
    {frame: 44, reason: "cue:cue-1:end"},
    {frame: 45, reason: "cue:cue-2:start"},
    {frame: 89, reason: "last-content"},
  ],
  watermark: true,
  seed: "fixture",
};

test("sole runtime input accepts cue-based trusted props", () => {
  const result = VideoRenderInputSchema.safeParse(validInput);
  assert.equal(result.success, true, JSON.stringify(result.error?.issues));
  for (const removed of ["beats", "transitions", "captions"]) {
    assert.equal(
      VideoRenderInputSchema.safeParse({...validInput, [removed]: []}).success,
      false,
    );
  }
});

test("cue, audio, asset, sample, and duration bounds are enforced", () => {
  const hardLimitInput = {
    ...validInput,
    duration_in_frames: 6300,
    narration_cues: [{cue_id: "cue-1", start_frame: 0, duration_in_frames: 6300}],
    audio_tracks: [
      {...validInput.audio_tracks[0], duration_in_frames: 6300},
    ],
  };
  assert.equal(
    VideoRenderInputSchema.safeParse(hardLimitInput).success,
    true,
  );
  assert.equal(
    VideoRenderInputSchema.safeParse({
      ...hardLimitInput,
      duration_in_frames: 6301,
      narration_cues: [{cue_id: "cue-1", start_frame: 0, duration_in_frames: 6301}],
      audio_tracks: [
        {...validInput.audio_tracks[0], duration_in_frames: 6301},
      ],
    }).success,
    false,
  );
  assert.equal(
    VideoRenderInputSchema.safeParse({
      ...validInput,
      audio_tracks: [{...validInput.audio_tracks[0], cue_id: "missing"}],
    }).success,
    false,
  );
  assert.equal(
    VideoRenderInputSchema.safeParse({
      ...validInput,
      sample_frames: [{frame: 0, reason: "first"}, {frame: 90, reason: "outside"}],
    }).success,
    false,
  );
  assert.equal(assertDurationLimit({durationInFrames: 6300, fps: 30}, 210), 210);
});

test("neutral samples and imported capability provenance are deterministic", () => {
  assert.deepEqual(neutralSampleFrames(validInput), validInput.sample_frames);
  assert.deepEqual(
    resolvedCapabilityIds(
      validInput,
      trustedIds,
      ["video.component.animated-bar-chart"],
    ),
    [
      "font.inter",
      "video.component.animated-bar-chart",
      "video.renderer.master",
    ],
  );
});

test("public authoring and capability APIs expose only the supported surface", () => {
  for (const exported of [
    "NarrationCueTiming",
    "NarrationCueState",
    "VideoAsset",
  ]) {
    assert.match(contractSource, new RegExp(`export type ${exported}\\b`));
  }
  for (const hook of [
    "useNarrationCue",
    "useNarrationCues",
    "useAsset",
    "useSeededRandom",
  ]) {
    assert.match(contractSource, new RegExp(`export declare const ${hook}\\b`));
    assert.match(authoringSource, new RegExp(`export const ${hook}\\b`));
  }
  assert.doesNotMatch(contractSource, /\b(?:cue_id|start_frame|duration_in_frames)\b/);
  assert.doesNotMatch(
    authoringSource,
    /export (?:const|type) (?:VideoRuntimeProvider|useVideoRuntime|VideoRenderInput|NarrationCue)\b/,
  );
  assert.match(contextSource, /export const VideoRuntimeProvider/);
  assert.match(publicSource, /AnimatedBarChart/);
  assert.match(publicSource, /BlurOutUp/);
  assert.match(publicSource, /whipPan as WhipPan/);
  assert.doesNotMatch(publicSource, /capabilityBuildId|capabilityIds/);
  assert.doesNotMatch(
    registrySource,
    /componentLoaders|transitionRenderers|fontFamilies|nativeCanvasById/,
  );
  assert.match(hostSource, /export const TrustedVideoHost/);
  assert.match(hostSource, /<JobComposition \/>/);
  assert.match(hostSource, /<VideoRuntimeProvider value=\{input\}>/);
  assert.match(hostSource, /<Audio src=\{staticFile\(track\.src\)\}/);
  assert.doesNotMatch(hostSource, /\bbeats\b|\btransitions\b|\bcaptions\b/);
});

test("render consumes one prepared bundle and emits provenance receipt", () => {
  assert.equal((renderSource.match(/\brenderMedia\(/g) ?? []).length, 1);
  assert.doesNotMatch(renderSource, /@remotion\/bundler|\bbundle\(/);
  for (const field of [
    "source_sha256",
    "bundle_sha256",
    "runtime_build_id",
    "capability_build_id",
    "imported_capability_ids",
    "sample_frames",
    "expected_frame_count",
    "render_settings",
  ]) {
    assert.match(renderSource, new RegExp(`\\b${field}\\b`));
  }
  assert.match(renderSource, /--job-dir/);
  assert.doesNotMatch(renderSource, /beat_sample_frames|--bundle-dir/);
});
