import type { Metadata } from "next";
import { Fraunces, Archivo, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const serif = Fraunces({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
  style: ["normal", "italic"],
  axes: ["opsz"],
});

const sans = Archivo({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

function resolveSiteUrl(): URL {
  const raw = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  try {
    return new URL(raw);
  } catch {
    return new URL("http://localhost:3000");
  }
}

const SITE_URL = resolveSiteUrl();
const DESCRIPTION =
  "Trust infrastructure for AI outputs. Code goes in, adversaries hammer it, only what survives reaches you.";

export const metadata: Metadata = {
  metadataBase: SITE_URL,
  title: "CRUCIBLE — the arena",
  description: DESCRIPTION,
  openGraph: {
    title: "CRUCIBLE — the answer is on trial",
    description: DESCRIPTION,
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "CRUCIBLE — the answer is on trial",
    description: DESCRIPTION,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${serif.variable} ${sans.variable} ${mono.variable}`}>
      <body className="font-sans antialiased">
        <div aria-hidden className="arena-floor" />
        {children}
      </body>
    </html>
  );
}
