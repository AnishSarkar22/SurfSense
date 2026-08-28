import type React from "react";
import {interpolate, useCurrentFrame} from "remotion";

export type StaggeredFadeUpProps = {
  text: string;
  staggerDelay?: number;
  distance?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  speed?: number;
};

// Adapted from https://remocn.dev/r/staggered-fade-up.json (MIT).
export const StaggeredFadeUp: React.FC<StaggeredFadeUpProps> = ({
  text,
  staggerDelay = 4,
  distance = 20,
  fontSize = 72,
  color = "#171717",
  fontWeight = 600,
  speed = 1,
}) => {
  const frame = useCurrentFrame() * speed;
  const words = text.split(" ");

  return (
    <div style={{position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center"}}>
      <span style={{color, fontFamily: "Inter, sans-serif", fontSize, fontWeight, letterSpacing: "-0.03em"}}>
        {words.map((word, index) => {
          const localFrame = frame - index * staggerDelay;
          return (
            <span
              key={words.slice(0, index + 1).join(" ")}
              style={{
                display: "inline-block",
                marginRight: "0.25em",
                opacity: interpolate(localFrame, [0, 12], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
                translate: `0 ${interpolate(localFrame, [0, 12], [distance, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                })}px`,
              }}
            >
              {word}
            </span>
          );
        })}
      </span>
    </div>
  );
};
