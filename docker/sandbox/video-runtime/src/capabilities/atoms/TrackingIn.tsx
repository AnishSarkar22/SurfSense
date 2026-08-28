import type React from "react";
import {interpolate, spring, useCurrentFrame, useVideoConfig} from "remotion";

export type TrackingInProps = {
  text: string;
  startTracking?: number;
  startBlur?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  speed?: number;
};

// Adapted from https://remocn.dev/r/tracking-in.json (MIT).
export const TrackingIn: React.FC<TrackingInProps> = ({
  text,
  startTracking = 0.5,
  startBlur = 12,
  fontSize = 96,
  color = "#171717",
  fontWeight = 700,
  speed = 1,
}) => {
  const frame = useCurrentFrame() * speed;
  const {fps} = useVideoConfig();
  const progress = spring({
    frame,
    fps,
    config: {damping: 18, stiffness: 90},
  });

  return (
    <div style={{position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center"}}>
      <span
        style={{
          color,
          filter: `blur(${interpolate(progress, [0, 1], [startBlur, 0])}px)`,
          fontFamily: "Inter, sans-serif",
          fontSize,
          fontWeight,
          letterSpacing: `${interpolate(progress, [0, 1], [startTracking, -0.03])}em`,
          opacity: interpolate(frame, [0, 15], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          whiteSpace: "nowrap",
        }}
      >
        {text}
      </span>
    </div>
  );
};
