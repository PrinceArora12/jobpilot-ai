/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f5ff",
          100: "#dbe6ff",
          200: "#b8ccff",
          300: "#8aa9ff",
          400: "#5c7fff",
          500: "#3757ff",
          600: "#2338e6",
          700: "#1c2bb4",
          800: "#1a2691",
          900: "#1a2578",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
