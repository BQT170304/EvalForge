/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#040814', // deepest midnight background
          900: '#070f23', // primary app background
          850: '#0b1633', // card and sidebar background
          800: '#102047', // card elevate / panel
          750: '#15295c', // card hover / input background
          700: '#1d3778', // borders & dividers
          650: '#264796', // active borders & subtle accents
          600: '#325bb6', // secondary blue
          500: '#3b82f6', // primary brand blue
          400: '#60a5fa', // bright highlight blue
          300: '#93c5fd', // soft blue
          200: '#bfdbfe',
          100: '#dbeafe',
        },
        cyan: {
          400: '#38bdf8',
          500: '#06b6d4',
          600: '#0891b2',
        },
        eval: {
          bg: '#060d1f',
          surface: '#0a142c',
          card: '#0f1d3e',
          cardHover: '#14254e',
          border: '#1b3266',
          borderLight: '#254488',
          text: '#f1f5f9',
          textMuted: '#94a3b8',
          textDark: '#64748b',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'Monaco', 'Courier New', 'monospace'],
      },
      boxShadow: {
        'glow-sm': '0 0 15px rgba(59, 130, 246, 0.15)',
        'glow': '0 0 25px rgba(59, 130, 246, 0.25)',
        'glow-lg': '0 0 35px rgba(59, 130, 246, 0.35)',
        'glow-cyan': '0 0 25px rgba(56, 189, 248, 0.25)',
      },
    },
  },
  plugins: [],
};
