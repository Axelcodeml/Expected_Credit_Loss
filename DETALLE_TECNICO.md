# ECL_Credit_Loss

Modelo de **Expected Credit Loss (ECL)** sobre un dataset crediticio de ~2.1 millones de registros. El objetivo es predecir la variable binaria `y` (default / morosidad) con **regresión logística** sobre variables transformadas con **WoE (Weight of Evidence)**, dejando el feature engineering estructurado como clases `fit/transform` listas para un futuro despliegue MLOps.

---

## 1. Estado actual del proyecto

| Fase | Estado |
|---|---|
| Limpieza e imputación de nulos | Hecho |
| Tratamiento de outliers (EDA) | Hecho |
| Pruebas de hipótesis (ANOVA, chi-cuadrado, correlación) | Hecho |
| Cálculo de IV y filtrado de variables | Hecho |
| Correlación (Spearman) y VIF | Hecho |
| Feature engineering (variables derivadas y flags) | Hecho |
| Split train/test | Hecho |
| `WOEEncoder` + `PreprocesadorECL` | Definidos (al final del notebook) |
| Entrenamiento de regresión logística | Siguiente paso |
| Evaluación (AUC, KS, Gini) y calibración a PD/ECL | Pendiente |
| MLOps (empaquetado, despliegue, monitoreo) | Pendiente |

---

## 2. Dataset

- **Filas totales:** 2,139,643
- **Variable objetivo:** `y` (binaria), ~**13%** de tasa positiva (dataset desbalanceado).
- **Tipo de variables:** financieras, de historial crediticio y de morosidad (`funded_amnt`, `interest_rate`, `num_30+_delinq_in_2yrs`, `annual_income`, `loan_term_months`, `region_code`, etc.).
- **Supuesto temporal:** las variables tipo `_6mths`, `_12mths`, `_24mths` se miden **hacia atrás desde la fecha de originación** del crédito (`issued_date_month` / `issued_date_year`), no desde la fecha de extracción de los datos.

### Split train / test

| Conjunto | Filas | Tasa de default |
|---|---|---|
| Train | 1,711,714 | ~13.07% |
| Test | 427,929 | ~13.07% |

- Split **aleatorio estratificado por `y`** (`test_size=0.2`, `random_state=42`). No es un split temporal.
- `train_df` ya tiene aplicado el tratamiento previo (limpieza/outliers). `test_df` se mantiene **crudo** y recibe las transformaciones únicamente a través del preprocesador.

---

## 3. Transformaciones realizadas

### 3.1 Tratamiento de valores nulos

**Variables numéricas → imputación por la media**

Se reemplazaron los NaN por la media de cada columna tras estudiar sus distribuciones. Se eligió media y no mediana porque la mediana daba 0 en varias de estas columnas.

Columnas imputadas:

- `mths_since_last_delinq`
- `num_open_trades_in_6mths`
- `num_installment_acc_op_in_12mths`
- `num_installment_acc_op_in_24mths`
- `mths_since_last_installment_acc_op`
- `num_rev_trades_op_in_12mths`
- `num_rev_trades_op_in_24mths`
- `max_bal_owed`
- `bal_to_cred_lim`
- `num_inq`
- `mths_since_recent_bankcard_delinq`
- `mths_since_recent_revol_delinq`

**Variables categóricas → imputación por la moda**

- `emp_title`
- `emp_length`

### 3.2 Flags de "nunca ocurrió"

Los NaN en las variables `mths_since_*` suelen significar que el evento nunca ocurrió. Para no perder esa información al imputar con la media, se crearon indicadores binarios:

| Flag | Significado |
|---|---|
| `nunca_delinq` | Nunca tuvo morosidad |
| `nunca_last_install` | Nunca tuvo cuenta a plazos reciente |
| `nunca_last_bankcard_delinq` | Nunca tuvo morosidad en tarjeta bancaria |
| `nunca_last_revol_delinq` | Nunca tuvo morosidad en crédito revolvente |
| `flag_sin_empleo` | Sin información de empleo |

### 3.3 Variables derivadas

- **`emp_length_num`**: codificación ordinal de `emp_length` (0–10 años).
- **`credit_history_length`**: `issue_date_year - earliest_cr_line_year`. Sin valores negativos, rango 0–83.

### 3.4 Tratamiento de outliers

Se definió por variable, según la severidad:

- **Winsorización 5%–95%** para outliers moderados.
- **Capping por 1.5 × IQR** para outliers muy lejanos.

---

## 4. Selección de variables

### 4.1 Pruebas de hipótesis

- Numérico–numérico: correlación.
- Categórico–numérico: ANOVA.
- Categórico–categórico: chi-cuadrado.

### 4.2 Information Value (IV)

Criterio: se eliminan las variables con **IV < 0.01**.

Variables que quedaron (entre otras):

| Variable | IV |
|---|---|
| `interest_rate` | 0.45 |
| `mths_since_last_installment_acc_op` | 0.11 |
| `bal_to_cred_lim` | 0.10 |
| `nunca_last_install` | 0.09 |
| `max_bal_owed` | 0.08 |
| `annual_income` | 0.036 |
| `funded_amnt` | 0.02 |

