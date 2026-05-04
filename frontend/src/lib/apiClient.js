import axios from 'axios';

/**
 * API base URL resolution.
 *
 * Platform-proxied `/api/*` means the same-origin URL *always* works (preview,
 * custom domains like slimyou.life, production). Using `window.location.origin`
 * avoids CORS entirely and makes the build portable across any domain without
 * a rebuild — the previous `process.env.REACT_APP_BACKEND_URL` baked in one
 * specific emergent.host URL at build time, which broke CORS on custom domains.
 *
 * Fall back to the build-time env var only for SSR / non-browser contexts.
 */
const API_BASE = (typeof window !== 'undefined' && window.location && window.location.origin)
  ? `${window.location.origin}/api`
  : `${process.env.REACT_APP_BACKEND_URL || ''}/api`;

/**
 * Centralized axios instance.
 * Auth runs entirely via httpOnly Secure cookies set by the backend on
 * /auth/login, /auth/register and /auth/guest. The browser sends them
 * automatically because of `withCredentials: true`. JS code never reads
 * the JWT — that closes the XSS-token-theft surface.
 */
const apiClient = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

export default apiClient;
export { API_BASE };
