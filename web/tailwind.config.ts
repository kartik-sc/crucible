import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "rgb(var(--c-ink) / <alpha-value>)",
          2: "rgb(var(--c-ink-2) / <alpha-value>)",
          3: "rgb(var(--c-ink-3) / <alpha-value>)",
        },
        bone: {
          DEFAULT: "rgb(var(--c-bone) / <alpha-value>)",
          dim: "rgb(var(--c-bone-dim) / <alpha-value>)",
          faint: "rgb(var(--c-bone-faint) / <alpha-value>)",
        },
        hairline: "var(--hairline)",
        accent: "rgb(var(--c-accent) / <alpha-value>)",
        survived: "rgb(var(--c-survived) / <alpha-value>)",
        unsupported: "rgb(var(--c-unsupported) / <alpha-value>)",
        struck: "rgb(var(--c-struck) / <alpha-value>)",
        builder: "rgb(var(--c-survived) / <alpha-value>)",
        swarm: "rgb(var(--c-struck) / <alpha-value>)",
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        label: "0.18em",
      },
      transitionTimingFunction: {
        settle: "cubic-bezier(0.16, 1, 0.3, 1)",
        exit: "cubic-bezier(0.4, 0, 1, 1)",
      },
      boxShadow: {
        panel: "0 1px 0 0 var(--hairline), 0 24px 60px -30px rgba(0,0,0,0.8)",
        stamp: "inset 0 0 0 1.5px currentColor, 0 1px 12px -6px currentColor",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.4s cubic-bezier(0.16,1,0.3,1) both",
      },
    },
  },
  plugins: [],
};

export default config;
