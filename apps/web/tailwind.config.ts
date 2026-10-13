import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        // Road Intelligence glass design tokens (values in app/globals.css).
        // Surface tokens carry their own translucency; an opacity modifier scales it.
        ri: {
          bg: "rgb(var(--ri-bg) / calc(var(--ri-bg-a) * <alpha-value>))",
          sunken: "rgb(var(--ri-sunken) / calc(var(--ri-sunken-a) * <alpha-value>))",
          surface: "rgb(var(--ri-glass) / calc(var(--ri-surface-a) * <alpha-value>))",
          raised: "rgb(var(--ri-glass) / calc(var(--ri-raised-a) * <alpha-value>))",
          input: "rgb(var(--ri-input) / calc(var(--ri-input-a) * <alpha-value>))",
          line: "rgb(var(--ri-glass) / calc(var(--ri-line-a) * <alpha-value>))",
          "line-strong": "rgb(var(--ri-glass) / calc(var(--ri-line-strong-a) * <alpha-value>))",
          solid: "rgb(var(--ri-solid) / <alpha-value>)",
          text: "rgb(var(--ri-text) / <alpha-value>)",
          "text-soft": "rgb(var(--ri-text-soft) / <alpha-value>)",
          muted: "rgb(var(--ri-muted) / <alpha-value>)",
          faint: "rgb(var(--ri-faint) / <alpha-value>)",
          primary: "rgb(var(--ri-primary) / <alpha-value>)",
          "primary-bright": "rgb(var(--ri-primary-bright) / <alpha-value>)",
          "on-primary": "rgb(var(--ri-on-primary) / <alpha-value>)",
          success: "rgb(var(--ri-success) / <alpha-value>)",
          warning: "rgb(var(--ri-warning) / <alpha-value>)",
          orange: "rgb(var(--ri-orange) / <alpha-value>)",
          danger: "rgb(var(--ri-danger) / <alpha-value>)",
          "danger-soft": "rgb(var(--ri-danger-soft) / <alpha-value>)",
          "danger-deep": "rgb(var(--ri-danger-deep) / <alpha-value>)",
          review: "rgb(var(--ri-review) / <alpha-value>)",
          "review-soft": "rgb(var(--ri-review-soft) / <alpha-value>)",
          info: "rgb(var(--ri-info) / <alpha-value>)",
          "info-soft": "rgb(var(--ri-info-soft) / <alpha-value>)",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        // Legacy aliases, kept neutral so nothing falls back to the old navy palette.
        background: "#050506",
        foreground: "#e5e5e8",
        primary: { DEFAULT: "#ffffff", foreground: "#000000" },
        secondary: { DEFAULT: "#d4d4d8", foreground: "#000000" },
        muted: { DEFAULT: "#18181b", foreground: "#a1a1aa" },
        accent: { DEFAULT: "#232326", foreground: "#e5e5e8" },
        popover: { DEFAULT: "#0f0f10", foreground: "#e5e5e8" },
        card: { DEFAULT: "#111113", foreground: "#e5e5e8" },
        destructive: { DEFAULT: "#ef4444", foreground: "#ffffff" },
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
        "code-sm": ["JetBrains Mono", "ui-monospace", "monospace"],
        "code-md": ["JetBrains Mono", "ui-monospace", "monospace"],
        "code-lg": ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        stitch: "0 1px 3px 0 rgba(0, 0, 0, 0.35)",
        "stitch-elevated": "0 4px 12px 0 rgba(0, 0, 0, 0.45)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
