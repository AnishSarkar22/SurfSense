import {staticFile, useCurrentFrame} from "remotion";
import type * as Contract from "./authoring-contract";
import type {NarrationCueTiming} from "./authoring-contract";
import {useTrustedVideoRuntime} from "./authoring-context";
import type {NarrationCue} from "./schemas/VideoRenderInput";

const toTiming = (cue: NarrationCue): NarrationCueTiming => ({
  cueId: cue.cue_id,
  startFrame: cue.start_frame,
  durationInFrames: cue.duration_in_frames,
  endFrame: cue.start_frame + cue.duration_in_frames,
});

export const useNarrationCue: typeof Contract.useNarrationCue = (cueId) => {
  const frame = useCurrentFrame();
  const {narration_cues: cues} = useTrustedVideoRuntime();
  const cue = cueId
    ? cues.find(({cue_id: id}) => id === cueId)
    : cues.find(
        ({start_frame: start, duration_in_frames: duration}) =>
          frame >= start && frame < start + duration,
      );
  if (!cue) return null;
  const localFrame = frame - cue.start_frame;
  return {
    ...toTiming(cue),
    active: localFrame >= 0 && localFrame < cue.duration_in_frames,
    localFrame,
    progress: Math.max(0, Math.min(1, localFrame / cue.duration_in_frames)),
  };
};

export const useNarrationCues: typeof Contract.useNarrationCues = () =>
  useTrustedVideoRuntime().narration_cues.map(toTiming);

export const useAsset: typeof Contract.useAsset = (assetId) => {
  const {assets} = useTrustedVideoRuntime();
  const asset = assets.find(({id}) => id === assetId);
  if (!asset) throw new Error(`Unknown video asset: ${assetId}`);
  return {id: asset.id, kind: asset.kind, src: staticFile(asset.path)};
};

const hashUnit = (value: string): number => {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 4294967296;
};

export const useSeededRandom: typeof Contract.useSeededRandom = (key, frame) => {
  const currentFrame = useCurrentFrame();
  const {seed} = useTrustedVideoRuntime();
  return hashUnit(`${seed}:${key}:${frame ?? currentFrame}`);
};

export type {
  NarrationCueState,
  NarrationCueTiming,
  VideoAsset,
} from "./authoring-contract";
