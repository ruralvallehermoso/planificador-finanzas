/**
 * Centralized API configuration
 */
export const BACKEND_URL = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' && window.location.hostname !== 'localhost' ? '' : 'http://localhost:8000');
export const API_BASE = BACKEND_URL;
