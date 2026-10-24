# Guía de usuario de la interfaz ECL

Esta guía explica cómo usar la aplicación desde el navegador: qué hace cada pestaña, cómo cargar una cartera, cómo interpretar los resultados y qué significan los indicadores del modelo.

> **Alcance:** herramienta local de apoyo analítico. No es un detector de fraude y no debe usarse para aprobar o rechazar créditos individuales.

## 1. Antes de empezar

La interfaz necesita que la API y el frontend estén en ejecución.

**Terminal 1 — API**

```powershell
uvicorn api.main:app --port 8000
```

**Terminal 2 — frontend**

```powershell
cd frontend
npm run dev
```

Abrir <http://localhost:3000>.

Comprobaciones rápidas:

- La API responde en <http://localhost:8000/health>.
- La documentación técnica de la API está en <http://localhost:8000/docs>.
- `frontend/.env.local` debe apuntar a `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- Si falta la cartera de ejemplo, ejecutar desde la raíz:

```powershell
python scripts/make_sample.py
```

La instalación completa, los requisitos y la generación del modelo están en [README.md](README.md).

## 2. Navegación general

La cabecera es fija y contiene cuatro pestañas:

| Pestaña | Ruta | Para qué sirve |
|---|---|---|
| **Cartera** | `/` | Cargar un CSV, procesar una cartera y analizar los resultados |
| **Crédito individual** | `/credito` | Estimar PD, LGD, EAD y ECL de un solo crédito |
| **Modelo** | `/modelo` | Consultar metodología, métricas, supuestos y límites |
| **Historial** | `/historial` | Revisar corridas anteriores y descargar sus CSV |

La pestaña activa se resalta en la cabecera. En pantallas pequeñas, la navegación se puede desplazar horizontalmente.

Elementos globales:

- **Aviso superior:** recuerda que la estimación es agregada y no una decisión crediticia.
- **Cabecera:** identifica la aplicación y permite cambiar de pestaña.
- **Pie de página:** muestra si la API está disponible, la versión del modelo y la semilla. Si aparece **“API no disponible”**, revise que el backend esté encendido en el puerto 8000.

## 3. Pestaña Cartera

Es el flujo principal para analizar un conjunto de créditos.

### 3.1 Cargar un archivo

En la tarjeta **Cargar cartera** puede:

1. Arrastrar un archivo `.csv` sobre la zona punteada.
2. Hacer clic en la zona punteada.
3. Usar **Seleccionar CSV**.
4. Usar **Usar cartera de ejemplo** para procesar la muestra incluida de 1.000 créditos.

El archivo debe ser CSV, no estar vacío y contener las 16 columnas de entrada. La carga se envía a la API y el procesamiento continúa en segundo plano.

### 3.2 Estados del procesamiento

La tarjeta de progreso muestra el archivo, el `job_id` y el estado:

| Estado visible | Significado |
|---|---|
| **Subiendo cartera** | El navegador está transfiriendo el archivo |
| **En cola** | La API recibió el archivo y espera un trabajador |
| **Procesando** | Se están calculando PD, LGD, EAD y ECL |
| **Completado** | Los resultados están disponibles |
| **Error** | El procesamiento falló; revise el reporte y el mensaje |

Si hay un error, la interfaz muestra **“El procesamiento no pudo completarse”**. El reporte de calidad puede seguir visible para explicar el problema.

### 3.3 Reporte de calidad de datos

Aparece antes de los resultados principales. El distintivo puede ser **Sin hallazgos** o **Revisar**.

Incluye:

- **Filas leídas:** registros encontrados en el CSV.
- **Filas procesadas:** registros que llegaron al cálculo.
- **Columnas faltantes:** columnas obligatorias ausentes.
- **Valores fuera de rango:** valores fuera del mínimo/máximo observado en entrenamiento.
- **IDs duplicados:** identificadores repetidos; no se eliminan automáticamente.
- **Valores faltantes por columna:** conteo de nulos.
- **Primeros valores fuera del rango:** hasta 10 ejemplos con fila, valor y rango observado.
- **Advertencias:** observaciones adicionales del backend.

Un distintivo **Revisar** no siempre impide el procesamiento: lea las advertencias. Las columnas faltantes o los nulos en columnas no permitidas sí pueden bloquear el trabajo.

### 3.4 Indicadores principales

Cuando el trabajo termina, aparecen siete tarjetas:

| Indicador | Qué significa |
|---|---|
| **Créditos** | Cantidad de registros procesados |
| **Exposición total** | Suma del monto financiado de la cartera |
| **ECL calibrado** | Suma de `PD × LGD × EAD` por crédito |
| **ECL con margen** | Estimación final después de aplicar la regla de prudencia del modelo |
| **Relación margen / calibrado** | ECL con margen dividida por ECL calibrada |
| **Créditos marcados** | Porcentaje de créditos seleccionados por la regla de marcación |
| **PD media** | Probabilidad de default promedio de la cartera |

La **relación margen / calibrado** no es una constante fija: depende de la composición de la cartera y de cuántos créditos activan el margen. El valor **ECL con margen** no debe interpretarse como una predicción exacta de pérdida, sino como una estimación conservadora.

### 3.5 Gráficos

La sección de resultados incluye cuatro gráficos. Al pasar el cursor sobre las barras o líneas se muestran los valores exactos.

1. **Distribución de PD**
   - Cantidad de créditos por rango de probabilidad de default.
   - Sirve para ver si la cartera se concentra en PD bajas, medias o altas.

2. **ECL por banda de riesgo**
   - Barras para ECL calibrada y ECL con margen.
   - Línea naranja para la PD media.
   - Permite identificar en qué bandas se concentra la pérdida esperada.

3. **ECL por plazo**
   - Compara la pérdida esperada entre créditos a 36 y 60 meses.
   - Útil para evaluar el efecto del plazo en la cartera.

4. **ECL por año de originación**
   - Evolución de la pérdida esperada según el año de emisión del crédito.
   - Ayuda a detectar concentraciones por cohorte.

### 3.6 Tabla de créditos

La tabla **Créditos procesados** muestra el detalle por crédito:

| Columna | Lectura |
|---|---|
| **ID** | Identificador original o `credito_id` generado |
| **Monto** | Monto financiado |
| **PD** | Probabilidad de default |
| **LGD** | Pérdida dado el incumplimiento |
| **EAD** | Exposición al momento del default |
| **ECL calibrado** | `PD × LGD × EAD` |
| **ECL con margen** | Estimación final del crédito |
| **Banda** | Banda de riesgo de B1 a B10; B1 es menor PD y B10 mayor PD |
| **Marcado** | Sí/No según la regla de marcación del modelo |

Controles disponibles:

- **PD mínima (%):** muestra solo créditos con PD igual o superior al valor. Debe estar entre 0 y 100.
- **Solo marcados:** muestra únicamente los créditos marcados.
- **Ordenar por:** ECL con margen, ECL calibrado, PD, monto financiado, banda o ID.
- **Asc / Desc:** cambia el sentido del ordenamiento.
- **Filas por página:** 10, 25, 50 o 100.
- **Anterior / Siguiente:** navega entre páginas.
- **Descargar CSV:** descarga el detalle completo del trabajo.

Los filtros se aplican en el servidor y reinician la paginación. El contador inferior indica el total de créditos, la página actual y si se está actualizando.

### 3.7 Cómo leer una cartera

Un flujo de lectura recomendado:

1. Revise primero el **reporte de calidad**.
2. Compruebe **Créditos** y **Exposición total** para confirmar que cargó el archivo esperado.
3. Compare **ECL calibrado** y **ECL con margen** para dimensionar el efecto de la prudencia.
4. Use **PD media** y la **distribución de PD** para entender el perfil de riesgo.
5. Revise **ECL por banda** y **ECL por plazo** para localizar concentraciones.
6. Filtre por **PD mínima** o **Solo marcados** para explorar los casos de mayor riesgo.
7. Descargue el CSV si necesita análisis adicional.

## 4. Pestaña Crédito individual

Permite estimar un solo crédito con las mismas 16 variables del modelo.

### 4.1 Formulario

El campo **ID del crédito** es opcional. Si se deja vacío, la API devuelve un identificador interno.

Los campos están agrupados en cuatro tarjetas:

#### Crédito

| Campo | Obligatorio | Notas |
|---|---|---|
| Monto financiado (USD) | Sí | Debe ser mayor que cero |
| Tasa de interés (%) | Sí | Tasa reportada del crédito |
| Plazo (meses) | Sí | Solo 36 o 60 meses |
| Cuota mensual (USD) | Sí | Pago mensual |

#### Ingresos y capacidad

| Campo | Obligatorio | Notas |
|---|---|---|
| Ingreso anual (USD) | Sí | Mayor que cero |
| DTI (%) | Sí | Relación deuda / ingreso reportada |

#### Historial

| Campo | Obligatorio | Notas |
|---|---|---|
| Año de originación | Sí | Año del crédito |
| Año de la primera línea de crédito | Sí | Año de inicio del historial |

#### Comportamiento

| Campo | Obligatorio | Notas |
|---|---|---|
| Cuentas revolventes abiertas (24 m) | No | Puede quedar vacío |
| Consultas de crédito (6 m) | Sí | Consultas recientes |
| Consultas de crédito (total) | No | Puede quedar vacío |
| Registros públicos derogatorios | Sí | Registros negativos |
| Meses desde la última cuota (cuenta abierta) | No | Puede quedar vacío |
| Saldo / límite de crédito (%) | No | Puede quedar vacío |
| Saldo máximo adeudado (USD) | No | Puede quedar vacío |
| Uso de crédito (%) | Sí | Uso reportado |

El formulario se abre con valores de ejemplo para facilitar una prueba rápida. **Restablecer** vuelve a esos valores y borra el resultado.

### 4.2 Ejecutar la estimación

1. Revise o complete los campos.
2. Pulse **Estimar crédito**.
3. Espere el mensaje **Calculando estimación…**.
4. El resultado aparece en la columna derecha.

Si algún campo obligatorio falta o tiene un valor inválido, aparece **“Revise los datos del crédito”** con la lista de errores y no se envía la solicitud.

### 4.3 Resultado del crédito

La tarjeta **Resultado del crédito** muestra:

- **Estado:** **Marcado** o **No marcado**.
- **ID:** identificador usado en la respuesta.
- **PD:** probabilidad de default.
- **LGD:** porcentaje de pérdida si hay incumplimiento.
- **EAD:** exposición estimada al momento del default.
- **Banda de riesgo:** de B1 (menor PD) a B10 (mayor PD).
- **ECL calibrado:** `PD × LGD × EAD`.
- **ECL con margen:** estimación final con la regla de prudencia.

Si el backend detecta valores fuera del rango de entrenamiento, aparece una tarjeta de **Advertencias**. Úsela para revisar si el caso está fuera del dominio del modelo.

### 4.4 Principales factores de riesgo

La sección **Principales factores de riesgo** muestra las tres contribuciones más negativas del modelo para ese crédito. Cada elemento incluye:

- Nombre de la variable transformada.
- Contribución `coeficiente × WoE`.
- Valor WoE.
- Coeficiente.

Estas contribuciones explican la construcción del puntaje, pero **no son relaciones causales** ni recomendaciones de negocio. Una contribución negativa reduce el logit y, por tanto, la PD estimada; úsela para trazabilidad, no para concluir que la variable “causa” el riesgo.

## 5. Pestaña Modelo

Presenta la ficha metodológica del artefacto cargado por la API.

### 5.1 Ficha superior

| Tarjeta | Contenido |
|---|---|
| **Versión** | Versión del artefacto |
| **Semilla** | Semilla de reproducibilidad |
| **Entrenamiento** | Fecha de generación del modelo |
| **Criterio de calibración** | Criterio usado para seleccionar el margen |

### 5.2 Cómo se estima la pérdida

La pestaña resume tres conceptos:

- **ECL calibrada:** `PD × LGD × EAD`.
- **ECL con margen:** estimación final después de aplicar la regla de prudencia.
- **Probabilidad de default:** regresión logística sobre variables transformadas a WoE.

La tarjeta **Margen de prudencia** muestra:

- **q:** cuantil de calibración.
- **s:** factor de cobertura.
- **Relación del margen:** factor observado en la calibración.
- **Violaciones de calibración:** porcentaje de casos donde la ECL estimada quedó por debajo de la pérdida observada.

### 5.3 Métricas de validación

La tabla muestra métricas sobre la muestra holdout. Las más relevantes para lectura general:

| Métrica | Interpretación |
|---|---|
| **AUC** | Capacidad de discriminar entre créditos que incumplen y los que no |
| **Gini** | Discriminación normalizada a partir del AUC |
| **KS** | Separación máxima entre buenos y malos |
| **ECL / real** | Relación entre la ECL estimada y la pérdida observada |
| **Violaciones** | Porcentaje de casos con ECL inferior a la pérdida real |
| **MAE** | Error absoluto medio en unidades monetarias |
| **WAPE** | Error absoluto ponderado por el volumen de pérdida |
| **Precisión** | Proporción de créditos marcados que efectivamente incumplen |
| **Recall** | Proporción de incumplimientos capturados por la marcación |
| **Lift** | Mejora frente a una selección aleatoria |
| **Créditos marcados** | Cobertura de la regla de marcación |

Un AUC cercano a 0.5 indica discriminación similar al azar; un valor más alto indica mejor separación. Las métricas deben interpretarse junto con los supuestos y límites del modelo.

### 5.4 Supuestos, límites y variables

- **Supuestos:** condiciones bajo las cuales se construyó el modelo.
- **Límites:** restricciones de uso e interpretación.
- **Variables de entrada:** las 16 columnas requeridas.
- **Robustez:** resultados del bootstrap, con iteraciones, ratio medio, intervalo p05–p95 y probabilidad de que el ratio sea menor que 1.
- **Aviso de uso:** recordatorio de que la herramienta es analítica.

Si la API no responde, la pestaña muestra un estado de error y el pie de página indica **“API no disponible”**.

## 6. Pestaña Historial

Lista las corridas de cartera guardadas por la API local.

### 6.1 Resumen superior

| Indicador | Qué muestra |
|---|---|
| **Corridas** | Número de trabajos registrados |
| **Exposición acumulada** | Suma de la exposición de todas las corridas |
| **ECL con margen acumulada** | Suma de la ECL final de todas las corridas |

Los acumulados suman todas las corridas. Si se procesa la misma cartera varias veces, sus totales se cuentan varias veces; no los use como una cartera única sin depurar duplicados.

### 6.2 Tabla de corridas

Las corridas se muestran de la más reciente a la más antigua:

| Columna | Contenido |
|---|---|
| **Fecha** | Fecha y hora del procesamiento |
| **Archivo** | Nombre del CSV y `job_id` |
| **Créditos** | Registros procesados |
| **Exposición** | Monto financiado agregado |
| **ECL calibrada** | ECL antes del margen |
| **ECL con margen** | ECL final |
| **% marcados** | Porcentaje de créditos marcados |
| **Versión** | Versión del modelo usada |
| **Detalle** | Botón **CSV** para descargar el resultado |

Hacer clic en **CSV** descarga el detalle completo de esa corrida. La tabla no permite borrar ni volver a ejecutar trabajos; para una nueva corrida, vuelva a **Cartera**.

Si todavía no hay corridas, aparece **“Aún no hay corridas guardadas”**.

## 7. Formato del CSV de cartera

El CSV debe tener una fila por crédito y estas 16 columnas, con los nombres exactos:

```text
funded_amnt
interest_rate
loan_term_months
monthly_payment
annual_income
dept_paym_income_ratio
issue_date_year
earliest_cr_line_year
num_rev_trades_op_in_24mths
num_inq_in_6mths
num_inq
num_derogatory_pub_rec
mths_since_last_installment_acc_op
bal_to_cred_lim
max_bal_owed
used_credit_share
```

Reglas:

- Todas las columnas deben existir, aunque algunas pueden contener valores vacíos.
- Los valores deben ser numéricos; no se aceptan categorías de texto, excepto `id`, que puede ser texto o número.
- `loan_term_months` debe ser 36 o 60.
- `issue_date_year` y `earliest_cr_line_year` son años, no fechas completas.
- `id` es opcional. Si existe, se usa para identificar el crédito; si no, se genera `credito_id`.
- Las columnas adicionales se ignoran.
- No incluya la variable objetivo `y` ni variables de desempeño posteriores al desembolso.
- Se recomienda UTF-8 y una fila de encabezado.

Columnas que pueden contener valores vacíos:

```text
num_rev_trades_op_in_24mths
num_inq
mths_since_last_installment_acc_op
bal_to_cred_lim
max_bal_owed
```

El backend imputa estos vacíos con las reglas del modelo: 0 para conteos, 999 para meses desde la última cuota y media/mediana de entrenamiento para las variables de saldo. Las demás columnas no admiten nulos.

## 8. Flujo recomendado

1. Iniciar API y frontend.
2. Abrir **Cartera**.
3. Probar con **Usar cartera de ejemplo** o cargar el CSV propio.
4. Revisar el reporte de calidad.
5. Leer KPIs y gráficos.
6. Explorar la tabla con filtros y descargar el CSV.
7. Repetir un caso puntual en **Crédito individual** si se necesita explicabilidad.
8. Consultar **Modelo** para contextualizar las métricas.
9. Usar **Historial** para recuperar corridas anteriores.

## 9. Problemas comunes

| Situación | Causa probable | Solución |
|---|---|---|
| El pie dice **API no disponible** | La API no está encendida o cambió de puerto | Ejecutar `uvicorn api.main:app --port 8000` |
| El navegador no conecta con la API | `frontend/.env.local` incorrecto | Revisar `NEXT_PUBLIC_API_URL` y reiniciar el frontend |
| El botón de ejemplo muestra un error | Falta `frontend/public/cartera_demo.csv` | Ejecutar `python scripts/make_sample.py` |
| El trabajo falla por columnas faltantes | El CSV no tiene las 16 columnas | Revisar el reporte de calidad y completar el encabezado |
| El trabajo falla por valores no numéricos | Hay texto, comas mal formateadas o celdas inválidas | Limpiar el CSV y volver a cargar |
| Hay muchos valores fuera de rango | La cartera no se parece a los datos de entrenamiento | Revisar la calidad y no interpretar como si fuera una cartera conocida |
| La tabla queda vacía después de filtrar | El filtro de PD o **Solo marcados** es demasiado restrictivo | Limpiar la PD mínima o desmarcar **Solo marcados** |
| Los gráficos no cargan | Falló la consulta de resumen | Revisar la API y recargar la página |
| El historial está vacío | Aún no se completó ninguna corrida | Procesar una cartera desde **Cartera** |

## 10. Glosario

- **PD:** probabilidad de que un crédito incurra en default.
- **LGD:** porcentaje de la exposición que se pierde si ocurre el default.
- **EAD:** exposición estimada al momento del default.
- **ECL calibrada:** `PD × LGD × EAD`.
- **ECL con margen:** estimación final después de aplicar la regla de prudencia del modelo.
- **Banda de riesgo:** segmento de B1 a B10; B1 es menor PD y B10 mayor PD.
- **Marcado:** crédito seleccionado por la regla de marcación calibrada del modelo. No es una decisión de crédito ni una acusación de fraude.
- **WoE:** transformación que reemplaza el valor original por la evidencia de riesgo de su grupo.
- **q:** cuantil usado en la calibración del margen.
- **s:** factor de cobertura aplicado por la regla de prudencia.
- **Holdout:** muestra de validación separada del entrenamiento.

## 11. Privacidad y uso responsable

- La aplicación está pensada para ejecución local; no incluye autenticación ni control de usuarios.
- No exponga los puertos 8000 o 3000 a una red pública sin añadir autenticación, HTTPS y controles de acceso.
- Los resultados se guardan en `data/predictions/`; trate esos archivos como información sensible.
- No cargue datos personales reales en entornos compartidos o públicos.
- Use los resultados como apoyo analítico y combínelos con revisión humana, políticas de riesgo y validación del modelo.
