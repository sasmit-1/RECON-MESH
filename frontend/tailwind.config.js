/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        amoled: '#000000',
        card: '#0a0a0a',
        border: '#1f1f1f',
      }
    },
  },
  plugins: [],
}
