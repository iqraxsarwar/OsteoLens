// Local development always uses the backend with inference and RAG support.
// Deployment builds may supply their own API URL.
export const API_URL = import.meta.env.DEV
  ? 'http://127.0.0.1:8000'
  : (import.meta.env.VITE_OSTEOLENS_API_URL || '').replace(/\/$/, '')

// A production build uses its own HTTPS origin by default, never a visitor's localhost.
export const apiFetch = (url, options = {}) => fetch(url, { credentials: 'include', ...options })
