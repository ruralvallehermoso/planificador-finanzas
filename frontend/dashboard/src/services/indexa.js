/**
 * Indexa Capital API service
 * Connects to the FastAPI backend for secure API access
 * No separate proxy server needed - backend handles Indexa API directly
 */

import { API_BASE } from '../config.js';
const TIMEOUT_MS = 10000; // 10 second timeout

/**
 * Fetch with timeout
 */
async function fetchWithTimeout(url, timeoutMs = TIMEOUT_MS) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(url, { signal: controller.signal });
        clearTimeout(timeoutId);
        return response;
    } catch (e) {
        clearTimeout(timeoutId);
        throw e;
    }
}

/**
 * Fetch Indexa Capital accounts
 * @returns {Promise<Object>} - Response with accounts array or error
 */
export async function fetchIndexaAccounts() {
    try {
        const res = await fetchWithTimeout(`${API_BASE}/api/indexa/accounts`);

        const data = await res.json();

        // Handle API-level errors (returned as JSON with success: false)
        if (!data.success) {
            return {
                success: false,
                error: data.error || 'Error desconocido'
            };
        }

        if (data.accounts) {
            return {
                success: true,
                accounts: data.accounts,
                totalValue: data.total_value
            };
        }

        return {
            success: false,
            error: 'Respuesta inválida'
        };
    } catch (e) {
        // Clean up error message for display
        let errorMessage = e.message;

        if (e.name === 'AbortError') {
            errorMessage = 'Timeout (servidor lento)';
        } else if (errorMessage === 'Failed to fetch') {
            errorMessage = 'Backend no disponible';
        }

        console.error('Error fetching Indexa accounts:', e);
        return {
            success: false,
            error: errorMessage
        };
    }
}

/**
 * Check backend health
 * @returns {Promise<boolean>} - True if backend is available and has token
 */
export async function checkBackendHealth() {
    try {
        const res = await fetchWithTimeout(`${API_BASE}/api/health`, 5000);
        if (res.ok) {
            const data = await res.json();
            return data.status === 'ok' && data.token_available;
        }
        return false;
    } catch (e) {
        return false;
    }
}
