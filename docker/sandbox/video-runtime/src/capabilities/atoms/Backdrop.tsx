import type React from "react";
import {AbsoluteFill, useVideoConfig} from "remotion";

export type BackdropFill =
  | {type: "color"; value: string}
  | {type: "gradient"; value: string};

export type BackdropProps = {
  fill?: BackdropFill;
  padding?: number;
  radius?: number;
  shadow?: string;
  children?: React.ReactNode;
};

// Adapted from https://remocn.dev/r/backdrop.json (MIT).
// Remote image fills are intentionally excluded from the offline capability.
export const Backdrop: React.FC<BackdropProps> = ({
  fill = {type: "color", value: "#0a0a0a"},
  padding = 4,
  radius = 1,
  shadow = "0 20px 60px rgba(0,0,0,0.4)",
  children,
}) => {
  const {width} = useVideoConfig();
  const paddingPixels = (padding / 100) * width;
  const radiusPixels = (radius / 100) * width;
  const background =
    fill.type === "color" ? {backgroundColor: fill.value} : {background: fill.value};

  return (
    <AbsoluteFill style={background}>
      {children == null ? null : (
        <div
          style={{
            position: "absolute",
            inset: paddingPixels,
            borderRadius: radiusPixels,
            boxShadow: shadow || undefined,
            display: "flex",
            overflow: "hidden",
          }}
        >
          {children}
        </div>
      )}
    </AbsoluteFill>
  );
};
