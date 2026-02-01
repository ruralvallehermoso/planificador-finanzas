import { describe, it, expect, vi } from 'vitest';
import { createSimulatorView, setupSimulatorListeners } from './Simulador.js';

// Mock dependnecies
vi.mock('chart.js', () => ({
    Chart: class { }
}));

vi.mock('../config.js', () => ({
    BACKEND_URL: 'http://localhost:8000'
}));

describe('Simulador Component', () => {
    it('should export createSimulatorView function', () => {
        expect(typeof createSimulatorView).toBe('function');
    });

    it('should generate HTML string', () => {
        const html = createSimulatorView();
        expect(typeof html).toBe('string');
        expect(html).toContain('simulator-container');
        expect(html).toContain('Coste Hipoteca');
    });

    it('should not crash when setting up listeners with missing DOM', () => {
        // Should handle missing elements gracefully
        document.body.innerHTML = '';
        expect(() => setupSimulatorListeners()).not.toThrow();
    });
});
