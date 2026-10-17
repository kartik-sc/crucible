import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "var(--ink)",
          2: "var(--ink-2)",
          3: "var(--ink-3)",
        },
        bone: {
          DEFAULT: "var(--bone)",
          dim: "var(--bone-dim)",
          faint: "var(--bone-faint)",
        },
        hairline: "var(--hairline)",
        accent: "var(--accent)",
        survived: "var(--survived)",
        unsupported: "var(--unsupported)",
        struck: "var(--struck)",
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
