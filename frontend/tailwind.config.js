/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html","./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: "#0a0e13",
          bg2: "#0f141c",
          card: "#111820",
          card2: "#151d27",
          border: "#1e2a36",
          borderLight: "#253545",
          accent: "#00d395",
          accent2: "#0affb7",
          danger: "#ff4d4d",
          warning: "#ffb020",
          muted: "#8a9bb0",
          muted2: "#5a6b84",
          blue: "#3b9eff",
          purple: "#8b5cf6"
        }
      },
      fontFamily: {
        sans: ['Inter','system-ui','sans-serif'],
        mono: ['JetBrains Mono','Geist Mono','monospace'],
      },
      animation: {
        shimmer: 'shimmer 2s infinite',
        float: 'float 3s ease-in-out infinite',
        glow: 'glow 2s ease-in-out infinite',
      },
      keyframes: {
        shimmer: { '0%': { transform:'translateX(-100%)' }, '100%':{ transform:'translateX(100%)'} },
        float: { '0%,100%':{ transform:'translateY(0)' }, '50%':{ transform:'translateY(-4px)'} },
        glow: { '0%,100%':{ boxShadow:'0 0 20px rgba(0,211,149,0.3)' }, '50%':{ boxShadow:'0 0 30px rgba(0,211,149,0.5)'} },
      }
    },
  },
  plugins: [],
}
