import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#ffffff",
        paper: "#f4f7fb",
        ink: "#0f172a",
        line: "#d7e3f4",
        rose: "#1d4ed8",
        violet: "#1d4ed8",
        cyan: "#1d4ed8",
        clay: "#64748b",
        moss: "#047857",
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.04)",
      },
    },
  },
  plugins: [],
};

export default config;
