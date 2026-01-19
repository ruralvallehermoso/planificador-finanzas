## Portfolio Master App (FastAPI + SQLite)

Aplicación nueva que replica la funcionalidad principal de `Finanzas.html`
pero con una arquitectura más limpia:

- Backend moderno con **FastAPI** y **SQLite** (almacenamiento de activos).
- Frontend basado en **Vite** y **JavaScript** modular.
- Actualización de precios vía **Yahoo Finance**, **CoinGecko** e **Indexa Capital** (integrado directamente en el backend).

### 1. Requisitos

- Python 3.10+ recomendado.
- Conexión a internet para las APIs de mercado.
- Token de Indexa Capital configurado en el Keychain de macOS (ejecutar `python3 setup_indexa_token.py`).


Instalar dependencias:

```bash
cd /Users/ct/PERSONAL/Proyectos/Finanzas
python -m venv .venv
source .venv/bin/activate  # En macOS / Linux
pip install -r requirements.txt
```

### 2. Ejecutar el backend

```bash
uvicorn backend.main:get_app --reload
```

Por defecto se levantará en `http://127.0.0.1:8000`.

### 3. Uso de la aplicación

- Abre en el navegador: `http://127.0.0.1:8000/`
- Verás:
  - Tabla de activos con filtros **TODO / CRIPTO / ACCIONES / FONDOS**.
  - Total de patrimonio, conteo de activos y ratio **USD**.
  - Gráfico doughnut con distribución.
  - Panel de **Top Movers**.
  - Modal de edición manual (cantidad y precio) que se guarda en la BBDD.

La primera vez, la base de datos `portfolio.db` se rellena automáticamente
con un conjunto de activos equivalente a los del `Finanzas.html` original
(lista reducida pero fácilmente ampliable en `backend/seed_data.py`).

### 4. Actualización de mercados

- El botón de refresco llama a `POST /api/markets/update`:
  - Descarga cotizaciones de **Yahoo Finance** (acciones y fondos).
  - Descarga precios de **CoinGecko** (cripto).
  - Consulta el proxy de **Indexa** si está disponible.
- Los nuevos precios se guardan en SQLite y se recarga la tabla y el gráfico.

### 5. Estructura de carpetas

- `backend/`
  - `database.py` – conexión SQLite y sesión.
  - `models.py` – modelo `Asset`.
  - `schemas.py` – esquemas Pydantic.
  - `crud.py` – operaciones de BBDD.
  - `seed_data.py` – datos iniciales.
  - `market_client.py` – clientes Yahoo/CoinGecko/Indexa.
  - `main.py` – app FastAPI y rutas.
- `frontend/`
  - `templates/index.html` – página principal.
  - `static/js/app.js` – lógica de UI (tabla, filtros, gráfico, modal).

### 6. Notas

- Puedes seguir usando `Finanzas.html` como antes; la nueva app no lo modifica.
- Si quieres añadir más activos al seeding, edita `backend/seed_data.py`.


