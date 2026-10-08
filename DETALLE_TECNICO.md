# ECL_Credit_Loss

Modelo de **probabilidad de default (PD)**, componente central del cálculo de **Expected Credit Loss (ECL)**, sobre el dataset público *Lending Club* (~2.1 millones de créditos). Se usa **regresión logística** sobre variables transformadas con **WoE (Weight of Evidence)**, y el feature engineering queda encapsulado en clases `fit/transform` listas para un futuro despliegue MLOps.

- **Dataset:** [Lending Club Loan Data (cleared)](https://www.kaggle.com/datasets/db0boy/lending-club-loan-data-cleared/data), archivos `X.csv` y `target.csv`.
- **Notebook:** `ECL_Notebook.ipynb`

---

## 1. Estado actual del proyecto

| Fase | Estado |
|---|---|
| Carga de datos y split estratificado | Hecho |
| Tratamiento de valores faltantes | Hecho |
| Tratamiento de outliers | Hecho |
| EDA de variables numéricas vs. `y` | Hecho |
| Cálculo de WoE / IV y filtrado de variables | Hecho |
| Correlación de Spearman y VIF | Hecho |
| `WOEEncoderV2` + `PreprocesadorECL` | Hecho |
| Entrenamiento de regresión logística | Hecho |
| Evaluación (AUC, Gini, KS) y AUC por año de emisión | Hecho |
| Calibración de PD y cálculo de ECL (PD × LGD × EAD) | Pendiente |
| MLOps (empaquetado, despliegue, monitoreo) | Pendiente |

---

## 2. Dataset

- **Filas totales:** 2,139,643
- **Variable objetivo:** `y` (binaria), ~**13%** de casos positivos (dataset desbalanceado).
- **Variables con valores faltantes:** `emp_title` y `emp_length` (~6.9%) y un grupo de variables `num_*`, `mths_*`, `max_bal_owed`, `bal_to_cred_lim`.
- **Supuesto temporal:** las variables `_6mths`, `_12mths`, `_24mths` se miden hacia atrás desde la **fecha de originación** del crédito.

### Split train / test

| Conjunto | Filas | Tasa de default |
|---|---|---|
| Train | 1,711,714 | 13.073% |
| Test | 427,929 | 13.073% |

- `train_test_split(test_size=0.2, random_state=42, stratify=y)`. Es un split **aleatorio estratificado**, no temporal.
- El split se hace **antes** de cualquier transformación para evitar *data leakage*. Todo el tratamiento exploratorio se hace sobre `X_train`; `X_test` se transforma después, solo con el preprocesador.

---

## 3. Tratamiento de valores faltantes

El criterio general fue **no inventar actividad** que probablemente nunca ocurrió: para variables que cuentan eventos, un nulo se interpreta como "no hubo actividad".

### 3.1 Variables `mths_since_*`: flag + valor centinela 999

Un nulo significa que el evento **nunca ocurrió**. Se crea un flag binario y se rellena con un **centinela de 999 meses** (si nunca ocurrió, equivale a "ocurrió hace muchísimo tiempo"). Imputar con la media habría generado meses de incidencia falsos y afectado al modelo.

| Variable original | Flag creado |
|---|---|
| `mths_since_last_delinq` | `nunca_delinq` |
| `mths_since_last_installment_acc_op` | `nunca_last_install` |
| `mths_since_recent_bankcard_delinq` | `nunca_last_bankcard_delinq` |
| `mths_since_recent_revol_delinq` | `nunca_last_revol_delinq` |

Estas variables **no se recortan** (outliers) para conservar el valor centinela. En el EDA se comprobó que el 999 de `mths_since_recent_bankcard_delinq` concentra ~87% de `y=0`, lo que corrige la lectura engañosa del boxplot.

### 3.2 Variables de conteo `num_*`: imputación con **0**

Se imputan con **0**, no con la media: es más razonable suponer que **nunca hubo actividad** (no se abrieron cuentas ni hubo consultas) que asignar un valor medio, que implicaría actividad y debilitaría la relación del coeficiente con el target.

- `num_open_trades_in_6mths`
- `num_installment_acc_op_in_12mths`
- `num_installment_acc_op_in_24mths`
- `num_rev_trades_op_in_12mths`
- `num_rev_trades_op_in_24mths`
- `num_inq`

### 3.3 Variables de saldo: mediana y media

| Variable | Imputación | Motivo |
|---|---|---|
| `max_bal_owed` | **Mediana** | Distribución más asimétrica |
| `bal_to_cred_lim` | **Media** | Distribución más simétrica |

### 3.4 Variables de empleo

- `emp_title`: se crea el flag `sin_emp_title` (nulo = posible desempleo, no se imputa con la moda) y se elimina la columna original.
- `emp_length`: se convierte a numérica `emp_length_num` (`'10+ years'`→10 … `'1 year'`→1, `'< 1 year'`→0.5) con los nulos en 0, y se elimina la columna original.

---

## 4. Tratamiento de outliers

El tratamiento se decidió por grupo de variables, mediante boxplots:

| Grupo | Decisión |
|---|---|
| `mths_since_*` (centinela 999) | **Sin modificar**, para no perder el significado del centinela |
| Conteos de morosidad y consultas (`num_*`) | **Sin modificar**, un recorte perdería información |
| `funded_amnt`, `interest_rate`, `monthly_payment`, `princ_rec`, `interest_rec`, `remaining_princ_for_tot_amnt_fund`, `paym_rec_for_tot_amnt_fund` | **Capping con 1.5 × IQR** (distribución continua casi simétrica) |
| `annual_income` | Ver abajo |
| Variables discretas de fecha y `region_code` | Sin tratamiento |

**`annual_income` > $1M:** hay 574 registros (de 2,139,643). Se comparó su tasa de default contra la tasa base y se aplicó una **prueba z de proporciones** (`statsmodels.proportions_ztest`): p-value = 0.003, es decir, hay diferencia estadística. Aun así, por ser una fracción mínima del dataset, se decidió **conservarlos**, limitando el valor a $1M (`clip(upper=1_000_000)`) en el preprocesador.

---

## 5. EDA y selección de variables

### 5.1 EDA frente a la variable objetivo

- Boxplots de las variables `num_*` y `mths_*` separados por `y`.
- Análisis de la concentración del centinela 999 y de su estabilidad por año de emisión (`issue_date_year`), sin saltos abruptos.
- Se **excluyen por posible leakage** (`variables_prohibidas`): `princ_rec`, `interest_rec`, `late_fees_rec`, `remaining_princ_for_tot_amnt_fund`, `paym_rec_for_tot_amnt_fund`, con un `assert` de verificación sobre las features finales.
- Como el criterio estándar en riesgo de crédito con regresión logística es WoE/IV, no se usaron ANOVA ni chi-cuadrado como criterio de selección. La única prueba de hipótesis formal del notebook es la prueba z de proporciones sobre los ingresos extremos.

### 5.2 Information Value (IV)

Para cada variable se discretiza en bins (manuales para conteos y centinelas, **deciles** para continuas, categorías para flags), se calcula el WoE con suavizado de Laplace (0.5) y se obtiene el IV. **Umbral aplicado: IV > 0.01.**

Variables que pasaron el filtro (17):

| Variable | IV |
|---|---|
| `interest_rate` | 0.446 |
| `mths_since_last_installment_acc_op` | 0.108 |
| `bal_to_cred_lim` | 0.102 |
| `nunca_last_install` | 0.091 |
| `max_bal_owed` | 0.083 |
| `num_rev_trades_op_in_24mths` | 0.068 |
| `num_inq_in_6mths` | 0.059 |
| `dept_paym_income_ratio` | 0.051 |
| `num_installment_acc_op_in_24mths` | 0.044 |
| `used_credit_share` | 0.040 |
| `annual_income` | 0.036 |
| `num_rev_trades_op_in_12mths` | 0.025 |
| `monthly_payment` | 0.023 |
| `num_inq` | 0.022 |
| `funded_amnt` | 0.020 |
| `num_open_trades_in_6mths` | 0.017 |
| `num_derogatory_pub_rec` | 0.011 |

### 5.3 Multicolinealidad

**Spearman (|ρ| > 0.7):** en cada par correlacionado se elimina la variable con menor IV.

| Se elimina | Se conserva | Motivo |
|---|---|---|
| `nunca_last_install` | `mths_since_last_installment_acc_op` | Mayor IV |
| `num_installment_acc_op_in_24mths` (0.044) | `mths_since_last_installment_acc_op` (0.108) | Mayor IV |
| `num_rev_trades_op_in_12mths` (0.025) | `num_rev_trades_op_in_24mths` (0.068) | Ventana de 12 meses contenida en la de 24 |
| `funded_amnt` (0.020) | `monthly_payment` (0.023) | Mayor IV |

Quedan **13 variables**, con **VIF máximo de 1.97**.

### 5.4 Variables adicionales

| Variable | IV | Decisión |
|---|---|---|
| `loan_term_months` | 0.0730 | Se incorpora (categórica: 36 / 60 meses) |
| `credit_history_length` | 0.0107 | Se incorpora (`issue_date_year - earliest_cr_line_year`, sin valores negativos) |
| `emp_length_num` | 0.0043 | Se descarta |
| `region_code` | 0.0031 | Se descarta |

Sin pares con |ρ| > 0.7 entre las nuevas y las anteriores. **VIF máximo del set final: 1.98.**

### 5.5 Set final: 15 variables

`interest_rate`, `mths_since_last_installment_acc_op`, `bal_to_cred_lim`, `max_bal_owed`, `num_rev_trades_op_in_24mths`, `num_inq_in_6mths`, `dept_paym_income_ratio`, `used_credit_share`, `annual_income`, `monthly_payment`, `num_inq`, `num_open_trades_in_6mths`, `num_derogatory_pub_rec`, `loan_term_months`, `credit_history_length`.

---

## 6. WOEEncoderV2 (encoder general para train y test)

Encoder de **Weight of Evidence** que se ajusta **solo con train** y se aplica igual a train y test.

```
WoE = ln( %buenos / %malos )      # con suavizado de Laplace (+0.5)
```

**Cómo trabaja**

- `fit(df, target, variables_bins, categoricas)`: calcula el WoE de cada bin/categoría y guarda `mapas`, `bins_def` e `iv_final`.
- `transform(df)`: crea `<variable>_woe` con el mapa aprendido en train.
- **Fallback:** valores fuera de los bins de train reciben WoE = 0.0. En test se verificó que el fallback **nunca se activó**: todos los valores cayeron en bins reales de train.

**Bins por tipo de variable**

| Tipo | Variables | Bins |
|---|---|---|
| Conteos (*zero-inflated*) | `num_rev_trades_op_in_24mths`, `num_inq_in_6mths`, `num_inq`, `num_open_trades_in_6mths` | `[-0.1, 0, 1, 2, 5, inf]` |
| Casi siempre 0 | `num_derogatory_pub_rec` | `[-0.1, 0, inf]` |
| Con centinela 999 | `mths_since_last_installment_acc_op` | `[-0.1, 12, 24, 48, 998, inf]` (el 999 queda como bin propio) |
| Continuas | `interest_rate`, `bal_to_cred_lim`, `max_bal_owed`, `dept_paym_income_ratio`, `used_credit_share`, `annual_income`, `monthly_payment`, `credit_history_length` | Deciles (`qcut`, q=10) |
| Categórica | `loan_term_months` | Categorías directas |

**Qué cambió respecto al primer `WOEEncoder`:** la versión V2 soporta variables categóricas, guarda los bins de deciles como `IntervalIndex` y convierte el resultado a `float64` de forma segura. El `WOEEncoder` original se dejó sin modificar.

---

## 7. PreprocesadorECL (base para MLOps)

Clase con interfaz `fit` / `transform` que reproduce las transformaciones del notebook para que el mismo código corra en entrenamiento y en producción.

### Transformaciones Tipo A (fijas, iguales en train y test)

| Transformación | Detalle |
|---|---|
| `credit_history_length` | `issue_date_year - earliest_cr_line_year`, con `clip(lower=0)` |
| `mths_since_last_installment_acc_op` | Nulos → 999 |
| `num_open_trades_in_6mths`, `num_rev_trades_op_in_24mths`, `num_inq` | Nulos → 0 |
| `annual_income` | `clip(upper=1_000_000)` |

### Transformaciones Tipo B (aprendidas en `fit` solo con train)

| Parámetro | Valor aprendido |
|---|---|
| `mediana_max_bal_owed` | Mediana de train, para imputar `max_bal_owed` |
| `media_bal_to_cred_lim` | Media de train, para imputar `bal_to_cred_lim` |
| Mapas WoE | Un mapa por variable, vía `WOEEncoderV2` |

### Uso

```python
prep = PreprocesadorECL()
prep.fit(train_df)

train_woe = prep.transform(train_df)
test_woe  = prep.transform(test_df)        # test crudo, mismas transformaciones

features_finales = prep.get_features_finales()
X_train, y_train = train_woe[features_finales], train_woe['y']
X_test,  y_test  = test_woe[features_finales],  test_woe['y']
```

### Verificaciones realizadas

- Sin `NaN` ni `Inf` en `X_train` ni `X_test`.
- Shapes: `(1,711,714, 15)` y `(427,929, 15)`.
- Tasa de default idéntica en train y test (split estratificado correcto).
- El fallback del WoE no se activó en test.

### Puntos a revisar antes de desplegar

- El **capping 1.5 × IQR** de las variables continuas (incluidas `interest_rate` y `monthly_payment`) se aplica hoy en el notebook sobre train y **no está dentro del preprocesador**. Conviene incorporarlo como transformación aprendida para que producción reciba el mismo tratamiento.
- Serializar el preprocesador y el modelo juntos (`joblib` / `Pipeline`) y validar el esquema de entrada antes de `transform`.

---

## 8. Modelo y resultados

```python
modelo = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=42)
modelo.fit(X_train, y_train)
```

`class_weight='balanced'` compensa el desbalance de ~13%.

### Métricas

| Conjunto | AUC-ROC | Gini | KS |
|---|---|---|---|
| Train | 0.7056 | 0.4112 | 0.2981 |
| Test | 0.7065 | 0.4129 | 0.3005 |

Las métricas de train y test son prácticamente iguales: **no hay sobreajuste**.

### Coeficientes

Con WoE definido como `ln(%buenos/%malos)`, se esperan coeficientes negativos. Esto se cumple en 14 de las 15 variables.

| Variable | Coeficiente |
|---|---|
| `interest_rate_woe` | -0.818 |
| `monthly_payment_woe` | -0.749 |
| `num_derogatory_pub_rec_woe` | -0.741 |
| `annual_income_woe` | -0.705 |
| `num_inq_in_6mths_woe` | -0.520 |
| `dept_paym_income_ratio_woe` | -0.452 |
| `mths_since_last_installment_acc_op_woe` | -0.382 |
| `credit_history_length_woe` | -0.343 |
| `max_bal_owed_woe` | -0.256 |
| `num_rev_trades_op_in_24mths_woe` | -0.226 |
| `num_inq_woe` | -0.191 |
| `bal_to_cred_lim_woe` | -0.180 |
| `loan_term_months_woe` | -0.164 |
| `used_credit_share_woe` | -0.097 |
| `num_open_trades_in_6mths_woe` | **+0.039** |

La excepción es `num_open_trades_in_6mths_woe`, con signo positivo y magnitud muy pequeña. Es un candidato a revisar (eliminarla o reagrupar sus bins) en una siguiente iteración.

### Estabilidad temporal (AUC en test por año de emisión)

| Año | AUC |
|---|---|
| 2007 | 0.637 |
| 2008 | 0.674 |
| 2009 | 0.644 |
| 2010 | 0.662 |
| 2011 | 0.685 |
| 2012 | 0.661 |
| 2013 | 0.683 |
| 2014 | 0.683 |
| 2015 | 0.692 |
| 2016 | 0.687 |
| 2017 | 0.693 |
| 2018 | 0.696 |

El poder discriminante mejora de forma gradual en los años más recientes.

---

## 9. Próximos pasos

1. Revisar `num_open_trades_in_6mths` (signo del coeficiente).
2. Incorporar el capping IQR al `PreprocesadorECL`.
3. Calibrar las probabilidades a **PD**.
4. Estimar **LGD** y **EAD** y calcular **ECL = PD × LGD × EAD**.
5. Empaquetar preprocesador y modelo, y definir el pipeline de despliegue y monitoreo (PSI, AUC/KS en producción).
6. Evaluar el ciclo completo en **AWS SageMaker** y comparar con **Azure Machine Learning**.

---

## 10. Estructura sugerida del repositorio

```
ECL_Credit_Loss/
├── README.md
├── notebooks/
│   └── ECL_Notebook.ipynb
├── src/
│   ├── woe_encoder.py
│   └── preprocesador_ecl.py
├── models/
│   └── (artefactos serializados)
└── requirements.txt
```