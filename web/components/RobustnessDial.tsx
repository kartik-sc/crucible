"use client";

import { toPercent } from "@/lib/tally";
import { AnimatedCircularProgressBar } from "./fx/AnimatedCircularProgressBar";
import { NumberTicker } from "./fx/NumberTicker";

/** The dial borrows the verdict grammar: red while it's losing, amber contested, green held. */
function toneFor(percent: number) {
  if (percent >= 80) return { stroke: "var(--survived)", text: "text-survived" };
  if (percent >= 50) return { stroke: "var(--unsupported)", text: "text-unsupported" };
  return { stroke: "var(--struck)", text: "text-struck" };
}

export function RobustnessDial({ value }: { value: number | null }) {
  const percent = toPercent(value);
  const tone = toneFor(percent);

  return (
    <div
      role="meter"
      aria-valuemin={0}
      aria-valuemax={1}
      aria-valuenow={value ?? undefined}
      aria-label="Robustness"
      className="h-[124px] w-[124px] sm:h-[168px] sm:w-[168px]"
    >
      <AnimatedCircularProgressBar
        value={percent}
        gaugePrimaryColor={tone.stroke}
        gaugeSecondaryColor="rgba(233, 227, 212, 0.07)"
        className="h-full w-full"
      >
        {value === null ? (
          <span className="font-serif text-4xl leading-none text-bone-faint sm:text-5xl">—</span>
        ) : (
          <span className={`flex items-start font-serif leading-none ${tone.text} text-glow`}>
            <NumberTicker value={percent} className="text-4xl sm:text-5xl" />
            <span className="mt-1 text-lg">%</span>
          </span>
        )}
        <span className="mt-1.5 font-sans text-xs text-bone-dim">robustness</span>
      </AnimatedCircularProgressBar>
    </div>
  );
}
