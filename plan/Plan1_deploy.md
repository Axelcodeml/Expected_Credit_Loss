# PROMPT

## 1. Rol y objetivo

Eres un ingeniero senior de ML y de software. Vas a convertir el notebook del proyecto de estimación de pérdida esperada (ECL) en un servicio que corra **en local**, formado por:

1. Un paquete Python con el pipeline de preprocesamiento y el modelo, extraídos del notebook.
2. Una API REST con FastAPI que sirve el modelo.
3. Una interfaz web en **Next.js (TypeScript)** para el usuario final: un **analista de cartera de un banco**.

Los resultados de predicción se guardan en la carpeta `data/`.

## 2. Contexto del modelo (no lo modifiques)

El modelo estima la pérdida esperada de cada crédito y de la cartera:

```
ECL_j = PD_j × LGD_j × EAD_j        ECL de la cartera = Σ_j ECL_j
```

- **PD:** regresión logística sin penalización sobre 14 variables transformadas a WoE. Preprocesamiento en la clase `PreprocesadorECL` y codificación en `WOEEncoderV2`.
- **EAD:** regresión lineal sobre la fracción `EAD / funded_amnt`. **LGD:** regresión lineal. Ambas se entrenan solo con defaulters de train.
- **ECL calibrado** = `PD × LGD × EAD`. Es la estimación central y honesta.
- **ECL con margen de conservadurismo** (clase `ModeloECL`): se marca a los créditos con mayor `PD / funded_amnt` (fracción **q** de la cartera) y a los marcados se les asigna `máx(ECL calibrado, s × funded_amnt)`. Los valores de q y s se aprenden en el entrenamiento con una búsqueda en rejilla. En el notebook salieron q = 0.21 y s = 0.95.
- **Pérdida real, definición A** (función `construir_reales`): `EAD_real = máx(0, F − P)`, `Recuperado = máx(0, T − (P + I + L))`, `LGD_real = 1 − Recuperado / EAD_real`, `ECL_real = y × EAD_real × LGD_real`. Solo se usa para entrenar y evaluar. Nunca se necesita para predecir.
- **Todo se aprende con train.** La inferencia nunca recalcula medianas, medias, bins, WoE, cortes ni q y s sobre los datos nuevos.

## 3. Reglas generales

- **No cambies la lógica numérica** (bins, imputaciones, WoE, regresiones, búsqueda de q y s, definiciones). Las únicas modificaciones permitidas son las que se listan en este prompt. Si crees que algo debe cambiar, **pregunta antes**.
- **No modifiques el notebook original.**
- Si encuentras varias versiones de una clase o función en el notebook, usa la **más reciente por orden de ejecución** (por ejemplo `WOEEncoderV2` y no `WOEEncoder`). Si hay ambigüedad, pregunta.
- **No incluyas datos en el repositorio.** Crea un `.gitignore` que excluya `data/`, `models/` y `node_modules/`.
- Usa las **mismas versiones de librerías del entorno del notebook** (revisa con `pip freeze | grep -E "scikit-learn|pandas|numpy|statsmodels|joblib"`) y fíjalas en `requirements.txt`.
- Código con type hints, docstrings en español y nombres consistentes con el notebook.
- **Trabaja por fases.** Al terminar cada una, resume lo hecho, muestra cómo verificarlo y **espera confirmación**.

## 4. Estructura objetivo

```
Expected_Credit_Loss/
├── data/
│   ├── raw/                  # X.csv y target.csv (entrada de entrenamiento, no se versiona)
│   ├── samples/              # cartera de ejemplo para la demo
│   └── predictions/          # resultados de predicción (CSV, Parquet y resumen JSON)
├── models/                   # ecl_model.joblib y metadata.json (no se versiona)
├── src/ecl/
│   ├── __init__.py
│   ├── config.py             # SEED, rutas, rejilla de q y s, colchones, constantes
│   ├── preprocessing.py      # WOEEncoderV2 y PreprocesadorECL
│   ├── model.py              # ModeloECL, construir_reales, FEATS_EAD_LGD
│   └── evaluation.py         # restricciones del reto y métricas
├── train.py                  # entrena con SEED y guarda artefacto y metadatos
├── predict.py                # predice una cartera y guarda en data/predictions/
├── api/
│   ├── main.py
│   ├── schemas.py
│   └── jobs.py
├── scripts/make_sample.py    # genera data/samples/cartera_demo.csv
├── tests/
├── frontend/                 # Next.js
├── requirements.txt
├── .env.example
└── README.md
```

