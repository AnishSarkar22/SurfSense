import {createContext, useContext} from "react";
import {staticFile, useCurrentFrame} from "remotion";
import type {
  NarrationCue,
  VideoAsset,
  VideoRenderInput,
} from "./schemas/VideoRenderInput";

const VideoRuntimeContext = createContext<VideoRenderInput | null>(null);

export const VideoRuntimeProvider = VideoRuntimeContext.Provider;

export const useVideoRuntime = (): VideoRenderInput => {
  const input = useContext(VideoRuntimeContext);
  if (!input) {
    throw new Error("SurfSense video helpers must be used inside TrustedVideoHost");
  }
  return input;
};

export type NarrationCueState = NarrationCue & {
  active: boolean;
  localFrame: number;
  progress: number;
};

export const useNarrationCue = (cueId?: string): NarrationCueState | null => {
  const frame = useCurrentFrame();
  const {narration_cues: cues} = useVideoRuntime();
  const cue = cueId
    ? cues.find(({cue_id: id}) => id === cueId)
    : cues.find(
        ({start_frame: start, duration_in_frames: duration}) =>
          frame >= start && frame < start + duration,
      );
  if (!cue) return null;
  const localFrame = frame - cue.start_frame;
  return {
    ...cue,
    active: localFrame >= 0 && localFrame < cue.duration_in_frames,
    localFrame,
    progress: Math.max(0, Math.min(1, localFrame / cue.duration_in_frames)),
  };
};

export const useNarrationCues = (): readonly NarrationCue[] =>
  useVideoRuntime().narration_cues;

export const useAsset = (assetId: string): VideoAsset & {src: string} => {
  const {assets} = useVideoRuntime();
  const asset = assets.find(({id}) => id === assetId);
  if (!asset) throw new Error(`Unknown video asset: ${assetId}`);
  return {...asset, src: staticFile(asset.path)};
};

const hashUnit = (value: string): number => {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) / 4294967296;
};

export const useSeededRandom = (key: string, frame?: number): number => {
  const currentFrame = useCurrentFrame();
  const {seed} = useVideoRuntime();
  return hashUnit(`${seed}:${key}:${frame ?? currentFrame}`);
};

export type {NarrationCue, VideoAsset, VideoRenderInput};
