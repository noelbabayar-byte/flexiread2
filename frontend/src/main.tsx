import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// NOTE: StrictMode intentionally removed to prevent engine double-initialization.
ReactDOM.createRoot(document.getElementById('root')!).render(<App />)
