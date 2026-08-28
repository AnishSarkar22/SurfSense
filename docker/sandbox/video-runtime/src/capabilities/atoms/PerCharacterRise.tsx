import type React from "react";
import {Easing, interpolate, useCurrentFrame} from "remotion";

export type PerCharacterRiseProps = {
  text: string;
  distance?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  speed?: number;
};

// Adapted from https://remocn.dev/r/per-character-rise.json (MIT).
export const PerCharacterRise: React.FC<PerCharacterRiseProps> = ({
  text,
  distance = 32,
  fontSize = 72,
  color = "#171717",
  fontWeight = 600,
  speed = 1,
}) => {
  const frame = useCurrentFrame() * speed;
  const characters = Array.from(text);

  return (
    <div style={{position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center"}}>
      <span style={{color, fontFamily: "Inter, sans-serif", fontSize, fontWeight, letterSpacing: "-0.05em"}}>
        {characters.map((character, index) => {
          const localFrame = frame - index;
          return (
            <span
              key={characters.slice(0, index + 1).join("")}
              style={{
                display: "inline-block",
                opacity: interpolate(localFrame, [0, 21], [0, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.bezier(0.2, 0.8, 0.2, 1),
                }),
                translate: `0 ${interpolate(localFrame, [0, 10], [distance, 0], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                  easing: Easing.bezier(0.2, 0.8, 0.6, 0.85),
                })}px`,
                whiteSpace: "pre",
              }}
            >
              {character}
            </span>
          );
        })}
      </span>
    </div>
  );
};
