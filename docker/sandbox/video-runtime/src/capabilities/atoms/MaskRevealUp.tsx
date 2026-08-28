import type React from "react";
import {Easing, interpolate, useCurrentFrame, useVideoConfig} from "remotion";

export type MaskRevealUpProps = {
  text: string;
  distance?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  speed?: number;
};

// Adapted from https://remocn.dev/r/mask-reveal-up.json (MIT).
export const MaskRevealUp: React.FC<MaskRevealUpProps> = ({
  text,
  distance = 30,
  fontSize = 72,
  color = "#171717",
  fontWeight = 600,
  speed = 1,
}) => {
  const frame = useCurrentFrame() * speed;
  const {durationInFrames} = useVideoConfig();
  const lines = text.split("\n");
  const enterDuration = 23;
  const exitDuration = 16;
  const exitStart = Math.max(
    enterDuration + (lines.length - 1) * 3,
    durationInFrames - exitDuration - (lines.length - 1) * 2,
  );

  return (
    <div style={{position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center"}}>
      <span style={{color, fontFamily: "Inter, sans-serif", fontSize, fontWeight, letterSpacing: "-0.03em", lineHeight: 1.1, textAlign: "center"}}>
        {lines.map((line, index) => {
          const enterFrame = frame - index * 3;
          const exitFrame = frame - exitStart - index * 2;
          const enter = interpolate(enterFrame, [0, enterDuration], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.22, 1, 0.36, 1),
          });
          const exit = interpolate(exitFrame, [0, exitDuration], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.64, 0, 0.78, 0),
          });
          return (
            <span
              key={lines.slice(0, index + 1).join("\n")}
              style={{
                display: "block",
                filter: `blur(${interpolate(enter, [0, 1], [6, 0]) + interpolate(exit, [0, 1], [0, 6])}px)`,
                opacity: enter * (1 - exit),
                translate: `0 ${interpolate(enterFrame, [0, 11], [distance, 0], {extrapolateLeft: "clamp", extrapolateRight: "clamp"}) + interpolate(exitFrame, [8, exitDuration], [0, -22], {extrapolateLeft: "clamp", extrapolateRight: "clamp"})}px`,
              }}
            >
              {line}
            </span>
          );
        })}
      </span>
    </div>
  );
};
