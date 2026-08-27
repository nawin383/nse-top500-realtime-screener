/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html","./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: "#0a0e13",
          card: "#111820",
          border: "#1e2a36",
          accent: "#00d395",
          danger: "#ff4d4d",
          warning: "#ffb020",
          muted: "#8a9bb0"
        }
      }
    },
  },
  plugins: [],
}
