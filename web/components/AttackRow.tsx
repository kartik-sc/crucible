import type { AttackView } from "@/lib/view-model";
import { WEAKNESS_LABELS } from "@/lib/view-model";
import { VerdictStamp } from "./VerdictStamp";

export function AttackRow({ attack, index }: { attack: AttackView; index: number }) {
  const struck = attack.verdict === "struck";

  return (
    <li
      className="animate-fade-up border-b border-hairline px-5 py-4 last:border-b-0"
      style={{ animationDelay: `${index * 55}ms` }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-label text-bone-faint">
            <span className="font-sans">{WEAKNESS_LABELS[attack.breaker]}</span>
            <span aria-hidden>·</span>
            <span className="font-mono normal-case tracking-normal text-bone-dim">
              {attack.id}
            </span>
          </div>
          <p className="mt-1 truncate font-sans text-sm text-bone">{attack.rationale}</p>
          <p className="mt-1.5 truncate font-mono text-xs text-bone-dim">
            {attack.evidenceLabel}
          </p>
        </div>
        <VerdictStamp verdict={attack.verdict} />
      </div>

      {attack.evidence && (
        <p
          className={`mt-2.5 font-mono text-xs ${
            struck ? "text-struck" : "text-bone-faint"
          }`}
        >
          <span aria-hidden className="mr-1.5 opacity-60">
            ⤷
          </span>
          {attack.evidence}
        </p>
      )}
    </li>
  );
}
