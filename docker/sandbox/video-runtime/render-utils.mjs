import {createHash} from "node:crypto";
import {mkdir, readFile, readdir, rename, stat, writeFile} from "node:fs/promises";
import path from "node:path";

export function assertDurationLimit(composition, maxDurationSeconds) {
  if (!Number.isInteger(maxDurationSeconds) || maxDurationSeconds < 1) {
    throw new Error("maxDurationSeconds must be a positive integer");
  }
  const durationSeconds = composition.durationInFrames / composition.fps;
  if (durationSeconds > maxDurationSeconds) {
    const error = new Error(
      `Composition duration ${durationSeconds.toFixed(3)}s exceeds duration limit of ${maxDurationSeconds}s`,
    );
    error.code = "duration_limit";
    throw error;
  }
  return durationSeconds;
}

export function inputHash(source) {
  return createHash("sha256").update(source).digest("hex");
}

export async function directoryHash(directory) {
  const root = path.resolve(directory);
  const hash = createHash("sha256");
  const visit = async (current) => {
    const entries = await readdir(current, {withFileTypes: true});
    for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
      const target = path.join(current, entry.name);
      if (entry.isDirectory()) {
        await visit(target);
      } else if (entry.isFile()) {
        hash.update(path.relative(root, target).replaceAll(path.sep, "/"));
        hash.update("\0");
        hash.update(await readFile(target));
        hash.update("\0");
      } else {
        throw new Error(`Prepared bundle contains unsupported entry: ${target}`);
      }
    }
  };
  await visit(root);
  return hash.digest("hex");
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
    ...input.assets.map(({path: assetPath}) => assetPath),
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

export function neutralSampleFrames(input, limit = 36) {
  const totalFrames = input.duration_in_frames;
  const samples = new Map();
  for (const sample of input.sample_frames) {
    samples.set(clampFrame(sample.frame, totalFrames), sample.reason);
  }
  return [...samples.entries()]
    .sort(([left], [right]) => left - right)
    .slice(0, limit)
    .map(([frame, reason]) => ({frame, reason}));
}

export function resolvedCapabilityIds(input, trustedIds, importedCapabilityIds = []) {
  const selected = new Set(input.selected_capability_ids);
  const used = new Set(["video.renderer.master", ...importedCapabilityIds]);
  for (const id of selected) {
    if (id.startsWith("font.")) used.add(id);
  }
  return [...used]
    .filter((id) => selected.has(id) && trustedIds.has(id))
    .sort();
}
