import { ImageResponse } from "next/og";

export const alt = "CRUCIBLE — trust infrastructure for AI outputs";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const VERDICTS: [string, string][] = [
  ["Survived", "#46d9a0"],
  ["Unsupported", "#e0a94a"],
  ["Struck", "#e5484d"],
];

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          backgroundColor: "#0b0e14",
          padding: "72px 80px",
          color: "#e9e3d4",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              display: "flex",
              fontSize: 22,
              letterSpacing: 6,
              textTransform: "uppercase",
              color: "#5c6273",
            }}
          >
            Hacktoberfest Hack Day · Track 2
          </div>
          <div
            style={{
              display: "flex",
              fontSize: 132,
              fontWeight: 600,
              letterSpacing: -2,
              marginTop: 18,
              lineHeight: 1,
            }}
          >
            CRUCIBLE
          </div>
          <div style={{ display: "flex", fontSize: 40, color: "#e0a94a", marginTop: 20 }}>
            The answer is on trial.
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
          <div
            style={{
              display: "flex",
              fontSize: 28,
              color: "#969bab",
              maxWidth: 920,
              lineHeight: 1.45,
            }}
          >
            Trust infrastructure for AI outputs. Code goes in, a swarm of adversaries
            hammers it with checkable evidence, and only what survives reaches you.
          </div>
          <div style={{ display: "flex", gap: 14 }}>
            {VERDICTS.map(([label, color]) => (
              <div
                key={label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 16px",
                  borderRadius: 999,
                  border: "1px solid rgba(221,226,236,0.12)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    width: 12,
                    height: 12,
                    borderRadius: 999,
                    backgroundColor: color,
                  }}
                />
                <div style={{ display: "flex", fontSize: 22, color: "#969bab" }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    ),
    { ...size },
  );
}
