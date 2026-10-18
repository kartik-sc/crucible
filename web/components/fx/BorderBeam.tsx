// Ported from Magic UI's Border Beam (magicui.design, MIT) — Tailwind v4 utilities
// rewritten as inline styles for Tailwind v3, framer-motion import.
"use client";

import type { CSSProperties } from "react";
import { motion, type MotionStyle } from "framer-motion";

interface BorderBeamProps {
  size?: number;
  duration?: number;
  delay?: number;
  colorFrom?: string;
  colorTo?: string;
  reverse?: boolean;
  initialOffset?: number;
  borderWidth?: number;
}

const MASK = "linear-gradient(transparent, transparent), linear-gradient(#000, #000)";

export function BorderBeam({
  size = 50,
  delay = 0,
  duration = 6,
  colorFrom = "#ffaa40",
  colorTo = "#9c40ff",
  reverse = false,
  initialOffset = 0,
  borderWidth = 1,
}: BorderBeamProps) {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 rounded-[inherit] border-transparent"
      style={
        {
          borderWidth,
          borderStyle: "solid",
          borderColor: "transparent",
          maskImage: MASK,
          WebkitMaskImage: MASK,
          maskComposite: "intersect",
          WebkitMaskComposite: "source-in",
          maskClip: "padding-box, border-box",
          WebkitMaskClip: "padding-box, border-box",
        } as CSSProperties
      }
    >
      <motion.div
        className="absolute aspect-square"
        style={
          {
            width: size,
            offsetPath: `rect(0 auto auto 0 round ${size}px)`,
            background: `linear-gradient(to left, ${colorFrom}, ${colorTo}, transparent)`,
          } as MotionStyle
        }
        initial={{ offsetDistance: `${initialOffset}%` }}
        animate={{
          offsetDistance: reverse
            ? [`${100 - initialOffset}%`, `${-initialOffset}%`]
            : [`${initialOffset}%`, `${100 + initialOffset}%`],
        }}
        transition={{ repeat: Infinity, ease: "linear", duration, delay: -delay }}
      />
    </div>
  );
}
