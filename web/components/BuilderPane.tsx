import type { BuilderView, Domain } from "@/lib/view-model";

const DOMAIN_NOUN: Record<Domain, string> = {
  code: "the implementation",
  factual: "the answer",
  math: "the derivation",
};

export function BuilderPane({
  builder,
  domain,
}: {
  builder: BuilderView | null;
  domain: Domain;
}) {
  const lines = (builder?.contentPreview ?? "").split("\n");

  return (
    <section className="flex min-h-0 flex-col bg-ink-2/60" aria-label="Builder">
      <header className="flex items-baseline justify-between border-b border-hairline px-5 py-4">
        <div>
          <h2 className="font-sans text-[11px] uppercase tracking-label text-bone-dim">
            Builder
          </h2>
          <p className="mt-1 font-serif text-lg text-bone">The defense</p>
        </div>
        {builder && (
          <span className="rounded-full border border-hairline px-2.5 py-1 font-mono text-xs text-accent">
            v{builder.version}
          </span>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
        {builder ? (
          <pre className="font-mono text-[13px] leading-relaxed text-bone">
            {lines.map((line, i) => (
              <div key={i} className="flex gap-4">
                <span
                  aria-hidden
                  className="w-6 shrink-0 select-none text-right text-bone-faint"
                >
                  {i + 1}
                </span>
                <code className="whitespace-pre-wrap">{line || " "}</code>
              </div>
            ))}
          </pre>
        ) : (
          <p className="font-sans text-sm text-bone-faint">
            Awaiting {DOMAIN_NOUN[domain]}…
          </p>
        )}
      </div>
    </section>
  );
}
