import type React from "react";
import {useCurrentFrame} from "remotion";

export const LocalPulse: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        width: 36,
        height: 36,
        borderRadius: "50%",
        background: "#38bdf8",
        scale: String(1 + Math.sin(frame / 8) * 0.2),
      }}
    />
  );
};
