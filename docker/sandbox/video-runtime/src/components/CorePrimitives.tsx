import {Video} from "@remotion/media";
import type React from "react";
import {
  Img,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";
import {fontFamilies} from "../generated/capability-registry";
import type {VideoLayer} from "../schemas/VideoRenderInput";

type CoreLayer = Exclude<VideoLayer, {type: "component"}>;
type CommonLayer = CoreLayer & {
  x: number;
  y: number;
  width: number;
  height: number;
  opacity: number;
  rotation: number;
  scale: number;
  z_index: number;
};
type ChartLayer = Extract<CoreLayer, {type: "chart"}>;

const keyed = <Value,>(values: readonly Value[]) =>
  values.map((value, position) => ({key: String(position), position, value}));

const animationProgress = (frame: number, durationInFrames: number) =>
  durationInFrames <= 1
    ? 1
    : interpolate(frame, [0, Math.min(45, durationInFrames - 1)], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });

const animatedValue = (
  layer: CommonLayer,
  field: "x" | "y" | "scale" | "opacity",
  frame: number,
) => {
  const points = [...layer.keyframes]
    .filter((keyframe) => keyframe[field] !== undefined)
    .sort((left, right) => left.frame - right.frame)
    .filter((point, index, sorted) => sorted[index + 1]?.frame !== point.frame);
  if (points.length === 0) return layer[field];
  if (points.length === 1) return points[0][field] ?? layer[field];
  return interpolate(
    frame,
    points.map(({frame: keyframe}) => keyframe),
    points.map((point) => point[field] ?? layer[field]),
    {extrapolateLeft: "clamp", extrapolateRight: "clamp"},
  );
};

const commonStyle = (layer: CommonLayer, frame: number): React.CSSProperties => ({
  position: "absolute",
  left: animatedValue(layer, "x", frame),
  top: animatedValue(layer, "y", frame),
  width: layer.width,
  height: layer.height,
  opacity: animatedValue(layer, "opacity", frame),
  rotate: `${layer.rotation}deg`,
  scale: animatedValue(layer, "scale", frame),
  zIndex: layer.z_index,
  filter: layer.filter
    ? `blur(${layer.filter.blur}px) brightness(${layer.filter.brightness}) contrast(${layer.filter.contrast}) saturate(${layer.filter.saturate})`
    : undefined,
  boxSizing: "border-box",
});

const chartY = (value: number, maximum: number, range: number) =>
  30 + ((maximum - value) / range) * 420;

