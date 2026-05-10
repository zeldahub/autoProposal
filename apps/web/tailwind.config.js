/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0F1623",
        surface: "#1A2332",
        primary: "#3B82F6",
        accent: "#10B981",
        danger: "#EF4444",
      },
      fontFamily: {
        ko: ["맑은 고딕", "Malgun Gothic", "Apple SD Gothic Neo", "system-ui"],
      },
      keyframes: {
        toastIn: {
          "0%": { transform: "translateY(8px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        modalIn: {
          "0%": { transform: "scale(0.96)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
      },
      animation: {
        toast: "toastIn 180ms ease-out",
        modal: "modalIn 160ms ease-out",
      },
    },
  },
  plugins: [],
};
