import type React from "react";
import {Easing, interpolate, useCurrentFrame, useVideoConfig} from "remotion";

export type ScaleDownFadeProps = {
  text: string;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  speed?: number;
};

// Adapted from https://remocn.dev/r/scale-down-fade.json (MIT).
export const ScaleDownFade: React.FC<ScaleDownFadeProps> = ({
  text,
  fontSize = 72,
  color = "#171717",
  fontWeight = 600,
  speed = 1,
}) => {
  const frame = useCurrentFrame() * speed;
  const {durationInFrames} = useVideoConfig();
  const enterDuration = 16;
  const exitStart = Math.max(enterDuration, durationInFrames - 11);
  const enter = interpolate(frame, [0, enterDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.22, 1, 0.36, 1),
  });
  const exit = interpolate(frame, [exitStart, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.64, 0, 0.78, 0),
  });

  return (
    <div style={{position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center"}}>
      <span
        style={{
          color,
          display: "inline-block",
          fontFamily: "Inter, sans-serif",
          fontSize,
          fontWeight,
          letterSpacing: "-0.03em",
          opacity: enter * (1 - exit),
          scale: `${interpolate(enter, [0, 1], [1.04, 1]) - exit * 0.06}`,
          translate: `0 ${interpolate(enter, [0, 1], [8, 0]) - exit * 8}px`,
        }}
      >
        {text}
      </span>
    </div>
  );
};
