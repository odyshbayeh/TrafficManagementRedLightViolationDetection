module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',             // ⬅ enables dark mode via <html class="dark">
  theme: {
    extend: {
      fontFamily: {
        heading: ['Poppins', 'sans-serif'],
        body:    ['Inter',   'sans-serif'],
      },
      colors: {
        signal: {
          red   : '#e74c3c',
          yellow: '#f1c40f',
          green : '#27ae60',
          blue  : '#2563eb',
        },
      },
      boxShadow: {
        card: '0 4px 14px rgba(0,0,0,.06)',
      },
    },
  },
  plugins: [],
};
