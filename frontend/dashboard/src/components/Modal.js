/**
 * Modal component for Asset Editing and Asset Creation
 */

import { getAssetById, updateAsset, updateAssetAPI, createAssetAPI, deleteAssetAPI } from '../data/assets.js';

let currentAssetId = null;
let isCreationMode = false;
let onSaveCallback = null;

/**
 * Create modal HTML
 */
export function createModal() {
    return `
    <div id="editModal" class="modal-overlay hidden">
        <div class="modal-content">
            <h3 class="modal-title" id="modal-title">Ajuste Manual</h3>
            <p class="modal-subtitle" id="modal-subtitle">Edita la <span class="font-bold">CANTIDAD</span> o el PRECIO.</p>
            
            <div id="create-fields" class="hidden">
                <label class="input-label">Categoría</label>
                <select id="asset-cat" class="modal-input modal-select">
                    <option value="Renta Fija">Renta Fija (Bonos/Deuda)</option>
                    <option value="Acciones">Acciones</option>
                    <option value="Cripto">Cripto</option>
                    <option value="Fondos">Fondos</option>
                    <option value="Cash">Cash / Liquidez</option>
                </select>

                <label class="input-label">Nombre del Activo</label>
                <input type="text" id="asset-name" class="modal-input" placeholder="ej: Bonos Estado Español 10A">

                <div class="modal-row">
                    <div>
                        <label class="input-label">Ticker</label>
                        <input type="text" id="asset-ticker" class="modal-input" placeholder="ej: ES10Y">
                    </div>
                    <div>
                        <label class="input-label">Plataforma</label>
                        <input type="text" id="asset-plat" class="modal-input" placeholder="ej: Tesoro / ING">
                    </div>
                </div>

                <div id="bond-fields">
                    <div class="modal-row">
                        <div>
                            <label class="input-label">Rentabilidad / Cupón Anual (%)</label>
                            <input type="number" step="0.01" id="asset-coupon" class="modal-input" placeholder="ej: 3.7">
                        </div>
                        <div>
                            <label class="input-label">Fecha de compra</label>
                            <input type="date" id="asset-bond-date" class="modal-input">
                        </div>
                    </div>
                    <small>El cupón se devenga desde esta fecha (interés simple, sin componer). Si se deja vacío, se usa hoy.</small>
                </div>

                <label class="input-label">Símbolo Yahoo Finance (opcional, solo ETFs/fondos cotizados)</label>
                <input type="text" id="asset-yahoo" class="modal-input" placeholder="ej: IBGS.MI (deuda soberana individual no tiene ticker público)">
            </div>

            <div class="modal-row">
                <div>
                    <label class="input-label" id="label-qty">Cantidad / Inversión</label>
                    <input type="number" step="any" id="manual-qty" class="modal-input" placeholder="30000">
                </div>
                <div>
                    <label class="input-label" id="label-price">Precio Unitario (€)</label>
                    <input type="number" step="any" id="manual-price" class="modal-input" placeholder="1.0">
                </div>
            </div>
            
            <div class="modal-actions">
                <button id="modal-delete" class="btn-delete hidden">Eliminar</button>
                <div class="modal-actions-right">
                    <button id="modal-cancel" class="btn-cancel">Cancelar</button>
                    <button id="modal-save" class="btn-save">Guardar</button>
                </div>
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
    const deleteBtn = document.getElementById('modal-delete');
    const modal = document.getElementById('editModal');
    const catSelect = document.getElementById('asset-cat');

    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeModal);
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', saveChanges);
    }

    if (deleteBtn) {
        deleteBtn.addEventListener('click', deleteCurrentAsset);
    }

    if (catSelect) {
        catSelect.addEventListener('change', () => {
            const bondFields = document.getElementById('bond-fields');
            if (bondFields) {
                bondFields.style.display = (catSelect.value === 'Renta Fija') ? 'block' : 'none';
            }
        });
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
 * Open modal for adding a new asset
 */
export function openAddAssetModal() {
    isCreationMode = true;
    currentAssetId = null;

    const modal = document.getElementById('editModal');
    const title = document.getElementById('modal-title');
    const subtitle = document.getElementById('modal-subtitle');
    const createFields = document.getElementById('create-fields');
    const deleteBtn = document.getElementById('modal-delete');

    const catInput = document.getElementById('asset-cat');
    const nameInput = document.getElementById('asset-name');
    const tickerInput = document.getElementById('asset-ticker');
    const platInput = document.getElementById('asset-plat');
    const couponInput = document.getElementById('asset-coupon');
    const bondDateInput = document.getElementById('asset-bond-date');
    const yahooInput = document.getElementById('asset-yahoo');
    const qtyInput = document.getElementById('manual-qty');
    const priceInput = document.getElementById('manual-price');

    if (title) title.textContent = 'Añadir Nuevo Activo';
    if (subtitle) subtitle.textContent = 'Introduce los datos del activo (Renta Fija, Acciones, Cripto, Fondos...)';
    if (createFields) createFields.classList.remove('hidden');
    if (deleteBtn) deleteBtn.classList.add('hidden');

    // Los ejemplos ("Bonos Estado Español 10A", "10YESP.BD", cupón 3.7...) viven en
    // el atributo placeholder de cada input (ver createModal()); no se ponen aquí como
    // valor real porque, si el usuario no los toca o no se da cuenta de que ya había
    // algo escrito, se guardaban como si fueran datos suyos. En particular, un símbolo
    // Yahoo real de ejemplo se enviaba sin querer, y al no tener cupón definido el precio
    // se recalculaba con la cotización de ese ticker de ejemplo, disparando el valor total.
    if (catInput) catInput.value = 'Renta Fija';
    if (nameInput) nameInput.value = '';
    if (tickerInput) tickerInput.value = '';
    if (platInput) platInput.value = '';
    if (couponInput) couponInput.value = '';
    if (bondDateInput) bondDateInput.value = '';
    if (yahooInput) yahooInput.value = '';
    if (qtyInput) qtyInput.value = '';
    if (priceInput) priceInput.value = '';

    const bondFields = document.getElementById('bond-fields');
    if (bondFields) bondFields.style.display = 'block';

    if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('visible');
    }
}

/**
 * Open modal for editing an existing asset
 */
export function openModal(assetId) {
    const asset = getAssetById(assetId);
    if (!asset) return;

    isCreationMode = false;
    currentAssetId = assetId;

    const modal = document.getElementById('editModal');
    const title = document.getElementById('modal-title');
    const subtitle = document.getElementById('modal-subtitle');
    const createFields = document.getElementById('create-fields');
    const deleteBtn = document.getElementById('modal-delete');

    const qtyInput = document.getElementById('manual-qty');
    const priceInput = document.getElementById('manual-price');

    if (title) title.textContent = `Ajuste: ${asset.name}`;
    if (subtitle) subtitle.textContent = `Edita la cantidad o precio de ${asset.name} (${asset.cat})`;
    if (createFields) createFields.classList.add('hidden');
    if (deleteBtn) deleteBtn.classList.remove('hidden');

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
    isCreationMode = false;
}

/**
 * Delete current asset
 */
async function deleteCurrentAsset() {
    if (!currentAssetId) return;
    if (!confirm('¿Estás seguro de que deseas eliminar este activo?')) return;

    await deleteAssetAPI(currentAssetId);
    closeModal();
    if (onSaveCallback) onSaveCallback();
}

/**
 * Save changes from modal
 */
async function saveChanges() {
    const qtyInput = document.getElementById('manual-qty');
    const priceInput = document.getElementById('manual-price');

    const qty = parseFloat(qtyInput?.value || 0);
    const price = parseFloat(priceInput?.value || 0);

    if (isCreationMode) {
        const cat = document.getElementById('asset-cat')?.value || 'Renta Fija';
        const name = document.getElementById('asset-name')?.value || 'Nuevo Activo';
        const ticker = document.getElementById('asset-ticker')?.value || '';
        const plat = document.getElementById('asset-plat')?.value || '';
        const coupon = parseFloat(document.getElementById('asset-coupon')?.value || 0);
        const bondStartDate = document.getElementById('asset-bond-date')?.value || null;
        const yahoo = document.getElementById('asset-yahoo')?.value || null;

        await createAssetAPI({
            name,
            ticker,
            cat,
            plat,
            qty,
            price: price > 0 ? price : 1.0,
            coupon_rate: coupon > 0 ? coupon : null,
            bond_start_date: bondStartDate || null,
            yahoo: yahoo ? yahoo.trim() : null
        });
    } else {
        if (!currentAssetId) return;
        await updateAssetAPI(currentAssetId, {
            qty,
            price,
            manual: true
        });
    }

    closeModal();

    if (onSaveCallback) {
        onSaveCallback();
    }
}

