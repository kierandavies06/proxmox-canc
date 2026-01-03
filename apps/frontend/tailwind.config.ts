import type { Config } from "tailwindcss";

const config: Partial<Config> = {
  content: [
    "./components/**/*.{vue,js,ts}",
    "./layouts/**/*.vue",
    "./pages/**/*.vue",
    "./app/**/*.{vue,js,ts}",
    "./composables/**/*.{js,ts}",
    "./plugins/**/*.{js,ts}",
    "./App.{js,ts,vue}",
    "./app.config.{js,ts}",
  ],
  theme: {
    extend: {
      fontFamily: {
        grotesk: ['"Space Grotesk"', "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#edfcff",
          100: "#d8f5ff",
          200: "#b3ebff",
          300: "#78dcff",
          400: "#3ac9ff",
          500: "#16b3f2",
          600: "#078cc1",
          700: "#036f99",
          800: "#075c7c",
          900: "#0c4e68",
        },
      },
      boxShadow: {
        glow: "0 0 40px rgba(16, 185, 129, 0.25)",
      },
    },
  },
};

export default config;
