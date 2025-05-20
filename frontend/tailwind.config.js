/** @type {import('tailwindcss').Config} */
const config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class', // Активация переключения тем на основе класса .dark
  theme: {
    extend: {
      colors: {
        // Улучшенная палитра с более контрастными цветами
        blue: {
          50: '#e6f0ff',
          100: '#cce0ff',
          200: '#99c0ff',
          300: '#66a0ff',
          400: '#3380ff',
          500: '#0066ff', // более насыщенный синий
          600: '#0052cc',
          700: '#003d99',
          800: '#002966',
          900: '#001433',
        },
        green: {
          50: '#e6ffee',
          100: '#ccffdd',
          200: '#99ffbb',
          300: '#66ff99',
          400: '#33ff77',
          500: '#00ff55', // более яркий зеленый
          600: '#00cc44',
          700: '#009933',
          800: '#006622',
          900: '#003311',
        },
        red: {
          50: '#ffe6e6',
          100: '#ffcccc',
          200: '#ff9999',
          300: '#ff6666',
          400: '#ff3333',
          500: '#ff0000', // более насыщенный красный
          600: '#cc0000',
          700: '#990000',
          800: '#660000',
          900: '#330000',
        },
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#9ca3af',
          500: '#6b7280', // более темный серый для лучшей читаемости
          600: '#4b5563',
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        },
        // Переменные цветов темы
        background: {
          DEFAULT: 'var(--background)',
        },
        foreground: {
          DEFAULT: 'var(--foreground)',
        },
        primary: {
          DEFAULT: 'var(--primary)',
          light: 'var(--primary-light)',
          dark: 'var(--primary-dark)',
        },
        card: {
          bg: 'var(--card-bg)',
          border: 'var(--card-border)',
        },
        form: {
          bg: 'var(--form-bg)',
          input: 'var(--form-input-bg)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
          inverted: 'var(--text-inverted)',
        },
      },
      // Увеличиваем контрастность
      contrast: {
        '105': '1.05',
        '110': '1.1',
        '115': '1.15',
      },
    },
  },
  plugins: [],
};

// Экспорт для поддержки как CommonJS, так и ES модулей
module.exports = config;
export default config;
