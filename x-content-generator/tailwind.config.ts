import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "x-blue": "#1d9bf0",
        "x-dark": "#000000",
        "x-gray": "#71767b",
        "x-border": "#2f3336",
        "x-bg": "#000000",
        "x-card": "#16181c",
        "x-hover": "#1d1f23",
      },
    },
  },
  plugins: [],
};
export default config;
