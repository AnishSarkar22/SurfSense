import type React from "react";
import {Easing, interpolate, useCurrentFrame, useVideoConfig} from "remotion";

export type BlurOutUpProps = {
  text: string;
  staggerDelay?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  speed?: number;
};

// Adapted from https://remocn.dev/r/blur-out-up.json (MIT).
export const BlurOutUp: React.FC<BlurOutUpProps> = ({
  text,
  staggerDelay = 1,
  fontSize = 72,
  color = "#171717",
  fontWeight = 600,
  speed = 1,
}) => {
  const frame = useCurrentFrame() * speed;
  const {durationInFrames} = useVideoConfig();
  const words = text.split(/\s+/);
  const enterDuration = 17;
  const exitDuration = 14;
  const enterEnd = enterDuration + (words.length - 1) * staggerDelay;
  const exitStart = Math.max(
    enterEnd,
    durationInFrames - exitDuration - (words.length - 1) * staggerDelay,
  );

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Inter, sans-serif",
        fontSize,
        fontWeight,
        color,
      }}
    >
      {words.map((word, index) => {
        const enterFrame = frame - index * staggerDelay;
        const exitFrame = frame - exitStart - index * staggerDelay;
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
            key={`${word}-${index}`}
            style={{
              display: "inline-block",
              marginRight: "0.25em",
              opacity: enter * (1 - exit),
              translate: `0 ${interpolate(enter, [0, 1], [10, 0]) + interpolate(exit, [0, 1], [0, -14])}px`,
              filter: `blur(${interpolate(enter, [0, 1], [6, 0]) + interpolate(exit, [0, 1], [0, 8])}px)`,
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};
