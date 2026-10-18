// Adapted from Magic UI's Animated Circular Progress Bar (magicui.design, MIT).
// Changes: Tailwind v3 classes, children in the centre instead of a raw percent,
// a glow that grows with the value, and a minimum visible arc so low scores
// read as a deliberate stroke rather than a dull sliver.
import type { CSSProperties, ReactNode } from "react";
import { cn } from "@/lib/cn";

interface AnimatedCircularProgressBarProps {
  max?: number;
  min?: number;
  value: number;
  gaugePrimaryColor: string;
  gaugeSecondaryColor: string;
  /** 0–1: how strong the glow is (scaled by the value). */
  glow?: number;
  className?: string;
  children?: ReactNode;
}

const MIN_VISIBLE = 4; // percent — the shortest arc we ever draw for a non-zero value

export function AnimatedCircularProgressBar({
  max = 100,
  min = 0,
  value = 0,
  gaugePrimaryColor,
  gaugeSecondaryColor,
  glow = 1,
  className,
  children,
}: AnimatedCircularProgressBarProps) {
  const circumference = 2 * Math.PI * 45;
  const percentPx = circumference / 100;
  const raw = Math.round(((value - min) / (max - min)) * 100);
  const currentPercent = raw > 0 ? Math.max(MIN_VISIBLE, Math.min(100, raw)) : 0;
  const glowPx = 2 + (currentPercent / 100) * 14 * glow;
  const glowMix = Math.round(25 + (currentPercent / 100) * 55);

  return (
    <div
      className={cn("relative", className)}
      style={
        {
          "--circle-size": "100px",
          "--circumference": circumference,
          "--percent-to-px": `${percentPx}px`,
          "--gap-percent": "5",
          "--offset-factor": "0",
          "--transition-length": "1s",
          "--delay": "0s",
          "--percent-to-deg": "3.6deg",
          transform: "translateZ(0)",
        } as CSSProperties
      }
    >
      <svg fill="none" className="h-full w-full overflow-visible" strokeWidth="2" viewBox="0 0 100 100">
        {currentPercent <= 90 && (
          <circle
            cx="50"
            cy="50"
            r="45"
            strokeWidth="7"
            strokeDashoffset="0"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={
              {
                stroke: gaugeSecondaryColor,
                "--stroke-percent": 90 - currentPercent,
                "--offset-factor-secondary": "calc(1 - var(--offset-factor))",
                strokeDasharray:
                  "calc(var(--stroke-percent) * var(--percent-to-px)) var(--circumference)",
                transform:
                  "rotate(calc(1turn - 90deg - (var(--gap-percent) * var(--percent-to-deg) * var(--offset-factor-secondary)))) scaleY(-1)",
                transition: "all var(--transition-length) ease var(--delay)",
                transformOrigin: "calc(var(--circle-size) / 2) calc(var(--circle-size) / 2)",
              } as CSSProperties
            }
          />
        )}
        <circle
          cx="50"
          cy="50"
          r="45"
          strokeWidth="9"
          strokeDashoffset="0"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={
            {
              stroke: gaugePrimaryColor,
              opacity: currentPercent === 0 ? 0 : 1,
              filter: `drop-shadow(0 0 ${glowPx}px color-mix(in srgb, ${gaugePrimaryColor} ${glowMix}%, transparent))`,
              "--stroke-percent": currentPercent,
              strokeDasharray:
                "calc(var(--stroke-percent) * var(--percent-to-px)) var(--circumference)",
              transition:
                "stroke-dasharray var(--transition-length) cubic-bezier(0.16,1,0.3,1) var(--delay), stroke var(--transition-length) ease var(--delay), filter var(--transition-length) ease var(--delay)",
              transform:
                "rotate(calc(-90deg + var(--gap-percent) * var(--offset-factor) * var(--percent-to-deg)))",
              transformOrigin: "calc(var(--circle-size) / 2) calc(var(--circle-size) / 2)",
            } as CSSProperties
          }
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">{children}</div>
    </div>
  );
}
