# ECL Credit Loss

Aplicación local para estimar la **pérdida crediticia esperada (ECL)** de una cartera:

```text
ECL = PD × LGD × EAD
```

Incluye un paquete Python reproducible, una API FastAPI, procesamiento de carteras CSV en segundo plano y una interfaz Next.js para el analista.

Guía detallada de la interfaz: [USERGUIDE.md](USERGUIDE.md).

> **Aviso:** esta herramienta es analítica y educativa. No es un detector de fraude y no debe usarse para aprobar o rechazar créditos de forma automática.

## Estado

- Fases 1–4 implementadas: modelo, API, frontend, documentación y verificación local.
- Backend probado con `pytest`.
- Frontend validado con `typecheck`, `lint` y build de producción.
- Flujo E2E validado con una cartera de demostración de 1.000 créditos.

## Arquitectura

```text
data/raw/X.csv + target.csv
        │
        ▼
train.py ──► models/ecl_model.joblib + models/metadata.json
        │
        ├──► predict.py (CLI)
        │
        └──► api/main.py (FastAPI)
                    │
                    ▼
            frontend/ (Next.js)
```

| Componente | Tecnología | Puerto |
|---|---|---:|
| API | FastAPI + Uvicorn | 8000 |
| Interfaz | Next.js App Router + TypeScript | 3000 |
| Modelo | Regresión logística + WoE/IV | — |
| Persistencia local | CSV, Parquet, JSON e historial | — |

## Requisitos

- Python 3.11 o superior. Probado con Python 3.14.
- Node.js 20.9 o superior. Probado con Node.js 24.
- npm.
- Datos de entrada y artefactos del modelo, que **no se versionan** en el repositorio.

`data/raw/X.csv` y `data/raw/target.csv` son necesarios para entrenar o regenerar la muestra. Si ya existen `models/ecl_model.joblib` y `models/metadata.json`, puede ejecutar la API sin reentrenar.

## Instalación y ejecución

### 1. Backend

Desde la raíz del repositorio.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Entrenamiento reproducible:

```powershell
python train.py --seed 42 --data-dir data/raw --out-dir models
```

Generación de la muestra de demostración:

```powershell
python scripts/make_sample.py
```

El comando crea:

- `data/samples/cartera_demo.csv`
- `frontend/public/cartera_demo.csv`, usado por el botón **Usar cartera de ejemplo**

Si el directorio del frontend no existe, la segunda copia se omite. Para evitar la copia:

```powershell
python scripts/make_sample.py --skip-frontend-copy
```

Inicio de la API:

```powershell
uvicorn api.main:app --reload --port 8000
```

Comprobación:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Documentación interactiva: <http://localhost:8000/docs>

### 2. Frontend

En otra terminal:

```powershell
cd frontend
npm install
Copy-Item ..\.env.example .env.local
npm run dev
```

En Linux / macOS:

```bash
cd frontend
npm install
cp ../.env.example .env.local
npm run dev
```

Abrir <http://localhost:3000>.

La API solo permite CORS desde `http://localhost:3000`. Si cambia el puerto del frontend, actualice `api/settings.py` o la configuración correspondiente.

### 3. Variables de entorno

El archivo `.env.example` de la raíz contiene:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Debe copiarse a `frontend/.env.local`. Ese archivo está ignorado por git y no contiene secretos. Si `frontend/.env.local` no existe, el cliente usa `http://localhost:8000` como valor por defecto, pero se recomienda configurarlo explícitamente.

## Flujo de uso

1. Abrir **Cartera** y subir un CSV o pulsar **Usar cartera de ejemplo**.
2. El backend valida el esquema y genera un reporte de calidad por columna.
3. Al completarse el trabajo se muestran KPIs, gráficos y la tabla paginada.
4. La tabla permite filtrar por PD mínima, estado marcado, ordenar y descargar CSV.
5. **Crédito individual** estima PD, LGD, EAD, ECL y banda de riesgo.
6. **Modelo** muestra versión, seed, supuestos, métricas y limitaciones.
7. **Historial** lista trabajos previos y permite descargar sus resultados.

### Formato del CSV de cartera

- Una fila por crédito.
- Debe contener las 16 columnas de entrada del modelo.
- `id` es opcional; si no existe, el backend genera `credito_id`.
- No se deben incluir variables de desempeño posteriores al desembolso.
- Si faltan columnas obligatorias, el trabajo falla con un error claro; no se inventan datos.

Columnas de entrada:

```text
funded_amnt, interest_rate, loan_term_months, monthly_payment, annual_income,
dept_paym_income_ratio, issue_date_year, earliest_cr_line_year,
num_rev_trades_op_in_24mths, num_inq_in_6mths, num_inq,
num_derogatory_pub_rec, mths_since_last_installment_acc_op,
bal_to_cred_lim, max_bal_owed, used_credit_share
```

## API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado del servicio y disponibilidad del modelo |
| GET | `/model/info` | Versión, seed, métricas, supuestos, rangos y features |
| POST | `/predict` | Predicción individual o lote de hasta 1.000 créditos |
| POST | `/portfolio` | Carga CSV y encola un trabajo en segundo plano |
| GET | `/jobs/{job_id}` | Estado, progreso, totales y error del trabajo |
| GET | `/jobs/{job_id}/summary` | Agregados para los gráficos y top de créditos |
| GET | `/jobs/{job_id}/rows` | Filas paginadas con filtros y ordenamiento |
| GET | `/jobs/{job_id}/download` | Descarga del CSV de resultados |
| GET | `/history` | Historial de trabajos |

Estados de un trabajo: `queued`, `running`, `done`, `error`.

`GET /jobs/{job_id}/rows` acepta:

