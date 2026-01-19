/**
 * Formatting utilities
 */

/**
 * Format number as EUR currency (no decimals)
 */
export function formatEUR(n) {
    return new Intl.NumberFormat('es-ES', {
        style: 'currency',
        currency: 'EUR',
        maximumFractionDigits: 0
    }).format(n);
}

/**
 * Format number as USD currency (no decimals)
 */
export function formatUSD(n) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0
    }).format(n);
}

/**
 * Format number in the specified currency
 * @param {number} n - Value to format
 * @param {string} currency - 'EUR' or 'USD'
 */
export function formatCurrency(n, currency = 'EUR') {
    if (currency === 'USD') {
        return formatUSD(n);
    }
    return formatEUR(n);
}

/**
 * Format number as EUR currency (2-4 decimals)
 */
export function formatPrice(n) {
    return new Intl.NumberFormat('es-ES', {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 2,
        maximumFractionDigits: 4
    }).format(n);
}

/**
 * Format number as price in the specified currency (2-4 decimals)
 * @param {number} n - Value to format
 * @param {string} currency - 'EUR' or 'USD'
 */
export function formatPriceCurrency(n, currency = 'EUR') {
    const locale = currency === 'USD' ? 'en-US' : 'es-ES';
    return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 4
    }).format(n);
}

/**
 * Format number as percentage
 */
export function formatPercent(n) {
    return new Intl.NumberFormat('es-ES', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(n / 100);
}
