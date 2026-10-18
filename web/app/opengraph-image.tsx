import { ImageResponse } from "next/og";

export const alt = "CRUCIBLE — Builder vs Swarm: the answer is on trial";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const INK = "#0b0e14";
const BONE = "#e9e3d4";
const DIM = "#969bab";
const FAINT = "#5c6273";
const BUILDER = "#46d9a0";
const SWARM = "#e5484d";

// lucide shield-check and flame, as used by the arena's corner emblems
const SHIELD = [
  "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z",
  "m9 12 2 2 4-4",
];
const FLAME = [
  "M8.9 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z",
];

function Emblem({ paths, color }: { paths: string[]; color: string }) {
  return (
    <svg width="72" height="72" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {paths.map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}

function Corner({ name, role, color, paths, align }: { name: string; role: string; color: string; paths: string[]; align: "flex-start" | "flex-end" }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: align, width: 330 }}>
      <Emblem paths={paths} color={color} />
      <div style={{ display: "flex", fontSize: 76, fontWeight: 600, marginTop: 12, lineHeight: 1 }}>{name}</div>
      <div style={{ display: "flex", fontSize: 24, color: DIM, marginTop: 12, textAlign: align === "flex-end" ? "right" : "left" }}>
        {role}
      </div>
    </div>
  );
}

export default function OpengraphImage() {
  // a 95% arc, open at the bottom-left like the arena dial
  const r = 92;
  const c = 2 * Math.PI * r;

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          backgroundColor: INK,
          backgroundImage: `radial-gradient(60% 90% at 0% 60%, rgba(70,217,160,0.14), transparent 60%), radial-gradient(60% 90% at 100% 60%, rgba(229,72,77,0.15), transparent 60%)`,
          padding: "56px 72px",
          color: BONE,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
          <div style={{ display: "flex", fontSize: 64, fontWeight: 600, letterSpacing: -1 }}>CRUCIBLE</div>
          <div style={{ display: "flex", fontSize: 30, fontStyle: "italic", color: DIM }}>The answer is on trial.</div>
        </div>

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Corner name="Builder" role="Writes the answer, patches what breaks" color={BUILDER} paths={SHIELD} align="flex-start" />

          <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{ display: "flex", position: "relative", width: 220, height: 220, alignItems: "center", justifyContent: "center" }}>
              <svg width="220" height="220" viewBox="0 0 220 220" style={{ position: "absolute", top: 0, left: 0 }}>
                <circle cx="110" cy="110" r={r} fill="none" stroke="rgba(233,227,212,0.08)" strokeWidth="14" />
                <circle
                  cx="110"
                  cy="110"
                  r={r}
                  fill="none"
                  stroke={BUILDER}
                  strokeWidth="14"
                  strokeLinecap="round"
                  strokeDasharray={`${c * 0.95} ${c}`}
                  transform="rotate(-90 110 110)"
                />
              </svg>
              <div style={{ display: "flex", fontSize: 76, fontWeight: 600, color: BUILDER }}>95%</div>
            </div>
            <div style={{ display: "flex", fontSize: 28, fontStyle: "italic", color: FAINT, marginTop: 8 }}>vs</div>
          </div>

          <Corner name="Swarm" role="Breaks it with evidence anyone can check" color={SWARM} paths={FLAME} align="flex-end" />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
          <div
            style={{
              display: "flex",
              padding: "8px 14px 8px 20px",
              border: `2px solid ${BUILDER}`,
              borderRadius: 6,
              color: BUILDER,
              fontSize: 30,
              fontWeight: 700,
              letterSpacing: 4,
              transform: "rotate(-2deg)",
            }}
          >
            HARDENED
          </div>
          <div style={{ display: "flex", fontSize: 26, color: DIM }}>
            A deterministic verifier settles every attack. Only what survives reaches you.
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
