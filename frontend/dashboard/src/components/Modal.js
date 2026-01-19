/**
 * Edit modal component
 */

import { getAssetById, updateAsset } from '../data/assets.js';

let currentAssetId = null;
let onSaveCallback = null;

/**
 * Create modal HTML
 */
export function createModal() {
    return `
    <div id="editModal" class="modal-overlay hidden">
        <div class="modal-content">
            <h3 class="modal-title">Ajuste Manual</h3>
            <p class="modal-subtitle">Edita la <span class="font-bold">CANTIDAD</span> o el PRECIO.</p>
            
            <label class="input-label">Cantidad (Tokens/Acciones)</label>
            <input type="number" step="any" id="manual-qty" class="modal-input">
            
            <label class="input-label">Precio Unitario (€)</label>
            <input type="number" step="any" id="manual-price" class="modal-input">
            
            <div class="modal-actions">
                <button id="modal-cancel" class="btn-cancel">Cancelar</button>
                <button id="modal-save" class="btn-save">Guardar</button>
            </div>
        </div>
    </div>
    `;
}

/**
 * Setup modal event listeners
 */
export function setupModalListeners(onSave) {
    onSaveCallback = onSave;

    const cancelBtn = document.getElementById('modal-cancel');
    const saveBtn = document.getElementById('modal-save');
    const modal = document.getElementById('editModal');

    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeModal);
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', saveChanges);
    }

    // Close on overlay click
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
    }
}

/**
 * Open modal for editing an asset
 */
export function openModal(assetId) {
    const asset = getAssetById(assetId);
    if (!asset) return;

    currentAssetId = assetId;

    const modal = document.getElementById('editModal');
    const qtyInput = document.getElementById('manual-qty');
    const priceInput = document.getElementById('manual-price');

    if (qtyInput) qtyInput.value = asset.qty;
    if (priceInput) priceInput.value = asset.price;

    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('visible');
    }
}

/**
 * Close the modal
 */
export function closeModal() {
    const modal = document.getElementById('editModal');
    if (modal) {
        modal.classList.remove('visible');
        modal.classList.add('hidden');
    }
    currentAssetId = null;
}

/**
 * Save changes from modal
 */
function saveChanges() {
    if (!currentAssetId) return;

    const qtyInput = document.getElementById('manual-qty');
    const priceInput = document.getElementById('manual-price');

    const qty = parseFloat(qtyInput?.value || 0);
    const price = parseFloat(priceInput?.value || 0);

    updateAsset(currentAssetId, {
        qty,
        price,
        manual: true
    });

    closeModal();

    if (onSaveCallback) {
        onSaveCallback();
    }
}
