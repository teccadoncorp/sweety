import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        void: "#070b14",
        paper: "#0c1220",
        ink: "#e8eefc",
        rose: "#8b6dff",
        violet: "#8b6dff",
        cyan: "#4cc9f0",
        clay: "#94a3b8",
        moss: "#34d399",
      },
      fontFamily: {
        serif: ["Fraunces", "Georgia", "serif"],
        sans: ["Outfit", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