## 5. Fase 0 — Reconocimiento (no escribas código todavía)

1. Lee el notebook completo.
2. Entrega una tabla que mapee cada pieza a extraer con su archivo de destino: `WOEEncoderV2`, `PreprocesadorECL`, `ModeloECL`, `construir_reales`, `FEATS_EAD_LGD`, `verificar_restricciones`, `robustez_bootstrap` y el cálculo de métricas de `evaluar_seed`.
3. Indica el código de carga de datos de las primeras celdas (nombres de columnas, tipos, cualquier renombrado) y cómo lo replicarás.
4. Lista ambigüedades, versiones duplicadas y dependencias ocultas (por ejemplo, variables globales usadas dentro de las clases).
5. **Detente y espera confirmación.**

## 6. Fase 1 — Extracción del pipeline y del modelo

### 6.1 `src/ecl/preprocessing.py`

Extrae `WOEEncoderV2` y `PreprocesadorECL` con estas modificaciones obligatorias:

- **Elimina toda referencia a `num_open_trades_in_6mths`.** Es una variable descartada del modelo y no debe ser requerida en la entrada. Quítala de `variables_bins` y de `_features_fijas`.
- **Haz configurable el tope de ingresos** (`tope_ingresos`, por defecto `1_000_000`, igual que el notebook) y guárdalo como atributo del objeto.
- Añade `COLUMNAS_ENTRADA` con las 16 columnas requeridas para predecir:

```
funded_amnt, interest_rate, loan_term_months, monthly_payment, annual_income,
dept_paym_income_ratio, issue_date_year, earliest_cr_line_year,
num_rev_trades_op_in_24mths, num_inq_in_6mths, num_inq, num_derogatory_pub_rec,
mths_since_last_installment_acc_op, bal_to_cred_lim, max_bal_owed, used_credit_share
```

- Define `COLUMNAS_NULABLES` (solo estas admiten valores faltantes): `mths_since_last_installment_acc_op` (se imputa 999), `num_rev_trades_op_in_24mths` y `num_inq` (se imputan 0), `max_bal_owed` (mediana de train) y `bal_to_cred_lim` (media de train). El resto debe venir completo.
- Añade `validar_entrada(df)`, que lance un error claro si falta alguna columna requerida o si hay valores faltantes en columnas no nulables.
- La inferencia debe funcionar **sin** las columnas `y` ni las de desempeño (`princ_rec`, `interest_rec`, `late_fees_rec`, `paym_rec_for_tot_amnt_fund`, `remaining_princ_for_tot_amnt_fund`).

### 6.2 `src/ecl/model.py`

Extrae `ModeloECL`, `construir_reales` y `FEATS_EAD_LGD`. Añade, sin alterar la lógica existente:

- `guardar(ruta)` y `cargar(ruta)` con `joblib`.
- `predecir(df)`, que devuelva un DataFrame con: `pd`, `lgd`, `ead`, `ecl_calibrado`, `ecl_final`, `marcado` y `banda_riesgo`.
- **Bandas de riesgo:** durante `fit`, calcula los cortes de decil de la PD **con train**, guárdalos en el objeto y úsalos para asignar `banda_riesgo` (1 a 10) a cualquier crédito.
- `contribuciones(df)`: para cada crédito, la contribución de cada variable al logit (`coeficiente × WoE`), para poder mostrar los 3 principales factores de riesgo en la vista individual.

