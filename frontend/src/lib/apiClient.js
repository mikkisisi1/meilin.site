import axios from 'axios';

const API_BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
