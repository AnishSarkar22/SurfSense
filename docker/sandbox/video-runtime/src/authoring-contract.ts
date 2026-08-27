export type NarrationCueTiming = {
  cueId: string;
  startFrame: number;
  durationInFrames: number;
  /** The first frame after this cue. */
  endFrame: number;
};

export type NarrationCueState = NarrationCueTiming & {
  active: boolean;
  localFrame: number;
  /** Cue progress clamped to the inclusive range 0–1. */
  progress: number;
};

export type VideoAsset = {
  id: string;
  kind: "image" | "video" | "audio" | "svg";
  src: string;
};

export declare const useNarrationCue: (
  cueId?: string,
) => NarrationCueState | null;
export declare const useNarrationCues: () => readonly NarrationCueTiming[];
export declare const useAsset: (assetId: string) => VideoAsset;
export declare const useSeededRandom: (key: string, frame?: number) => number;
