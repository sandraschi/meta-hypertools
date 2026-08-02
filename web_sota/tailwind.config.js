/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: "#00f3ff",
        secondary: "#bd00ff",
        accent: "#ff0055",
        muted: "#c0c0c0",
      },
      fontSize: {
        xs: ["0.8125rem", { lineHeight: "1.25rem" }],
        sm: ["0.9375rem", { lineHeight: "1.5rem" }],
        base: ["1.0625rem", { lineHeight: "1.75rem" }],
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { boxShadow: "0 0 20px rgba(0, 243, 255, 0.1)" },
          "50%": { boxShadow: "0 0 40px rgba(0, 243, 255, 0.3)" },
        },
      },
    },
  },
  plugins: [],
};
