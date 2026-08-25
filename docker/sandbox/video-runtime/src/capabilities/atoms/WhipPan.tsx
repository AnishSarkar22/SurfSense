import type {
  TransitionPresentation,
  TransitionPresentationComponentProps,
} from "@remotion/transitions";
import type React from "react";
import {AbsoluteFill, Easing, interpolate} from "remotion";

export type WhipPanProps = {
  direction?: "left" | "right" | "up" | "down";
  blur?: number;
};

export const whipPanStyle = ({
  progress,
  entering,
  props,
}: {
  progress: number;
  entering: boolean;
  props: Record<string, unknown>;
}): React.CSSProperties => {
  const direction = (props.direction as WhipPanProps["direction"]) ?? "left";
  const blur = (props.blur as number | undefined) ?? 24;
  const travel = interpolate(progress, [0, 1], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.7, 0, 0.2, 1),
  });
  const velocity = Math.sin(Math.PI * travel);
  const vertical = direction === "up" || direction === "down";
  const sign = direction === "left" || direction === "up" ? -1 : 1;
  const offset = (entering ? travel - 1 : travel) * 110 * sign;
  return {
    translate: vertical ? `0 ${offset}%` : `${offset}% 0`,
    scale: vertical ? `1 ${1 + velocity * 0.12}` : `${1 + velocity * 0.12} 1`,
    filter: `blur(${velocity * blur}px)`,
  };
};

const WhipPanPresentation: React.FC<
  TransitionPresentationComponentProps<WhipPanProps>
> = ({children, presentationProgress, presentationDirection, passedProps}) => {
  return (
    <AbsoluteFill
      style={whipPanStyle({
        progress: presentationProgress,
        entering: presentationDirection === "entering",
        props: passedProps,
      })}
    >
      {children}
    </AbsoluteFill>
  );
};

// Vendored from https://remocn.dev/r/whip-pan.json (MIT).
export const whipPan = (
  props: WhipPanProps = {},
): TransitionPresentation<WhipPanProps> => ({
  component: WhipPanPresentation,
  props,
});
