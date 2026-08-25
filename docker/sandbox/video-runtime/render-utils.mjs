import {createHash} from "node:crypto";
import {mkdir, rename, stat, writeFile} from "node:fs/promises";
import path from "node:path";

export function assertDurationLimit(composition, maxDurationSeconds = 180) {
  const durationSeconds = composition.durationInFrames / composition.fps;
  if (durationSeconds > maxDurationSeconds) {
    const error = new Error(
      `Composition duration ${durationSeconds.toFixed(3)}s exceeds ${maxDurationSeconds}s`,
    );
    error.code = "duration_limit";
    throw error;
  }
  return durationSeconds;
}

export function inputHash(source) {
  return createHash("sha256").update(source).digest("hex");
}

export async function atomicWriteJson(filePath, value) {
  await mkdir(path.dirname(filePath), {recursive: true});
  const temporaryPath = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  await writeFile(temporaryPath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  await rename(temporaryPath, filePath);
}

export async function assertBundleAssets(input, bundleDir) {
  const publicDir = path.resolve(bundleDir, "public");
  const sources = [
    ...input.audio_tracks.map(({src}) => src),
    ...input.beats.flatMap(({layers}) =>
      layers
        .filter(({type}) => type === "image" || type === "video")
        .map(({src}) => src),
    ),
  ];
  for (const source of new Set(sources)) {
    const target = path.resolve(publicDir, source);
    if (
      path.isAbsolute(source) ||
      (target !== publicDir && !target.startsWith(`${publicDir}${path.sep}`))
    ) {
      const error = new Error(`Asset path escapes the job bundle: ${source}`);
      error.code = "asset_path_escape";
      throw error;
    }
    try {
      const metadata = await stat(target);
      if (!metadata.isFile()) throw new Error("not a file");
    } catch {
      const error = new Error(`Job bundle asset does not exist: ${source}`);
      error.code = "missing_bundle_asset";
      throw error;
    }
  }
}

const clampFrame = (frame, totalFrames) =>
  Math.max(0, Math.min(totalFrames - 1, Math.round(frame)));

export function riskFrames(input, limit = 36) {
  const totalFrames = input.duration_in_frames;
  const samples = new Map([
    [0, "first-content"],
    [totalFrames - 1, "last-content"],
  ]);
  for (const beat of input.beats) {
    samples.set(
      clampFrame(beat.start_frame + (beat.duration_in_frames - 1) / 2, totalFrames),
      `beat:${beat.id}:midpoint`,
    );
    for (const layer of beat.layers) {
      for (const keyframe of layer.keyframes ?? []) {
        samples.set(
          clampFrame(beat.start_frame + layer.from + keyframe.frame, totalFrames),
          `beat:${beat.id}:keyframe`,
        );
      }
    }
  }
  for (const transition of input.transitions) {
    samples.set(clampFrame(transition.start_frame, totalFrames), "transition:start");
    samples.set(
      clampFrame(
        transition.start_frame + transition.duration_in_frames / 2,
        totalFrames,
      ),
      "transition:midpoint",
    );
    samples.set(
      clampFrame(
        transition.start_frame + transition.duration_in_frames - 1,
        totalFrames,
      ),
      "transition:end",
    );
  }
  return [...samples.entries()]
    .sort(([left], [right]) => left - right)
    .slice(0, limit)
    .map(([frame, reason]) => ({frame, reason}));
}

export function resolvedCapabilityIds(input, trustedIds) {
  const selected = new Set(input.selected_capability_ids);
  const used = new Set(["video.renderer.master"]);
  for (const id of selected) {
    if (id.startsWith("font.")) used.add(id);
  }
  for (const beat of input.beats) {
    for (const layer of beat.layers) {
      if (layer.capability_id) used.add(layer.capability_id);
      else used.add("video.component.core.primitives");
      if (layer.font_id) used.add(layer.font_id);
    }
  }
  for (const transition of input.transitions) used.add(transition.capability_id);
  return [...used]
    .filter((id) => selected.has(id) && trustedIds.has(id))
    .sort();
}
