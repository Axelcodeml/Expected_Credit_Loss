🏛️ Reto 01: Expected Credit Loss
Este mes vais a poneros en la piel de un equipo de modelización de riesgo de crédito en un banco. El Comité de Riesgos os ha pasado una cartera de préstamos y os ha enviado este correo en donde os pide una cosa muy concreta:
Buenos días, 
Necesitamos calcular la pérdida esperada de la nueva cartera que acabamos de adquirir. Estos resultados se utilizarán para las provisiones y los tendrá que validar el regulador, así que debemos ser conservadores para evitar sanciones potenciales.
Necesitamos el dato listo para el Comité del 17 de octubre. Adjuntamos los datos que disponemos de la cartera.
Saludos, 
Big Boss
Ese es el reto traducido: Estimar el ECL (Expected Credit Loss) de la cartera lo mejor posible, con sesgo conservador. Pero fíjate en dos cosas que dicen entre líneas (esto se aprende con la experiencia). La primera, es que indican que se utilizará para provisiones (es decir, el dinero que hay que “guardar” en caso de impagos), por lo que nos interesa que la ECL sea lo más baja posible para ahorrar capital. Pero la segunda, es precisamente que el regulador va a validarlo, por lo que si las predicciones no son conservadoras nos impondrán sanciones. Por tanto, el objetivo real es obtener la ECL más precisa posible con la restricción de que la estimación esté siempre por encima del valor real. 
Una vez elegidos los ganadores, “pondremos en producción” el modelo entre la Comunidad. Cómo proponía Jose Osvaldo en la Comunidad: “Para llevarlo a un escenario más real, propongo que construyamos un backend y un frontend sencillos. Así podríamos implementar un pipeline de CI/CD y automatizar el despliegue en un mini cluster de Kubernetes.”
Los datos
Cartera de préstamos personales de Lending Club (EE. UU.), solo solicitudes individuales: https://www.kaggle.com/datasets/db0boy/lending-club-loan-data-cleared/data
Son dos ficheros: X.csv (variables disponibles para la modelización) y target.csv (columna y, 1 = impago). Contiene más de 2 millones de préstamos. Las columnas de X.csv se dividen en dos grupos, y esta es una distinción importante:
Variables de originación (disponibles en el momento de conceder el préstamo ~37 en total): importe financiado, plazo, tipo de interés, grade, ingresos anuales, situación de vivienda, antigüedad laboral, finalidad del préstamo, estado/región, ratio cuota-ingresos, líneas de crédito abiertas, morosidad previa, consultas de crédito recientes, saldo y uso del revolving, antigüedad de la primera línea de crédito, fecha de emisión, método de desembolso, entre otras.
Variables de desempeño (posteriores a la concesión, construidas a partir del histórico de pagos): principal recibido, intereses recibidos, comisiones por mora recibidas, y principal pendiente.
Este segundo grupo es la clave: son las que nos van a permitir reconstruir cuánto se ha cobrado realmente de cada préstamo y cuánto queda pendiente para calcular la LGD y el EAD observados y con ellos, la pérdida real de la cartera.


### ⚠️ Data leakage: 
Las variables de desempeño (y el grade de Lending Club) NO pueden usarse como input de nuestro modelo de PD, porque no existían en el momento de conceder el préstamo. Usarlas sería hacer trampa. Sí son la base para modelizar LGD y EAD.
El problema: PD × LGD × EAD = ECL
La pérdida esperada de un préstamo se descompone en tres piezas:
PD (Probability of Default): probabilidad de que ese préstamo impague.
LGD (Loss Given Default): qué % de lo que debe se pierde realmente si impaga (1 – tasa de recuperación).
EAD (Exposure at Default): cuánto queda pendiente en el momento del impago.
La pérdida esperada de cada préstamo es ECL_i = PD_i × LGD_i × EAD_i, y la pérdida esperada de la cartera es la suma de todos los ECL_i. 

### 🏁 Las reglas de la competición:
Aquí no ganamos por accuracy ni por el modelo más bonito. Ganamos por quién estima mejor la pérdida real de la cartera de test. El reto se evaluará con las dos siguientes métricas: 
ECL total de la cartera. Cuanto más bajo, mejor. 
MAE y MAPE de los ECL_j
Habrá dos ganadores, uno para el que consiga el mejor resultado en cada métrica.

### 🚨 IMPORTANTE! Con las siguientes restricciones. Si se incumple alguna, el modelo se descarta automáticamente:
El ECL estimado tiene que ser mayor al “ECL real”
ECL_j puede ser menor al “ECL_j real” para un máximo del 10% de la cartera
No hace falta que los tres modelos sean igual de sofisticados, de hecho en banca es habitual que LGD y EAD sean ajustados con modelos distintos que la PD. Lo importante es que el ECL agregado sea una estimación honesta y razonablemente conservadora.
### 📌 Al final 

Del reto quien quiera participar tendrá que compartir su proyecto con la Comunidad. Yo elegiré una semilla para el train/test split y todos correréis vuestro notebook cambiando solo esa semilla. Esto es lo que tendríamos en la práctica. Unos datos train para modelizar (operaciones hasta ayer) y unos datos de test (dentro de varios años, la pérdida final observada para los nuevos créditos.
Para que esto funcione, desde ya:

Todo el pipeline (desde que cargáis los datos hasta que calculáis el ECL final) depende de una sola variable SEED, definida al principio del notebook, que controla el train_test_split y cualquier otra fuente de aleatoriedad (random_state fijado en todos los modelos).
Nada de excluir filas "raras" a mano, ni de mirar el test antes de tiempo, ni de colar variables de desempeño en el modelo de PD. El split lo hace el código, no vosotros.
Los datos test no pueden incluirse en ninguna modelización. La limpieza, ingeniería de variables (y por supuesto entrenamiento de modelos) tiene que hacerse sobre la muestra Train, y solo después se le aplicará todo esto a la muestra de Test. 
El notebook termina con una única celda que imprime los dos números de interés.
Cuando cerremos el reto, os paso la semilla oficial, volvéis a correr el notebook cambiando solo eso, y compartís el resultado.
Cómo lo vamos a organizar
La idea es que esto dé para 15-20h en total, a vuestro ritmo. Os propongo una estructura orientativa (no obligatoria) para poder ir compartiendo avances en la comunidad:
Semana 1 (21–27 sept): estructura del Notebook, limpieza y preparación de datos. Entender la cartera, tratar missings/outliers, separar bien qué variables son de originación y cuáles de desempeño y preparar el pipeline para cuando hagamos la evaluación con la muestra de test.
Semana 2 (28 sept–4 oct): visualización y análisis exploratorio. Relaciones entre variables y default, y entre variables y pérdida.
Semanas 3–4 (5–18 oct): modelización. Construir PD, LGD y EAD, agregarlos en el ECL, y validar que la estimación tiene sentido.
Esto es solo una guía: podéis ir más rápido, saltaros el orden, mezclar etapas. Lo único que pido es que en cada etapa compartáis algo en la comunidad (un hallazgo, una duda, una decisión y por qué). La idea es generar debate, no que cada uno lo resuelva en su rincón.
Dudas, aquí mismo en el post o en el próximo directo. ¡Vamos con ello! 🚀
