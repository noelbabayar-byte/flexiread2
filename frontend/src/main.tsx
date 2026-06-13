import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// NOTE: StrictMode intentionally removed to prevent engine double-initialization.
// The reader uses a vanilla JS engine with imperative DOM manipulation.
// StrictMode's double-mount/double-effect in development causes the engine
// to initialize → destroy → reinitialize, leaving the DOM in an invalid state.
ReactDOM.createRoot(document.getElementById('root')!).render(<App />)
