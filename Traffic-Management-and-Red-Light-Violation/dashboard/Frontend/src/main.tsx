import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

/* -- Persist dark-mode preference BEFORE React renders -- */
if (localStorage.theme === 'dark') {
  document.documentElement.classList.add('dark')
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
