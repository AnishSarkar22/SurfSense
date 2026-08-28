import type React from "react";
import {spring, useCurrentFrame, useVideoConfig} from "remotion";

export type AnimatedLineChartProps = {
  data?: number[];
  width?: number;
  height?: number;
  strokeColor?: string;
  strokeWidth?: number;
  gridColor?: string;
  showDot?: boolean;
  speed?: number;
};

// Adapted from https://remocn.dev/r/animated-line-chart.json (MIT), sized for 1920x1080.
export const AnimatedLineChart: React.FC<AnimatedLineChartProps> = ({
  data = [12, 19, 8, 15, 22, 18, 28, 25, 32],
  width = 1600,
  height = 800,
  strokeColor = "#22c55e",
  strokeWidth = 4,
  gridColor = "#27272a",
  showDot = true,
  speed = 1,
}) => {
  const frame = useCurrentFrame() * speed;
  const {fps, durationInFrames} = useVideoConfig();
  const padding = 80;
  const innerWidth = width - padding * 2;
  const innerHeight = height - padding * 2;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const points = data.map((value, index) => ({
    x: padding + (index / (data.length - 1)) * innerWidth,
    y: padding + innerHeight - ((value - min) / range) * innerHeight,
  }));
  let pathLength = 0;
  for (let index = 1; index < points.length; index++) {
    pathLength += Math.hypot(
      points[index].x - points[index - 1].x,
      points[index].y - points[index - 1].y,
    );
  }
  const progress = spring({
    frame,
    fps,
    durationInFrames: Math.round(durationInFrames * 0.85),
    config: {damping: 200},
  });
  const targetLength = pathLength * progress;
  let traveled = 0;
  let dot = points[0];
  for (let index = 1; index < points.length; index++) {
    const previous = points[index - 1];
    const current = points[index];
    const segmentLength = Math.hypot(current.x - previous.x, current.y - previous.y);
    if (traveled + segmentLength >= targetLength) {
      const segmentProgress = (targetLength - traveled) / segmentLength;
      dot = {
        x: previous.x + (current.x - previous.x) * segmentProgress,
        y: previous.y + (current.y - previous.y) * segmentProgress,
      };
      break;
    }
    traveled += segmentLength;
    dot = current;
  }
  const path = points
    .map(({x, y}, index) => `${index === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");

  return (
    <div style={{position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center"}}>
      <svg role="img" aria-label="Animated line chart" viewBox={`0 0 ${width} ${height}`} style={{width: "83.333%", height: "74.074%"}}>
        {Array.from({length: 5}, (_, index) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: fixed grid order defines geometry.
          <line key={`h-${index}`} x1={padding} x2={padding + innerWidth} y1={padding + (index / 4) * innerHeight} y2={padding + (index / 4) * innerHeight} stroke={gridColor} />
        ))}
        {points.map(({x}, index) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: point order is immutable chart data.
          <line key={`v-${index}`} x1={x} x2={x} y1={padding} y2={padding + innerHeight} stroke={gridColor} />
        ))}
        <path d={path} fill="none" stroke={strokeColor} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={pathLength} strokeDashoffset={pathLength * (1 - progress)} />
        {showDot && progress > 0 && progress < 1 ? (
          <circle cx={dot.x} cy={dot.y} r={strokeWidth * 2} fill={strokeColor} />
        ) : null}
      </svg>
    </div>
  );
};