### 6.3 `src/ecl/evaluation.py`

Extrae `verificar_restricciones` y `robustez_bootstrap`. Añade `metricas_holdout(...)` con:

- PD: AUC, Gini, KS.
- ECL: ECL total, ECL final / ECL real, **violaciones (%)**, R1 y R2 cumplidas, MAE, **WAPE**, MAPE y APE mediano. El MAPE usa **solo créditos con pérdida real ≥ 1 dólar**.
- Grupo marcado frente a default: matriz de confusión (TN, FP, FN, TP), recall, precisión, especificidad, exactitud y lift.

### 6.4 `src/ecl/config.py`

Concentra: `SEED` (por defecto 42), rutas, rejilla (q de 0.10 a 0.40 en pasos de 0.01; s de 0.60 a 1.00 en pasos de 0.05), `obj_viol = 0.09`, `obj_r1 = 1.02`, `criterio = "pd_por_monto"`. **q y s no se escriben en el código:** se aprenden en `fit`.

### 6.5 `train.py`

CLI: `python train.py --seed 42 --data-dir data/raw --out-dir models`.

1. Carga `X.csv` y `target.csv` (replicando el código del notebook).
2. Parte 80/20 estratificado por `y` con `random_state = SEED`.
3. Ajusta `ModeloECL` **solo con train** (sin excluir filas).
4. Evalúa en el 20% de test con `metricas_holdout`.
5. Guarda `models/ecl_model.joblib` y `models/metadata.json` con: seed, fecha, versiones de librerías, q, s, cortes de bandas, columnas de entrada, tamaños de train y test, y todas las métricas.

### 6.6 `predict.py`

CLI: `python predict.py --input data/samples/cartera_demo.csv --output-dir data/predictions`.

- Carga el artefacto, valida, predice y **guarda en `data/predictions/`**:
  - `ecl_<timestamp>.csv` y `ecl_<timestamp>.parquet` (identificador, `funded_amnt` y todas las salidas),
  - `ecl_<timestamp>_resumen.json` (totales y versión del modelo).
- Implementa la lógica en **una sola función** `predecir_cartera(df, modelo)` que reutilizará la API. No dupliques código.

### 6.7 Pruebas (`tests/`, con `pytest`)

- El preprocesador acepta los valores faltantes permitidos y **no exige `num_open_trades_in_6mths`**.
- `validar_entrada` falla con mensajes claros cuando falta una columna.
- La inferencia no necesita `y` ni variables de desempeño.
- Las salidas cumplen: `pd` en [0, 1], `lgd` en [0, 1], `ead ≥ 0`, `ecl_final ≥ ecl_calibrado`.
- Reproducibilidad (ver abajo).

### 6.8 Criterio de reproducibilidad (obligatorio antes de pasar a la Fase 2)

Con `SEED = 42` y los mismos datos, `train.py` debe reproducir las cifras del notebook, con una tolerancia de ±1%:

| Cifra | Valor del notebook |
|---|---|
| q / s elegidos | 0.21 / 0.95 |
| ECL final / ECL real | ≈ 1.911 |
| Violaciones (definición A) | ≈ 8.97% |
| MAE | ≈ 2,951 |

Si no coinciden, **detente, explica la causa y no continúes.**

**Detente aquí y espera confirmación.**

## 7. Fase 2 — API REST (FastAPI)

- Carga el artefacto **una sola vez** al iniciar (lifespan). Valida con Pydantic. Habilita CORS para `http://localhost:3000`.
- Esquema de entrada `LoanInput`: las 16 columnas de `COLUMNAS_ENTRADA` más un `id` opcional. `loan_term_months` solo admite 36 o 60. Los campos nulables aceptan `null`. Advierte (sin rechazar) cuando un valor cae fuera del rango visto en entrenamiento.

