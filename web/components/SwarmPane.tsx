import type { AttackView, WeaknessClass } from "@/lib/view-model";
import { WEAKNESS_LABELS } from "@/lib/view-model";
import { BREAKER_ICON } from "@/lib/ui";
import { Gavel } from "lucide-react";
import { AttackRow } from "./AttackRow";

/** Plain-language key for the stamps, for viewers who have never seen a verifier. */
const KEY = [
  { label: "Survived", meaning: "attack failed", dot: "bg-survived" },
  { label: "Struck", meaning: "attack landed", dot: "bg-struck" },
  { label: "Unsupported", meaning: "no evidence either way", dot: "bg-unsupported" },
] as const;

const ROLES: readonly WeaknessClass[] = [
  "boundary",
  "numeric_type",
  "spec_gap",
  "factual",
];

export function SwarmPane({ attacks }: { attacks: AttackView[] }) {
  const active = new Set(attacks.map((a) => a.breaker));

  return (
    <section className="flex min-h-[300px] flex-col lg:min-h-0" aria-label="Breaker swarm">
      <header className="border-b border-hairline px-5 py-4">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 font-sans text-xs font-medium text-swarm">
              <span aria-hidden className="h-2 w-2 rounded-[2px] bg-swarm" />
              Swarm
            </h2>
            <p className="mt-1 font-serif text-xl text-bone">The adversaries</p>
          </div>
          <span className="font-mono text-xs text-bone-dim">
            {attacks.length} attack{attacks.length === 1 ? "" : "s"}
          </span>
        </div>

        <ul className="mt-3 flex flex-wrap gap-1.5" aria-label="Breakers">
          {ROLES.map((role) => {
            const Icon = BREAKER_ICON[role];
            return (
              <li
                key={role}
                className={[
                  "flex items-center gap-1.5 rounded-[3px] border px-2 py-1 font-sans text-[11px] transition-colors duration-300",
                  active.has(role)
                    ? "border-swarm/40 bg-swarm/[0.07] text-bone"
                    : "border-hairline text-bone-faint",
                ].join(" ")}
              >
                <Icon
                  aria-hidden
                  className={[
                    "h-3.5 w-3.5",
                    active.has(role) ? "text-swarm" : "text-bone-faint",
                  ].join(" ")}
                />
                {WEAKNESS_LABELS[role]}
              </li>
            );
          })}
        </ul>

        <p className="mt-3 flex items-start gap-2 font-sans text-xs leading-relaxed text-bone-dim">
          <Gavel aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" />
          <span>
            Every attack is settled by a deterministic verifier: code is run, math is computed,
            claims are checked against sources. No model grades its own homework.
          </span>
        </p>
      </header>

      <div
        aria-hidden
        className="grid grid-cols-[2rem_minmax(0,1fr)_auto] gap-x-3 border-b border-hairline bg-ink-3/50 py-1.5 pl-4 pr-5 font-sans text-[11px] text-bone-faint"
      >
        <span>#</span>
        <span>Attack and evidence</span>
        <span>Ruling</span>
      </div>
      <ul
        aria-label="What the rulings mean"
        className="flex flex-wrap gap-x-4 gap-y-1 border-b border-hairline px-5 py-2 font-sans text-[11px]"
      >
        {KEY.map((k) => (
          <li
            key={k.label}
            aria-label={`${k.label}: ${k.meaning}`}
            className="flex items-center gap-1.5 text-bone-faint"
          >
            <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${k.dot}`} />
            <span aria-hidden>{k.meaning}</span>
          </li>
        ))}
      </ul>

      <ol className="min-h-0 flex-1 overflow-auto">
        {attacks.length === 0 ? (
          <li className="px-5 py-10 text-center font-sans text-sm text-bone-faint">
            No attacks yet — the swarm is circling.
          </li>
        ) : (
          attacks.map((attack, i) => <AttackRow key={attack.id} attack={attack} rank={i + 1} />)
        )}
      </ol>
    </section>
  );
}
