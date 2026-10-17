"use client";

import { useEffect } from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useReducedMotion,
  animate,
} from "framer-motion";

const SIZE = 132;
const STROKE = 9;
const RADIUS = (SIZE - STROKE) / 2;
const GAP = 0.26; // fraction of the circle left open at the bottom (an arc, not a ring)
const ARC = 1 - GAP;
const CIRC = 2 * Math.PI * RADIUS;

export function RobustnessDial({ value }: { value: number | null }) {
  const reduce = useReducedMotion();
  const target = value ?? 0;

  const progress = useSpring(0, { stiffness: 90, damping: 20 });
  const number = useMotionValue(0);

  useEffect(() => {
    if (reduce) progress.jump(target);
    else progress.set(target);
    const controls = animate(number, target, {
      duration: reduce ? 0 : 0.9,
      ease: [0.16, 1, 0.3, 1],
    });
    return () => controls.stop();
  }, [target, reduce, progress, number]);

  const dashoffset = useTransform(progress, (p) => CIRC * (1 - p * ARC));
  const label = useTransform(number, (n) => (value === null ? "—" : n.toFixed(2)));

  return (
    <div
      className="relative"
      style={{ width: SIZE, height: SIZE }}
      role="meter"
      aria-valuemin={0}
      aria-valuemax={1}
      aria-valuenow={value ?? undefined}
      aria-label="Robustness"
    >
      <svg
        width={SIZE}
        height={SIZE}
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="-rotate-[234deg]"
      >
        <defs>
          <linearGradient id="verdict-ramp" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--struck)" />
            <stop offset="55%" stopColor="var(--unsupported)" />
            <stop offset="100%" stopColor="var(--survived)" />
          </linearGradient>
        </defs>
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="var(--hairline)"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={`${CIRC * ARC} ${CIRC}`}
        />
        <motion.circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="url(#verdict-ramp)"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={`${CIRC * ARC} ${CIRC}`}
          strokeDashoffset={dashoffset}
        />
      </svg>

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span className="font-serif text-3xl leading-none text-bone tabular-nums">
          {label}
        </motion.span>
        <span className="mt-1 font-sans text-[9px] uppercase tracking-label text-bone-dim">
          Robustness
        </span>
      </div>
    </div>
  );
}
