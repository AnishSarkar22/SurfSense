import type React from "react";
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from "remotion";

export type DriftProps = {
  children?: React.ReactNode;
  grow?: number;
};

// Adapted from https://remocn.dev/r/drift.json (MIT).
export const Drift: React.FC<DriftProps> = ({children, grow = 0.035}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const scale = interpolate(frame, [0, durationInFrames], [1, 1 + grow]);

  return <AbsoluteFill style={{transform: `scale(${scale})`}}>{children}</AbsoluteFill>;
};
