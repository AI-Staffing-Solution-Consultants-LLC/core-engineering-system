import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep slate × cyan accent — dark theme tokens
        "app-bg": "#0f172a",
        "app-panel": "#1e293b",
        "app-border": "#334155",
        "app-text-muted": "#94a3b8",
        "app-text": "#e2e8f0",
        "app-accent": "#22d3ee",
        "app-accent-hover": "#67e8f9",
      },
    },
  },
  plugins: [],
};
export default config;
