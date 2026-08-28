import type React from "react";
import type {SpatialGridProps, SpatialStackProps} from "./authoring-contract";
export type {SpatialGridProps, SpatialStackProps} from "./authoring-contract";

const bounded = (value: number, fallback: number, min: number, max: number) =>
  Number.isFinite(value) ? Math.min(max, Math.max(min, value)) : fallback;

export const SpatialStack: React.FC<SpatialStackProps> = ({
  children,
  direction = "column",
  gap = 24,
  align = "stretch",
  justify = "flex-start",
  style,
}) => {
  const safeGap = bounded(gap, 24, 0, 240);
  return (
    <div
      style={{
        ...style,
        alignItems: align,
        display: "flex",
        flexDirection: direction,
        gap: safeGap,
        justifyContent: justify,
        minHeight: 0,
        minWidth: 0,
      }}
    >
      {children}
    </div>
  );
};

export const SpatialGrid: React.FC<SpatialGridProps> = ({
  children,
  minItemWidth = 280,
  gap = 24,
  align = "stretch",
  style,
}) => {
  const safeGap = bounded(gap, 24, 0, 240);
  const safeMinItemWidth = bounded(minItemWidth, 280, 160, 960);
  return (
    <div
      style={{
        ...style,
        alignItems: align,
        display: "grid",
        gap: safeGap,
        gridTemplateColumns: `repeat(auto-fit, minmax(min(100%, ${safeMinItemWidth}px), 1fr))`,
        minHeight: 0,
        minWidth: 0,
      }}
    >
      {children}
    </div>
  );
};
