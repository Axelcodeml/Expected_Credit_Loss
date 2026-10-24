# Estimación del ECL — Resumen del proyecto

## 1. Objetivo y reglas del reto

Estimar la pérdida esperada (ECL) de una cartera de préstamos de Lending Club para provisiones:

```
ECL_j = PD_j × LGD_j × EAD_j        ECL de la cartera = Σ_j ECL_j
```

- **Datos:** 2,139,643 créditos; el 13.07% cayó en default (`y = 1`).
- **Partición:** 80/20 estratificada por `y` (train 1,711,714; test 427,929). Todo se aprende solo con train; test se usa solo para evaluar.
- **Restricciones eliminatorias:**
  - **R1:** el ECL total estimado debe ser mayor que el ECL real.
  - **R2:** como máximo el 10% de los créditos puede tener `ECL_j` estimado menor que el real.
- **Qué gana:** el menor ECL total que cumpla R1 y R2. Hay un segundo ganador por MAE/MAPE de los `ECL_j`.

## 2. Pérdida real — método A (la "clave de respuestas")

Notación del crédito *j*: F = `funded_amnt`, P = `princ_rec`, I = `interest_rec`, L = `late_fees_rec`, T = `paym_rec_for_tot_amnt_fund`, y = 1 si cayó en default.

```
EAD_real   = máx(0, F − P)                      principal que seguía sin devolverse
Recuperado = máx(0, T − (P + I + L))            cobros posteriores al default (residuo)
LGD_real   = 1 − Recuperado / EAD_real          acotada a [0, 1]
ECL_real_j = y_j · EAD_real · LGD_real          = y · (EAD_real − Recuperado)
ECL_real   = Σ_j ECL_real_j
```

- Los intereses (I) solo sirven para aislar la recuperación; **no restan pérdida**.
- En defaulters de train: EAD medio 11,016, LGD media 0.902, pérdida media 9,939.
- **Método B** (solo para comparar): `ECL_real_B = y · máx(0, F − T)`. Resta además los intereses cobrados, así que es siempre ≤ A (≈ 26% menos en total). Si se cubre A, B queda cubierto.

## 3. PD: probabilidad de default

Variables transformadas a WoE por bins y regresión logística sin penalización (probabilidades calibradas):

```
WoE_b = ln( pct_buenos_b / pct_malos_b )          por bin b
IV    = Σ_b (pct_buenos_b − pct_malos_b) · WoE_b
PD_j  = 1 / (1 + exp(−(β0 + Σ_k β_k · WoE_k(x_jk))))
```

- **14 variables:** `interest_rate`, `mths_since_last_installment_acc_op`, `bal_to_cred_lim`, `max_bal_owed`, `num_rev_trades_op_in_24mths`, `num_inq_in_6mths`, `dept_paym_income_ratio`, `used_credit_share`, `annual_income`, `monthly_payment`, `num_inq`, `num_derogatory_pub_rec`, `loan_term_months`, `credit_history_length`.
- **Selección:** IV > 0.01, eliminación de pares con Spearman > 0.7 (se queda el de mayor IV) y VIF < 5.
- **Desempeño en test:** AUC 0.7065, Gini 0.413, KS 0.300. Todos los coeficientes salieron negativos.
- Las variables de desempeño y el grade no entran al PD.

## 4. EAD y LGD

Regresiones lineales simples, entrenadas **solo con defaulters de train**, sobre variables de originación:

```
z = [F, interest_rate, loan_term_months, monthly_payment, annual_income, dept_paym_income_ratio, issue_date_year]

EAD^_j = clip(γ0 + γ'z_j, 0, 1) · F_j       modela la fracción EAD/F    (R² validación cruzada = 0.178)
LGD^_j = clip(δ0 + δ'z_j, 0, 1)                                          (R² = 0.015, casi constante ≈ 0.90)
```

El EAD depende sobre todo de cuánto pagó el cliente antes de caer, y eso no se conoce al originar. La LGD casi no varía.

## 5. ECL calibrado y por qué no basta

```
ECL_cal_j = PD_j · LGD^_j · EAD^_j
```

| | Resultado en test |
|---|---|
| Total estimado / real A | 0.999 |
| Créditos con estimado < real | 12.83% (98.1% de los defaulters, 0% de los no defaulters) |
| R1 | Falla por 0.13% |
| R2 | Falla (12.83% > 10%) |

