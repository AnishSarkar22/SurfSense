import type React from "react";
import {Easing, interpolate, useCurrentFrame, useVideoConfig} from "remotion";

export type FocusBlurResolveProps = {
  text: string;
  blur?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  speed?: number;
};

// Adapted from https://remocn.dev/r/focus-blur-resolve.json (MIT).
export const FocusBlurResolve: React.FC<FocusBlurResolveProps> = ({
  text,
  blur = 14,
  fontSize = 72,
  color = "#171717",
  fontWeight = 600,
  speed = 1,
}) => {
  const frame = useCurrentFrame() * speed;
  const {durationInFrames} = useVideoConfig();
  const enterDuration = 23;
  const exitStart = Math.max(enterDuration, durationInFrames - 16);
  const enterEasing = Easing.bezier(0.22, 1, 0.36, 1);
  const exitEasing = Easing.bezier(0.64, 0, 0.78, 0);
  const enter = interpolate(frame, [0, enterDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: enterEasing,
  });
  const exit = interpolate(frame, [exitStart, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: exitEasing,
  });

  return (
    <div style={{position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center"}}>
      <span
        style={{
          color,
          display: "inline-block",
          filter: `blur(${interpolate(enter, [0, 1], [blur, 0]) + interpolate(exit, [0, 1], [0, 10])}px)`,
          fontFamily: "Inter, sans-serif",
          fontSize,
          fontWeight,
          letterSpacing: "-0.03em",
          opacity: enter * (1 - exit),
          scale: `${interpolate(enter, [0, 1], [1.01, 1])}`,
          translate: `0 ${interpolate(enter, [0, 1], [14, 0]) + interpolate(exit, [0, 1], [0, -10])}px`,
        }}
      >
        {text}
      </span>
    </div>
  );
};
