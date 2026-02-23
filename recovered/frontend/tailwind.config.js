/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        chaldea: {
          bg: '#050810',
          panel: '#0a1018',
          'panel-alt': '#0d1520',
          border: '#1a3a4a',
          cyan: '#00d4ff',
          'cyan-dim': '#0a5a6a',
          orange: '#ff9500',
          magenta: '#ff3366',
          gold: '#ffd700',
          text: '#8ba4b4',
          'text-bright': '#d0e8f0',
          green: '#00ff88',
          // Legacy aliases
          primary: '#1a1a2e',
          secondary: '#16213e',
          accent: '#0f3460',
          light: '#eaeaea',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.15s ease',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateX(4px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
}
