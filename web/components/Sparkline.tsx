"use client";

import { motion } from "framer-motion";

const W = 112;
const H = 26;

/** Robustness after each scoring pass — the climb at a glance. Hidden until two points exist. */
export function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return <div aria-hidden style={{ height: H }} />;
  const step = W / (values.length - 1);
  const points = values.map((v, i) => [i * step, H - 3 - Math.max(0, Math.min(1, v)) * (H - 6)] as const);
  const d = points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const last = points[points.length - 1];

  return (
    <svg
      width={W}
      height={H}
      viewBox={`-3 0 ${W + 6} ${H}`}
      role="img"
      aria-label={`Robustness by round: ${values.map((v) => Math.round(v * 100)).join(", ")}`}
    >
      <line x1={0} x2={W} y1={H - 3} y2={H - 3} stroke="var(--hairline)" />
      <motion.path
        d={d}
        fill="none"
        stroke="var(--survived)"
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
      />
      {last && <circle cx={last[0]} cy={last[1]} r={2.5} fill="var(--survived)" />}
    </svg>
  );
}
