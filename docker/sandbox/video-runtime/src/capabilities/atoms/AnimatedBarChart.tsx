import type React from "react";
import {spring, useCurrentFrame, useVideoConfig} from "remotion";

export type AnimatedBarChartProps = {
  data: number[];
  labels?: string[];
  width?: number;
  height?: number;
  barColor?: string;
  gap?: number;
  staggerFrames?: number;
};

// Adapted from https://remocn.dev/r/animated-bar-chart.json (MIT).
export const AnimatedBarChart: React.FC<AnimatedBarChartProps> = ({
  data,
  labels,
  width = 1000,
  height = 500,
  barColor = "#0ea5e9",
  gap = 16,
  staggerFrames = 6,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const max = Math.max(...data, 1);
  const labelHeight = labels ? 44 : 0;
  const chartHeight = height - labelHeight;
  const barWidth = Math.max(1, (width - gap * (data.length - 1)) / data.length);

  return (
    <svg
      role="img"
      aria-label="Animated bar chart"
      viewBox={`0 0 ${width} ${height}`}
      style={{width: "100%", height: "100%", overflow: "visible"}}
    >
      {data.map((value, index) => {
        const progress = spring({
          frame: frame - index * staggerFrames,
          fps,
          config: {damping: 18, stiffness: 120, mass: 0.8},
        });
        const barHeight = (Math.max(0, value) / max) * (chartHeight - 16) * progress;
        const x = index * (barWidth + gap);
        return (
          <g key={`${labels?.[index] ?? "bar"}-${index}`}>
            <rect
              x={x}
              y={chartHeight - barHeight}
              width={barWidth}
              height={barHeight}
              rx={Math.min(12, barWidth / 4)}
              fill={barColor}
            />
            {labels?.[index] ? (
              <text
                x={x + barWidth / 2}
                y={height - 8}
                textAnchor="middle"
                fill="currentColor"
                fontFamily="Inter, sans-serif"
                fontSize={22}
              >
                {labels[index]}
              </text>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
};