| Método y ruta | Función |
|---|---|
| `GET /health` | Estado del servicio y versión del modelo |
| `GET /model/info` | Contenido de `metadata.json` más los textos de supuestos y límites |
| `POST /predict` | Lista de créditos (máximo 1,000) → resultados por crédito (con `contribuciones`) y totales |
| `POST /portfolio` | Recibe un CSV (multipart). Guarda el archivo en disco por streaming, procesa en **segundo plano** y devuelve `job_id` |
| `GET /jobs/{id}` | Estado: `queued`, `running`, `done` o `error`, con mensaje y reporte de calidad de datos |
| `GET /jobs/{id}/summary` | Agregados para gráficos (ver abajo) |
| `GET /jobs/{id}/rows` | Filas paginadas: `page`, `page_size`, `sort_by`, `order`, `min_pd`, `marcado` |
| `GET /jobs/{id}/download` | CSV completo |
| `GET /history` | Corridas guardadas en `data/predictions/` (se reconstruye desde disco al reiniciar) |

- **Salida por crédito:** `id`, `pd`, `lgd`, `ead`, `ecl_calibrado`, `ecl_final`, `marcado`, `banda_riesgo`.
- **Totales:** `n`, `exposicion_total` (suma de `funded_amnt`), `ecl_calibrado_total`, `ecl_final_total`, `ratio_final_calibrado`, `pct_marcados`, `pd_media`.
- **Agregados de `summary`:** histograma de la PD; por decil de riesgo (n, PD media, ECL calibrado, ECL final); por plazo (36 y 60); por año de originación; y los 20 créditos con mayor `ecl_final`.
- **Reporte de calidad de datos:** filas leídas, columnas faltantes, valores faltantes por columna, valores fuera de rango e identificadores duplicados.
- Persiste cada corrida en `data/predictions/` (Parquet para paginar rápido, CSV para exportar y JSON de resumen). Usa `pyarrow`.
- Las columnas extra del CSV se ignoran. Si el CSV trae `y` o variables de desempeño, también se ignoran en esta versión.
- Los errores devuelven 422 con mensajes que indiquen exactamente qué columna o qué valor falla.

**Detente aquí y espera confirmación.**

## 8. Fase 3 — Interfaz web (Next.js)

**Stack:** Next.js (App Router) con TypeScript estricto, Tailwind CSS, shadcn/ui, Recharts y TanStack Query. Genera los tipos del cliente a partir de `http://localhost:8000/openapi.json` con `openapi-typescript`; **no inventes endpoints ni campos**. Configura la URL del API con `NEXT_PUBLIC_API_URL`. El navegador debe llamar **directo a FastAPI** (no a través de rutas de Next.js) para evitar límites de tamaño en cargas grandes.

**Usuario:** analista de cartera de un banco. Interfaz en español, sobria y profesional, montos en dólares con formato `Intl`, primero escritorio y adaptable.

### Páginas

1. **`/` — Cartera**
   - Carga de CSV (arrastrar y soltar) con progreso por `job_id`, y botón "usar cartera de ejemplo".
   - Reporte de calidad de datos antes de mostrar resultados.
   - KPIs: número de créditos, exposición total, **ECL calibrado**, **ECL con margen**, relación entre ambos, % de créditos marcados y PD media.
   - Gráficos: histograma de PD, ECL por decil de riesgo, ECL por plazo y por año de originación.
   - Tabla de créditos con paginación en servidor, orden y filtros (PD mínima, marcados). Botón para descargar el CSV.
2. **`/credito` — Crédito individual:** formulario con los 16 campos y validación. Muestra PD, LGD, EAD, ambos ECL y los **3 principales factores de riesgo** (contribuciones).
3. **`/modelo` — Modelo:** descripción, fórmulas, parámetros q y s leídos de `metadata.json`, métricas de validación, supuestos y límites.
4. **`/historial`:** corridas anteriores guardadas en `data/predictions/`, con descarga.

Incluye estados de carga, error y vacío, y el pie de página con la versión del modelo y la semilla.

### Textos obligatorios en la interfaz

