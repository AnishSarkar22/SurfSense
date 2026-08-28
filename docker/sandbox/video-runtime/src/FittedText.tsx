import {fitTextOnNLines} from "@remotion/layout-utils";
import type React from "react";

type LockedTextStyle =
  | "fontFamily"
  | "fontSize"
  | "fontWeight"
  | "letterSpacing"
  | "lineHeight"
  | "maxWidth"
  | "overflow"
  | "whiteSpace"
  | "width";

export type FittedTextProps = {
  id: string;
  children: string;
  maxWidth: number;
  maxLines?: number;
  maxFontSize?: number;
  fontFamily?: "Inter" | "Lora" | "JetBrains Mono";
  fontWeight?: number | string;
  letterSpacing?: string;
  lineHeight?: number;
  style?: Omit<React.CSSProperties, LockedTextStyle>;
};

export const FittedText: React.FC<FittedTextProps> = ({
  id,
  children,
  maxWidth,
  maxLines = 2,
  maxFontSize = 120,
  fontFamily = "Inter",
  fontWeight = 400,
  letterSpacing,
  lineHeight = 1.1,
  style,
}) => {
  if (!children.trim()) throw new Error(`FittedText ${id} requires non-empty text`);
  if (!Number.isFinite(maxWidth) || maxWidth <= 0) {
    throw new Error(`FittedText ${id} requires a positive finite maxWidth`);
  }
  if (!Number.isInteger(maxLines) || maxLines < 1 || maxLines > 12) {
    throw new Error(`FittedText ${id} requires maxLines between 1 and 12`);
  }
  if (!Number.isFinite(maxFontSize) || maxFontSize <= 0) {
    throw new Error(`FittedText ${id} requires a positive finite maxFontSize`);
  }

  const fitted = fitTextOnNLines({
    text: children,
    maxLines,
    maxBoxWidth: maxWidth,
    fontFamily,
    fontWeight,
    letterSpacing,
    maxFontSize,
    validateFontIsLoaded: true,
  });

  return (
    <div
      style={{
        ...style,
        fontFamily,
        fontSize: fitted.fontSize,
        fontWeight,
        letterSpacing,
        lineHeight,
        maxWidth,
        overflow: "hidden",
        paddingBlock: "0.08em",
        whiteSpace: "pre",
        width: maxWidth,
      }}
    >
      {fitted.lines.join("\n")}
    </div>
  );
};