Es un estimador honesto del total, pero un defaulter siempre queda por debajo de su pérdida real, porque PD < 1. Los defaulters son ~13% de la cartera, así que se supera el 10% permitido.

## 6. Margen de conservadurismo: q y s

### Qué son

| Parámetro | Significado |
|---|---|
| **q** | Fracción de la cartera que se **marca** como alto riesgo |
| **s** | Fracción del monto financiado que se asigna como ECL a un crédito marcado |

```
u_j  = PD_j / F_j                         puntaje (criterio "pd_por_monto")
c(q) = cuantil de u en train de orden 1 − q
m_j  = 1 si u_j ≥ c(q), si no 0           crédito marcado

ECL_j = m_j · máx(ECL_cal_j, s · F_j) + (1 − m_j) · ECL_cal_j
```

- **Por qué PD / monto:** R2 cuenta créditos, no dólares. Cubrir un préstamo de 3,000 elimina el mismo riesgo de violación que cubrir uno de 15,000, pero cuesta cinco veces menos.
- **Ejemplo de s:** con s = 0.95, un crédito marcado de 10,000 recibe un ECL de al menos 9,500. Con s = 1 la cobertura está garantizada, porque ECL_real ≤ EAD ≤ F. Con s menor cuesta menos, pero quedan sin cubrir los defaulters cuya pérdida supera `s · F`.
- **El corte c(q) se fija con train** y se aplica igual a test.

### Cómo se eligen (solo con train)

Rejilla de q ∈ {10%, 11%, …, 40%} y s ∈ {0.60, 0.65, …, 1.00}:

```
mín   Σ_j ECL_j(q, s)
s.a.  (1/N) · Σ_j 1{ECL_j < ECL_real_j} ≤ 9%          colchón de 1 punto sobre el 10% del reto
      Σ_j ECL_j ≥ 1.02 · Σ_j ECL_real_j
```

El colchón de 9% cubre la variación entre semillas, que fue de ~0.02 puntos. **Resultado: q = 21% y s = 0.95** en las cinco semillas probadas.

### Evolución del costo

| Versión | ECL / ECL real | Violaciones | MAE |
|---|---|---|---|
| Calibrado puro | 0.999 | 12.83% | 2,083 |
| Criterio `pd`, q = 20%, s = 0.9 (colchón 8.5%) | 2.82 | 8.02% | 3,598 |
| Criterio `pd_por_monto`, q = 25%, s = 0.9 (colchón 8.5%) | 2.10 | 8.44% | 3,108 |
| **`pd_por_monto`, q = 21%, s = 0.95 (colchón 9%, rejilla fina)** | **1.905** | **8.96%** | **2,950** |

## 7. Métricas de evaluación

### Restricciones

```
R1: Σ_j ECL_j > Σ_j ECL_real_j
R2: (1/N) · Σ_j 1{ECL_j < ECL_real_j} ≤ 10%
```

### WAPE

```
WAPE = Σ_j |ECL_j − ECL_real_j| / Σ_j ECL_real_j  =  MAE / media(ECL_real_j)
```

- **Valor: 2.27.** El error absoluto total equivale a 2.27 veces la pérdida real total. Con una pérdida real media de ~1,298 por crédito, MAE 2,950 / 1,298 ≈ 2.27.
- Es alto porque el ECL final es ~1.9 veces el real (los créditos marcados se sobreestiman a propósito) y los defaulters sin marcar se subestiman. El ECL calibrado, sin margen, daría un WAPE de ≈ 1.6.
- No divide por créditos individuales, así que no se rompe con pérdidas reales de cero.

### MAPE

```
APE_j = |ECL_j − ECL_real_j| / ECL_real_j        MAPE = media(APE_j)   solo con ECL_real_j ≥ 1 dólar
```

- **Problema:** el ECL real es 0 en el ~87% de la cartera (los no defaulters), y el MAPE divide por ese valor. Además hay en promedio **5.2 créditos por test** con pérdida real positiva pero menor a 1 dólar. Con ellos, el MAPE salió en 1.857 × 10¹² %.
- **Tratamiento provisional:** se miden solo los créditos con pérdida real ≥ 1 dólar. El umbral es una convención nuestra, no sale de los datos. El enunciado no dice qué hacer con los ceros.
- **Valores:** MAPE ≈ 1.135 (113%, con desviación de 0.13 entre semillas) y **APE mediano 0.82**, que es estable. Un APE mediano de 0.82 sugiere que un defaulter típico recibe cerca del 18% de su pérdida real (es una lectura, no una medición directa).