IV de las variables evaluadas después:

| Variable | IV | Lectura |
|---|---|---|
| `region_code` | 0.0031 | Débil |
| `loan_term_months` | 0.0730 | Medio |
| `emp_length_num` | 0.0043 | Débil |
| `credit_history_length` | 0.0107 | Al límite del umbral |

### 4.3 Multicolinealidad

- **Spearman > 0.7:** entre cada par altamente correlacionado se eliminó la variable con menor IV.
  - Eliminadas: `nunca_last_install`, `num_installment_acc_op_in_24mths`, `num_rev_trades_op_in_12mths`, `funded_amnt`.
- **VIF:** máximo de **1.97** en el set final (sin problemas de colinealidad).

### 4.4 Set final: 15 variables

13 variables originales que sobrevivieron al filtro de IV y correlación (incluyendo `mths_since_last_installment_acc_op` y `num_open_trades_in_6mths`), más:

- `loan_term_months`
- `credit_history_length`

> Completar aquí la lista nominal de las 15 variables tal como queda en el notebook.

---

## 5. WOEEncoder (encoder general para train y test)

Encoder de **Weight of Evidence** pensado para ajustarse **solo con train** y aplicarse igual a train y test, evitando fuga de información (data leakage).

**Idea general**

1. `fit(X_train, y_train)`: para cada variable, agrupa en bins (numéricas) o categorías, y calcula el WoE de cada grupo:

   ```
   WoE = ln( %no_default_en_grupo / %default_en_grupo )
   ```

2. `transform(X)`: reemplaza cada valor por el WoE de su grupo, usando **siempre** las tablas aprendidas en `fit`.
3. Categorías o rangos no vistos en train deben recibir un valor por defecto (por ejemplo WoE = 0) en lugar de generar error.

**Decisión de diseño**

- El `WOEEncoder` original se **dejó sin modificar**.
- La versión corregida del encoder se usa dentro de `PreprocesadorECL` (sección siguiente), definida al final del notebook.

**Por qué WoE + regresión logística**

- Relación monótona y lineal con el log-odds, ideal para regresión logística.
- Maneja nulos, outliers y categóricas de forma uniforme.
- Resultado interpretable y compatible con scorecards de riesgo crediticio.

---

## 6. PreprocesadorECL (base para MLOps)

Clase con interfaz `fit` / `transform` que encapsula **todo** el feature engineering para que el mismo código corra en entrenamiento y en producción.

**Responsabilidades**

| Paso | Qué hace | ¿Se aprende en `fit`? |
|---|---|---|
| Imputación numérica | Media por columna | Sí (medias de train) |
| Imputación categórica | Moda por columna | Sí (modas de train) |
| Flags `nunca_*` y `flag_sin_empleo` | Crea indicadores de ausencia de evento | No (reglas fijas, se calculan **antes** de imputar) |
| Variables derivadas | `emp_length_num`, `credit_history_length` | No (reglas fijas) |
| Outliers | Winsorización 5–95% / cap 1.5×IQR | Sí (límites de train) |
| Selección de variables | Conserva las 15 variables finales | No (lista fija) |
| WoE encoding | Aplica el `WOEEncoder` corregido | Sí (tablas WoE de train) |

**Flujo de uso**

```python
pre = PreprocesadorECL()
pre.fit(train_df)                      # aprende medias, modas, límites y tablas WoE solo con train

X_train = pre.transform(train_df)
X_test  = pre.transform(test_df)       # test_df crudo: recibe exactamente las mismas transformaciones
```

**Reglas importantes**

- Todo parámetro estadístico (medias, modas, percentiles, WoE) se calcula **solo con train**.
- El orden importa: los flags `nunca_*` se crean **antes** de imputar, porque dependen de qué valores eran nulos.
- `test_df` nunca se usa para ajustar nada.

**Camino hacia MLOps**

- Serializar el preprocesador entrenado (`joblib` / `pickle`) junto con el modelo en un único artefacto o `Pipeline`.
- Validar el esquema de entrada (columnas, tipos, rangos) antes de `transform`.
- Versionar datos, preprocesador y modelo.
- Monitorear drift de variables (PSI) y desempeño del modelo en producción.
- Evaluación en curso: ejecutar el ciclo completo en **AWS SageMaker** (con Amazon Q Developer) y comparar con **Azure Machine Learning**.

---

## 7. Próximos pasos

1. Aplicar `PreprocesadorECL` a train y test.
2. Entrenar la **regresión logística** (considerar `class_weight` por el desbalance de ~13%).
3. Evaluar con AUC-ROC, KS y Gini, además de matriz de confusión con umbral ajustado.
4. Convertir probabilidades en **PD**, y de ahí al cálculo de **ECL = PD × LGD × EAD**.
5. Empaquetar preprocesador y modelo, y definir el pipeline de despliegue y monitoreo.

---

## 8. Estructura sugerida del repositorio

```
ECL_Credit_Loss/
├── README.md
├── notebooks/
│   └── ECL_Credit_Loss.ipynb
├── src/
│   ├── woe_encoder.py
│   └── preprocesador_ecl.py
├── models/
│   └── (artefactos serializados)
└── requirements.txt
```