```text
page=1
page_size=25        # 1..200
sort_by=pd
order=desc
min_pd=0
marcado=true|false
```

`POST /predict` recibe:

```json
{
  "creditos": [
    {
      "funded_amnt": 12000,
      "interest_rate": 13.5,
      "loan_term_months": 36,
      "monthly_payment": 406.55,
      "annual_income": 65000,
      "dept_paym_income_ratio": 18.5,
      "issue_date_year": 2016,
      "earliest_cr_line_year": 2008,
      "num_rev_trades_op_in_24mths": 4,
      "num_inq_in_6mths": 1,
      "num_inq": 2,
      "num_derogatory_pub_rec": 0,
      "mths_since_last_installment_acc_op": 18,
      "bal_to_cred_lim": 42,
      "max_bal_owed": 14500,
      "used_credit_share": 38
    }
  ]
}
```

La respuesta incluye resultados por crédito, totales y advertencias.

## Modelo

- Probabilidad de default (PD) mediante regresión logística con `class_weight="balanced"`.
- Variables transformadas con WoE; selección con IV, correlación de Spearman y VIF.
- 16 columnas de entrada; 14 features de PD después de las transformaciones.
- `credit_history_length = (issue_date_year - earliest_cr_line_year).clip(lower=0)`.
- `annual_income` limitado a 1.000.000.
- Imputaciones fijas: `mths_since_last_installment_acc_op` → 999; `num_rev_trades_op_in_24mths` y `num_inq` → 0; `max_bal_owed` → mediana de train; `bal_to_cred_lim` → media de train.
- Outliers: sin capping IQR; se conservan los centinelas 999.
- Rejilla de negocio: `q = 0.10..0.40` (paso 0.01) y `s = 0.60..1.00` (paso 0.05).
- Configuración calibrada en entrenamiento: `q = 0.21`, `s = 0.95`, `criterio = "pd_por_monto"`.
- `q` y `s` se leen de `models/metadata.json`; no están hardcodeados en la API.

Métricas de test:

| Métrica | Valor |
|---|---:|
| AUC-ROC | 0.7065 |
| Gini | 0.4130 |
| KS | 0.3002 |
| ECL / ECL real | 1.9113 |
| Violaciones | 8.9662 % |
| MAE | 2950.90 |

La interpretación completa y el análisis del notebook están en `Resumen_Estimacion_ECL.md` y `DETALLE_TECNICO.md`.

## Estructura

```text
.
├── api/                     # FastAPI, schemas, settings, jobs
├── data/
│   ├── raw/                 # X.csv y target.csv (no versionados)
│   ├── samples/             # cartera_demo.csv
│   └── predictions/         # resultados de la API y CLI
├── frontend/
│   ├── public/              # cartera_demo.csv generada
│   └── src/
│       ├── app/             # páginas App Router
│       ├── components/      # layout, cartera, crédito, modelo, historial
│       └── lib/             # API, tipos, formato y metadata
├── models/                  # artefactos joblib/json (no versionados)
├── scripts/make_sample.py
├── src/ecl/                 # configuración, preprocesamiento, modelo, métricas
├── tests/
├── train.py
├── predict.py
├── requirements.txt
└── .env.example
```

## Pruebas y verificación

Backend:

```powershell
python -m pytest -q
```

Frontend:

```powershell
cd frontend
npm run lint
npm run typecheck
npm run build
```

Regenerar los tipos TypeScript después de cambiar la API:

```powershell
cd frontend
npm run generate:types
```

Verificación E2E manual:

1. Iniciar la API y el frontend.
2. Subir `data/samples/cartera_demo.csv` desde la interfaz.
3. Confirmar que aparece el reporte de calidad, los gráficos y la tabla.
4. Ejecutar la misma cartera por CLI:

```powershell
python predict.py --input data/samples/cartera_demo.csv
```

5. Comparar el ECL final y el porcentaje de marcados con los de la interfaz.
6. Confirmar que se generaron CSV, Parquet y JSON en `data/predictions/`.

Resultado de la última verificación local: 1.000 créditos, ECL final total `2.350.085,59` y `18,9 %` de créditos marcados, coincidentes entre la API y `predict.py`.

## Datos y artefactos

No se versionan datos ni artefactos:

- `data/` está ignorado.
- `models/` está ignorado.
- `frontend/public/cartera_demo.csv` está ignorado.
- `frontend/.env.local` está ignorado.

Por eso, un clon limpio necesita los CSV originales para entrenar y `python scripts/make_sample.py` para habilitar la cartera de ejemplo.

## Limitaciones

- Ejecución local; no incluye autenticación, base de datos, Docker ni despliegue cloud.
- No es un sistema de decisión crediticia ni un detector de fraude.
- El modelo se entrenó con datos históricos de Lending Club y hereda sus sesgos y limitaciones.
- La calidad de las predicciones depende de que el CSV tenga el mismo esquema y la misma semántica temporal que los datos de entrenamiento.
- Sin monitoreo de drift ni reentrenamiento automático.

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| El frontend no conecta con la API | API detenida o URL incorrecta | Verificar `http://localhost:8000/health` y `frontend/.env.local` |
| El botón de ejemplo devuelve 404 | Falta la muestra pública | Ejecutar `python scripts/make_sample.py` |
| Error al importar el modelo | Faltan artefactos en `models/` | Ejecutar `python train.py` con los datos disponibles |
| Error de CORS | Frontend en otro puerto | Usar el puerto 3000 o ajustar CORS en `api/settings.py` |
| Cambió un contrato de la API | Tipos TypeScript desactualizados | Ejecutar `npm run generate:types` |
| Faltan columnas en la carga | CSV no cumple el esquema | Revisar el reporte de calidad y las 16 columnas requeridas |
