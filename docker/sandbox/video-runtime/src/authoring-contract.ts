import type React from "react";

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

export type TimelineLayerProps = {
  id: string;
  from: number;
  durationInFrames: number;
  children: React.ReactNode;
};

type LockedTextStyle =
  | "fontFamily"
  | "fontSize"
  | "fontWeight"
  | "letterSpacing"
  | "lineHeight"
  | "maxWidth"
  | "overflow"
  | "whiteSpace"
  | "width";

export type FittedTextProps = {
  id: string;
  children: string;
  maxWidth: number;
  maxLines?: number;
  maxFontSize?: number;
  fontFamily?: "Inter" | "Lora" | "JetBrains Mono";
  fontWeight?: number | string;
  letterSpacing?: string;
  lineHeight?: number;
  style?: Omit<React.CSSProperties, LockedTextStyle>;
};

type LockedStackStyle =
  | "alignItems"
  | "display"
  | "flexDirection"
  | "gap"
  | "justifyContent"
  | "minHeight"
  | "minWidth";

export type SpatialStackProps = {
  children: React.ReactNode;
  direction?: "row" | "column";
  gap?: number;
  align?: React.CSSProperties["alignItems"];
  justify?: React.CSSProperties["justifyContent"];
  style?: Omit<React.CSSProperties, LockedStackStyle>;
};

type LockedGridStyle =
  | "alignItems"
  | "display"
  | "gap"
  | "gridTemplateColumns"
  | "minHeight"
  | "minWidth";

export type SpatialGridProps = {
  children: React.ReactNode;
  /** Minimum item width in pixels; columns wrap to fit the available region. */
  minItemWidth?: number;
  gap?: number;
  align?: React.CSSProperties["alignItems"];
  style?: Omit<React.CSSProperties, LockedGridStyle>;
};

export declare const TimelineLayer: React.FC<TimelineLayerProps>;
export declare const FittedText: React.FC<FittedTextProps>;
export declare const SpatialStack: React.FC<SpatialStackProps>;
export declare const SpatialGrid: React.FC<SpatialGridProps>;
export declare const useNarrationCue: (
  cueId?: string,
) => NarrationCueState | null;
export declare const useNarrationCues: () => readonly NarrationCueTiming[];
export declare const useAsset: (assetId: string) => VideoAsset;
export declare const useSeededRandom: (key: string, frame?: number) => number;