const Chart: React.FC<{layer: ChartLayer}> = ({layer}) => {
  const frame = useCurrentFrame();
  const progress = animationProgress(frame, layer.duration_in_frames);
  if (layer.chart === "metric_grid") {
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${Math.min(3, layer.values.length)}, 1fr)`,
          gap: 20,
          width: "100%",
          height: "100%",
        }}
      >
        {keyed(layer.values).map(({key, position, value}) => (
          <div
            key={key}
            style={{
              display: "grid",
              placeItems: "center",
              border: "1px solid rgba(148,163,184,.35)",
              borderRadius: 18,
              font: '600 44px "JetBrains Mono", monospace',
              color: layer.color,
            }}
          >
            <span>{Math.round(value * progress).toLocaleString("en-US")}</span>
            {layer.labels[position] ? (
              <small style={{font: "400 20px Inter, sans-serif", color: "#cbd5e1"}}>
                {layer.labels[position]}
              </small>
            ) : null}
          </div>
        ))}
      </div>
    );
  }
  const minimum = Math.min(0, ...layer.values);
  const maximum = Math.max(0, ...layer.values);
  const range = maximum - minimum || 1;
  const baselineY = chartY(0, maximum, range);
  const points = keyed(layer.values).map(({key, position, value}) => ({
    key,
    x:
      layer.values.length === 1
        ? 500
        : 30 + (position / (layer.values.length - 1)) * 940,
    y: chartY(value * progress, maximum, range),
  }));
  if (layer.chart === "line") {
    return (
      <svg viewBox="0 0 1000 500" style={{width: "100%", height: "100%"}}>
        <title>Animated line chart</title>
        <line
          x1="30"
          y1={baselineY}
          x2="970"
          y2={baselineY}
          stroke="rgba(148,163,184,.35)"
          strokeWidth="2"
        />
        <polyline
          points={points.map(({x, y}) => `${x},${y}`).join(" ")}
          fill="none"
          stroke={layer.color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {points.map(({key, x, y}) => (
          <circle key={key} cx={x} cy={y} r="7" fill={layer.color} />
        ))}
      </svg>
    );
  }
  const slotWidth = 940 / layer.values.length;
  const barWidth = Math.max(2, slotWidth * 0.72);
  return (
    <svg viewBox="0 0 1000 500" style={{width: "100%", height: "100%"}}>
      <title>Animated bar chart</title>
      <line
        x1="30"
        y1={baselineY}
        x2="970"
        y2={baselineY}
        stroke="rgba(148,163,184,.35)"
        strokeWidth="2"
      />
      {points.map(({key, y}, index) => {
        const top = Math.min(y, baselineY);
        return (
          <rect
            key={key}
            x={30 + index * slotWidth + (slotWidth - barWidth) / 2}
            y={top}
            width={barWidth}
            height={Math.max(2, Math.abs(y - baselineY))}
            rx={Math.min(10, barWidth / 4)}
            fill={layer.color}
          />
        );
      })}
    </svg>
  );
};

const audioBars = (samples: number[], count: number) =>
  Array.from({length: count}, (_, index) => {
    const start = Math.floor((index * samples.length) / count);
    const end = Math.max(start + 1, Math.floor(((index + 1) * samples.length) / count));
    const bucket = samples.slice(start, end);
    return bucket.reduce((sum, sample) => sum + sample, 0) / bucket.length;
  });

const arrowPoints = (
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  strokeWidth: number,
) => {
  const angle = Math.atan2(y2 - y1, x2 - x1);
  const size = Math.max(10, strokeWidth * 4);
  return [
    [x2, y2],
    [x2 - size * Math.cos(angle - Math.PI / 6), y2 - size * Math.sin(angle - Math.PI / 6)],
    [x2 - size * Math.cos(angle + Math.PI / 6), y2 - size * Math.sin(angle + Math.PI / 6)],
  ]
    .map((point) => point.join(","))
    .join(" ");
};

const groupLayout = (
  layer: Extract<CoreLayer, {type: "group"}>,
): React.CSSProperties => {
  if (layer.layout === "free") return {display: "block"};
  if (layer.layout === "grid") {
    return {
      display: "grid",
      gridTemplateColumns: `repeat(${Math.max(1, Math.ceil(Math.sqrt(layer.children.length)))}, minmax(0, 1fr))`,
    };
  }
  return {
    display: "flex",
    flexDirection: layer.layout === "column" ? "column" : "row",
  };
};

export const CorePrimitive: React.FC<{layer: CoreLayer}> = ({layer}) => {
  const frame = useCurrentFrame();
  const style = commonStyle(layer as CommonLayer, frame);

  switch (layer.type) {
    case "text":
    case "rich_text":
      return (
        <div
          style={{
            ...style,
            display: "flex",
            alignItems: "center",
            color: layer.color,
            fontFamily:
              fontFamilies[layer.font_id as keyof typeof fontFamilies] ??
              "sans-serif",
            fontSize: layer.font_size,
            fontWeight: layer.font_weight,
            textAlign: layer.align,
            whiteSpace: "pre-wrap",
            overflow: "hidden",
          }}
        >
          {layer.text}
        </div>
      );
    case "shape":
      if (layer.shape === "line") {
        return (
          <svg
            viewBox={`0 0 ${layer.width} ${layer.height}`}
            preserveAspectRatio="none"
            style={style}
          >
            <title>Line</title>
            <line
              x1="0"
              y1={layer.height / 2}
              x2={layer.width}
              y2={layer.height / 2}
              stroke={layer.stroke ?? layer.fill}
              strokeWidth={Math.max(1, layer.stroke_width)}
              strokeLinecap="round"
            />
          </svg>
        );
      }
      return (
        <div
          style={{
            ...style,
            borderRadius: layer.shape === "ellipse" ? "50%" : layer.radius,
            background: layer.gradient_to
              ? `linear-gradient(135deg, ${layer.fill}, ${layer.gradient_to})`
              : layer.fill,
            border: layer.stroke
              ? `${layer.stroke_width}px solid ${layer.stroke}`
              : undefined,
          }}
        />
      );
    case "image":
      return <Img src={staticFile(layer.src)} style={{...style, objectFit: layer.fit}} />;
    case "video":
      return (
        <Video
          src={staticFile(layer.src)}
          muted={layer.muted}
          style={{...style, objectFit: layer.fit}}
        />
      );
    case "svg":
    case "icon":
      return (
        <svg viewBox={layer.view_box} style={style}>
          <title>{layer.type === "icon" ? "Icon" : "Illustration"}</title>
          <path d={layer.path} fill={layer.fill} stroke={layer.stroke} />
        </svg>
      );
    case "chart":
      return (
        <div style={style}>
          <Chart layer={layer} />
        </div>
      );
    case "code":
      {
        const highlighted = new Set(layer.highlight_lines);
        return (
          <pre
            data-language={layer.language}
            style={{
              ...style,
              margin: 0,
              padding: 30,
              overflow: "hidden",
              borderRadius: 18,
              background: "#0b1120",
              color: "#e2e8f0",
              font: '24px/1.55 "JetBrains Mono", monospace',
              whiteSpace: "pre-wrap",
            }}
          >
            {keyed(layer.code.split("\n")).map(({key, position, value: line}) => (
              <span
                key={key}
                style={{
                  display: "block",
                  minHeight: "1.55em",
                  marginInline: -12,
                  paddingInline: 12,
                  background: highlighted.has(position + 1)
                    ? "rgba(56, 189, 248, .16)"
                    : undefined,
                }}
              >
                {line || " "}
              </span>
            ))}
          </pre>
        );
      }
    case "connector": {
      const x1 = animatedValue(layer as CommonLayer, "x", frame);
      const y1 = animatedValue(layer as CommonLayer, "y", frame);
      return (
        <svg
          viewBox="0 0 1920 1080"
          preserveAspectRatio="none"
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            opacity: animatedValue(layer as CommonLayer, "opacity", frame),
            rotate: `${layer.rotation}deg`,
            scale: animatedValue(layer as CommonLayer, "scale", frame),
            filter: style.filter,
            overflow: "visible",
            zIndex: layer.z_index,
          }}
        >
          <title>Connector</title>
          <line
            x1={x1}
            y1={y1}
            x2={layer.x2}
            y2={layer.y2}
            stroke={layer.color}
            strokeWidth={layer.stroke_width}
            strokeLinecap="round"
          />
          {layer.arrow ? (
            <polygon
              points={arrowPoints(
                x1,
                y1,
                layer.x2,
                layer.y2,
                layer.stroke_width,
              )}
              fill={layer.color}
            />
          ) : null}
        </svg>
      );
    }
    case "audio_visualization": {
      const samples = audioBars(layer.samples, layer.bars);
      return (
        <div style={{...style, display: "flex", alignItems: "center", gap: 4}}>
          {keyed(samples).map(({key, value: sample}) => (
            <div
              key={key}
              style={{
                flex: 1,
                height: `${Math.max(4, sample * 100)}%`,
                borderRadius: 999,
                background: layer.color,
              }}
            />
          ))}
        </div>
      );
    }
    case "repeated":
      return (
        <div
          style={{
            ...style,
            display: "grid",
            gridTemplateColumns: `repeat(${Math.min(layer.columns, layer.count)}, 1fr)`,
            gap: layer.gap,
          }}
        >
          {keyed(Array.from({length: layer.count})).map(({key}) => (
            <div
              key={key}
              style={{background: layer.fill, borderRadius: layer.radius}}
            />
          ))}
        </div>
      );
    case "group":
      return (
        <div
          style={{
            ...style,
            ...groupLayout(layer),
            gap: layer.gap,
            overflow: layer.clip ? "hidden" : "visible",
          }}
        >
          {keyed(layer.children).map(({key, value: child}) => (
            <Sequence
              key={key}
              from={child.from}
              durationInFrames={child.duration_in_frames}
              layout="none"
            >
              <CorePrimitive layer={child} />
            </Sequence>
          ))}
        </div>
      );
  }
};
