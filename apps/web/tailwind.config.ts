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
        background: "#050914",
        foreground: "#dce2f6",
        surface: {
          DEFAULT: "#0c1321",
          dim: "#0c1321",
          bright: "#323949",
          container: {
            lowest: "#070e1c",
            low: "#151b2a",
            DEFAULT: "#19202e",
            high: "#232a39",
            highest: "#2e3544",
          },
          variant: "#2e3544",
          tint: "#4cd7f6",
        },
        "on-surface": {
          DEFAULT: "#dce2f6",
          variant: "#bcc9cd",
        },
        outline: {
          DEFAULT: "#869397",
          variant: "#3d494c",
        },
        primary: {
          DEFAULT: "#4cd7f6",
          container: "#06b6d4",
          foreground: "#003640",
          fixed: "#acedff",
          "fixed-dim": "#4cd7f6",
          "on-fixed": "#001f26",
          "on-fixed-variant": "#004e5c",
          "on-container": "#00424f",
        },
        secondary: {
          DEFAULT: "#adc6ff",
          container: "#0566d9",
          foreground: "#002e6a",
          fixed: "#d8e2ff",
          "fixed-dim": "#adc6ff",
          "on-fixed": "#001a42",
          "on-fixed-variant": "#004395",
          "on-container": "#e6ecff",
        },
        tertiary: {
          DEFAULT: "#4edea3",
          container: "#1bbd85",
          foreground: "#003824",
          fixed: "#6ffbbe",
          "fixed-dim": "#4edea3",
          "on-fixed": "#002113",
          "on-fixed-variant": "#005236",
          "on-container": "#00452e",
        },
        error: {
          DEFAULT: "#ffb4ab",
          container: "#93000a",
          foreground: "#690005",
          "on-container": "#ffdad6",
        },
        muted: {
          DEFAULT: "#19202e",
          foreground: "#94a3b8",
        },
        accent: {
          DEFAULT: "#232a39",
          foreground: "#dce2f6",
        },
        popover: {
          DEFAULT: "#151b2a",
          foreground: "#dce2f6",
        },
        card: {
          DEFAULT: "#17223a",
          foreground: "#dce2f6",
        },
        destructive: {
          DEFAULT: "#ef4444",
          foreground: "#ffffff",
        },
      },
      fontFamily: {
        sans: ["var(--font-sans)", "Inter", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "monospace"],
        "code-sm": ["var(--font-mono)", "JetBrains Mono", "monospace"],
        "code-md": ["var(--font-mono)", "JetBrains Mono", "monospace"],
        "code-lg": ["var(--font-mono)", "JetBrains Mono", "monospace"],
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