- **Aviso fijo:** "Estimación a nivel de cartera. No es un detector de fraude ni debe usarse para aprobar o rechazar créditos individuales."
- **Tooltip del ECL calibrado:** "Estimación central de la pérdida esperada: PD × LGD × EAD."
- **Tooltip del ECL con margen:** "Suma un margen de conservadurismo a los créditos de mayor riesgo. Sus parámetros (q y s) se calibraron para cumplir las restricciones del reto y no son un parámetro regulatorio."
- **En `/modelo`, supuestos y límites:**
  - Definición A de pérdida real (los intereses cobrados no restan pérdida).
  - ECL real = 0 para créditos sin default (supuesto sin confirmar con el organizador).
  - La recuperación se infere como residuo de los pagos.
  - Validación con particiones aleatorias del mismo conjunto, por lo que el desempeño en otra época puede ser peor.
  - El PD discrimina de forma moderada (poder predictivo limitado).

**Detente aquí y espera confirmación.**

## 9. Fase 4 — Integración local y documentación

- `scripts/make_sample.py`: genera `data/samples/cartera_demo.csv` con ~1,000 créditos tomados de `data/raw/`, solo con las 16 columnas de entrada.
- `README.md` con los pasos exactos:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python train.py --seed 42 --data-dir data/raw --out-dir models
python scripts/make_sample.py
uvicorn api.main:app --reload --port 8000

# en otra terminal
cd frontend && npm install && npm run dev      # http://localhost:3000
```

- `.env.example` con `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- Prueba de extremo a extremo: sube `cartera_demo.csv` desde la interfaz, confirma que se genera el archivo en `data/predictions/` y que los totales coinciden con los que entrega `predict.py` por línea de comandos.

## 10. Criterios de aceptación

- [ ] `preprocessing.py` y `model.py` existen y el notebook original no se tocó.
- [ ] La inferencia **no** requiere `num_open_trades_in_6mths`, `y` ni variables de desempeño.
- [ ] Reproducibilidad con `SEED = 42` dentro de ±1% (sección 6.8).
- [ ] `pytest` pasa sin fallos.
- [ ] `predict.py` y la API guardan sus resultados en `data/predictions/`.
- [ ] Una cartera de ~430 mil filas se procesa sin que la interfaz se congele (procesamiento en segundo plano, tabla paginada en servidor).
- [ ] La interfaz muestra los dos ECL, el aviso fijo y los supuestos del modelo.
- [ ] No hay datos ni artefactos en el repositorio (`.gitignore` correcto).
- [ ] Todo corre en local con los comandos del README.

## 11. Lo que NO debes hacer

- No reajustes ni recalcules nada del modelo al hacer inferencia.
- No fijes q y s en el código ni cambies sus rejillas.
- No cambies la definición A ni ninguna fórmula.
- No presentes el modelo como detector de fraude en ningún texto.
- No añadas autenticación, base de datos externa ni servicios en la nube en esta versión.
- No inventes datos para completar columnas faltantes: devuelve un error claro.

## 12. Fase 5 — Opcional, no implementar ahora (deja la estructura lista)

- **MLflow:** bandera `--mlflow` en `train.py` para registrar parámetros, métricas y el modelo.
- **Docker y `docker-compose`** para API y frontend.
- **GitHub Actions:** lint, `pytest`, construcción de imágenes y una puerta de calidad que bloquee el despliegue si el modelo incumple R1 o R2.
- **Modo evaluación** (`POST /evaluate`) para CSV que incluyan `y` y las variables de desempeño: calcula la pérdida real (definición A) y las restricciones, WAPE, MAE y MAPE.
- **Reentrenamiento con el 100% de los datos** (`--full`) con q y s recalculados, indicando que las métricas dejan de ser fuera de muestra.

## 13. Si algo es ambiguo

Pregunta antes de decidir. Si debes elegir entre fidelidad al notebook y una mejora, **elige fidelidad al notebook** y deja la mejora anotada en el `README`.
