/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        teal: {
          DEFAULT: '#1D9E75',
          light: '#E1F5EE',
          dark: '#085041',
        },
        amber: {
          DEFAULT: '#BA7517',
          light: '#FAEEDA',
        },
        red: {
          DEFAULT: '#E24B4A',
          light: '#FCEBEB',
        },
        blue: {
          DEFAULT: '#378ADD',
          light: '#E6F1FB',
        },
      },
      fontFamily: {
        mono: ['"Space Mono"', 'monospace'],
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
