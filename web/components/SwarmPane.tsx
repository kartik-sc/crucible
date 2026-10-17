import type { AttackView, WeaknessClass } from "@/lib/view-model";
import { WEAKNESS_LABELS } from "@/lib/view-model";
import { AttackRow } from "./AttackRow";

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
        <div className="flex items-baseline justify-between">
          <div>
            <h2 className="font-sans text-[11px] uppercase tracking-label text-bone-dim">
              Swarm
            </h2>
            <p className="mt-1 font-serif text-lg text-bone">The adversaries</p>
          </div>
          <span className="font-mono text-xs text-bone-dim">
            {attacks.length} attack{attacks.length === 1 ? "" : "s"}
          </span>
        </div>

        <ul className="mt-3 flex flex-wrap gap-1.5">
          {ROLES.map((role) => (
            <li
              key={role}
              className={[
                "rounded-full border px-2.5 py-1 font-sans text-[10px] uppercase tracking-label",
                active.has(role)
                  ? "border-accent/40 text-accent"
                  : "border-hairline text-bone-faint",
              ].join(" ")}
            >
              {WEAKNESS_LABELS[role]}
            </li>
          ))}
        </ul>
      </header>

      <ol className="min-h-0 flex-1 overflow-auto">
        {attacks.length === 0 ? (
          <li className="px-5 py-10 text-center font-sans text-sm text-bone-faint">
            No attacks yet — the swarm is circling.
          </li>
        ) : (
          attacks.map((attack) => <AttackRow key={attack.id} attack={attack} />)
        )}
      </ol>
    </section>
  );
}