### Recall: cómo sale una vez elegidos q y s

El recall no se escoge sobre la curva ROC. Es **consecuencia** de q:

1. Con el corte c(q) fijado en train, se marcan los créditos de test con `u_j ≥ c(q)`. Se marca ≈ q de la cartera (20.98% en test).
2. Se arma la matriz de confusión entre "marcado" y "cayó en default".
3. Se calcula:

```
recall        = TP / (TP + FN)            precisión = TP / (TP + FP)
especificidad = TN / (TN + FP)            lift      = precisión / tasa de default
```

Con el promedio de los cinco test: TP = 17,512, FN = 38,431, FP = 72,251, TN = 299,735.

```
recall        = 17,512 / (17,512 + 38,431)  = 0.313
precisión     = 17,512 / (17,512 + 72,251)  = 0.195     lift = 0.195 / 0.1307 = 1.49
especificidad = 299,735 / (299,735 + 72,251) = 0.806
```

- **Por qué sale ~31% y no otro valor.** Casi todas las violaciones son defaulters sin marcar, de modo que:

```
violaciones ≈ tasa de default × (1 − recall)
0.1307 × (1 − 0.313) ≈ 8.98%         (observado: 8.96%)
```

Con un tope de 9% de violaciones hace falta cubrir ~31% de los defaulters. Con el tope de 10% bastaría ~24%, y con 8.5%, ~35%. Cada punto menos de violaciones cuesta unos 7.7 puntos de recall y más ECL.

- **s no cambia a quién se marca**, solo cuánto se asigna, así que el recall depende de q y del criterio de orden. Los "defaulters cubiertos" (31.5%) son casi iguales al recall (31.3%).
- **No es el recall del PD solo.** Ese era 0.66, con el umbral de máximo KS (PD ≥ 0.136), pero marcando ~40% de la cartera y con una precisión de 0.215. Es otro clasificador, con otro punto de corte.

## 8. Resultados finales (promedio de 5 conjuntos de test)

| Concepto | Valor |
|---|---|
| ECL final / ECL real (R1) | 1.905 (rango 1.894–1.915) |
| Créditos con estimado < real (R2) | 8.96% (rango 8.93–8.99%) |
| Cumple R1 y R2 (definiciones A y B) | Sí, en los 5 test |
| Recall / precisión / especificidad / exactitud | 0.313 / 0.195 / 0.806 / 0.741 |
| Lift | 1.49 |
| MAE / WAPE / APE mediano | 2,950 / 2.27 / 0.82 |
| MAPE (pérdida real ≥ 1 dólar) | 1.135 |

Ejemplo con la semilla 42: ECL estimado de 1,061,427,949 frente a un real de ~555 millones.

## 9. Supuestos, límites y pendientes

- **Supuestos sin confirmar:** definición A de pérdida real, ECL real = 0 para los `y = 0` y recuperación como residuo (T − P − I − L).
- Los `y = 0` incluyen préstamos todavía vivos, que podrían caer después.
- La partición es aleatoria, así que los resultados son optimistas frente a otras épocas.
- Las cinco semillas son particiones de los mismos datos y se solapan; no prueban estabilidad en una cartera nueva.
- `interest_rate` pesa ~37% del impacto del PD y refleja el precio fijado por el prestamista.
- El margen cumple las reglas del reto, pero fuera de él no existe un "ECL real" contra el cual calibrarlo.
- **Preguntas abiertas para el organizador:** fórmula exacta de EAD y LGD reales; ECL real de los `y = 0`; tratamiento del MAPE con ceros; si el 10% se mide en créditos o en monto; si se permite un margen sobre PD × LGD × EAD; si la evaluación usa una o varias semillas.
- **Pendientes del notebook:** una sola `SEED` al inicio, tope de ingresos calculado con train y documentación de supuestos.

## 10. Uso adecuado

- **Sí:** estimar y provisionar la pérdida esperada de una cartera, presentando las dos capas (ECL calibrado y ECL con margen).
- **No:** detectar fraude (el dato no tiene etiqueta de fraude, solo de default), aprobar o rechazar créditos individuales, ni usar el grupo marcado como lista de alerta.
