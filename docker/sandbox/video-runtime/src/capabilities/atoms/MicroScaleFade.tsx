import type React from "react";
import {Easing, interpolate, useCurrentFrame} from "remotion";

export type MicroScaleFadeProps = {
  text: string;
  scaleFrom?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  speed?: number;
};

// Adapted from https://remocn.dev/r/micro-scale-fade.json (MIT).
export const MicroScaleFade: React.FC<MicroScaleFadeProps> = ({
  text,
  scaleFrom = 0.96,
  fontSize = 72,
  color = "#171717",
  fontWeight = 600,
  speed = 1,
}) => {
  const frame = useCurrentFrame() * speed;
  const easing = Easing.bezier(0.32, 0.72, 0, 1);
  const opacity = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing,
  });
  const scale = interpolate(frame, [0, 18], [scaleFrom, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing,
  });

  return (
    <div style={{position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center"}}>
      <span
        style={{
          display: "inline-block",
          color,
          fontFamily: "Inter, sans-serif",
          fontSize,
          fontWeight,
          letterSpacing: "-0.03em",
          opacity,
          scale: `${scale}`,
          transformOrigin: "50% 50%",
        }}
      >
        {text}
      </span>
    </div>
  );
};
