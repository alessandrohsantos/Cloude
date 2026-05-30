/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        nubank: '#820AD1',
        itau: '#EC7000',
        santander: '#CC0000',
      },
    },
  },
  plugins: [],
}
