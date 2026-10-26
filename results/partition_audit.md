# Auditoría de la partición agrupada

**Fecha:** 2026-10-25  
**Objeto:** partición principal de la Fase 3, generada por `src/preprocessing.py` con semilla `20261025` y proporciones 70/15/15.  
**Alcance:** revisión metodológica y numérica de la concentración de dominios en validación y prueba. No se modificó `Dataset.csv`, no se regeneró la partición, no se entrenaron modelos y no se alteró el informe ni ningún resultado existente.  
**Estado:** diagnóstico y alternativas propuestas; decisión pendiente de aprobación.

## 1. Resumen ejecutivo

La partición actual **no tiene fuga de información por dominio** y reproduce exactamente los índices almacenados. Sin embargo, la clase positiva de evaluación está dominada por un solo dominio:

- Validación: `google.com` concentra **1 439 de 2 483 positivos = 57,95 %**.
- Prueba: `weebly.com` concentra **2 444 de 2 493 positivos = 98,03 %**; solo **49 positivos** quedan fuera de ese dominio.
- La prueba contiene solo **50 dominios positivos** distintos; la validación, **747**, pero uno de ellos aporta casi el 58 % de los positivos.

El problema es estructural, no un mal resultado de la semilla. El algoritmo separa los grupos con clase 1, los ordena por tamaño y los asigna a la partición con menor carga. Al comenzar los tres conjuntos vacíos, los tres grupos positivos más grandes quedan necesariamente en conjuntos distintos. La semilla solo cambia cuál de esos tres grupos cae en validación y cuál en prueba.

**Consecuencia:** las métricas globales de validación y prueba medirán principalmente el comportamiento sobre `google.com` y `weebly.com`. La partición sirve como prueba de generalización a dominios no vistos, pero no como muestra representativa de la población de phishing. No debe presentarse como tal.

**Recomendación principal:** no reemplazar la partición actual de forma automática. Para el informe, conservarla y declarar su alcance; para la comparación de modelos, preferir validación cruzada agrupada. Si se exige un único holdout, la alternativa con tope del 10 % es la más equilibrada, pero cambia el estimando y debe presentarse como partición de sensibilidad.

## 2. Evidencia verificada

### 2.1 Reproducibilidad

- `src/preprocessing.py` reproduce la asignación almacenada en `results/tables/20_particion_agrupada_indices.csv`: **0 discrepancias**.
- Totales: 115 231 filas, 98 641 de clase 0 y 16 590 de clase 1.
- Partición actual: 80 658 / 17 291 / 17 282 filas; 11 614 / 2 483 / 2 493 positivos.
- Tasas de clase 1: 14,399 % / 14,360 % / 14,425 %.
- Ningún dominio aparece en más de una partición. Al agrupar por dominio, tampoco hay URL del mismo dominio en otra partición.

La fuente se contrastó con los metadatos públicos de URL-Phish v2: tamaño 15 149 338 bytes y SHA-256 `d68b3cd0648dcf9c775347416ad1a8995e8a025921fbe3871ca6158d4db3c3a1`, coincidentes con `Dataset.csv`. Los 1 369 duplicados exactos están en el archivo publicado; no son una alteración local.

### 2.2 Composición actual

| Partición | Filas | Positivos | Tasa clase 1 | Dominio positivo principal | % de positivos | Top 5 positivos | Dominios positivos | Dominios efectivos |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| Entrenamiento | 80 658 | 11 614 | 14,399 % | `pages.dev` (1 050) | 9,04 % | 23,59 % | 3 551 | 55,3 |
| Validación | 17 291 | 2 483 | 14,360 % | `google.com` (1 439) | 57,95 % | 60,01 % | 747 | 3,0 |
| Prueba | 17 282 | 2 493 | 14,425 % | `weebly.com` (2 444) | 98,03 % | 98,19 % | 50 | 1,0 |

“Dominios efectivos” es \(1/\sum p_i^2\), donde \(p_i\) es la proporción de positivos del dominio \(i\). Un valor cercano a 1 indica que casi todos los positivos vienen de un solo dominio; un valor mayor indica mayor diversidad.

### 2.3 Distribución global de positivos

| Corte | Positivos cubiertos | % de 16 590 |
|---|---:|---:|
| Top 1 (`weebly.com`) | 2 444 | 14,73 % |
| Top 3 | 4 933 | 29,73 % |
| Top 5 | 6 054 | 36,49 % |
| Top 10 | 7 249 | 43,69 % |
| Top 50 | 10 190 | 61,42 % |
| Hasta cubrir 80 % | — | requiere 1 072 dominios |

Además, **3 234 dominios tienen exactamente un positivo** (74,38 % de los dominios positivos). La distribución es de cola larga, pero con unos pocos dominios que concentran una fracción decisiva de los casos.

### 2.4 Causa estructural

`assign_grouped_split` hace lo siguiente:

1. Separa los grupos en `solo_clase_0` y `con_clase_1`.
2. Ordena cada estrato por número de filas.
3. Asigna cada grupo a la partición con menor carga normalizada de filas y positivos.
4. Al empezar con cargas vacías, los primeros grupos positivos se reparten uno por conjunto.

Con la semilla actual:

- `weebly.com` → prueba.
- `google.com` → validación.
- `pages.dev` → entrenamiento.

El barrido de 60 semillas (0–59) confirma que los tres primeros grupos positivos siempre quedan en conjuntos distintos: **60/60 casos**. En 48/60 semillas, `weebly.com` cae en validación o prueba y el máximo porcentaje positivo de evaluación es ≈98,03–98,07 %. En las 12 semillas restantes, `weebly.com` cae en entrenamiento y el máximo baja a ≈57,7–57,8 %, pero `google.com` sigue dominando la evaluación. **Cambiar la semilla no corrige el problema.**

La causa última es la combinación de tres restricciones:

- no separar registros de un mismo dominio;
- mantener 70/15/15;
- mantener la tasa de clase 1.

El objetivo de positivos de prueba es 2 489, mientras que `weebly.com` aporta 2 444. Si ese dominio cae en prueba, ocupa el 98,2 % del objetivo positivo. Si se fuerza a entrenamiento, `google.com` y `pages.dev` ocupan la mayor parte de la evaluación. No existe una asignación que respete las tres restricciones y, al mismo tiempo, haga que la evaluación sea representativa de la masa de positivos.

## 3. Alternativas evaluadas

### A. Mantener la partición actual y cambiar la interpretación

**Ventajas**

- No requiere rehacer la Fase 3 ni el informe.
- Mantiene la reproducibilidad y la ausencia de fuga.
- La prueba sigue siendo válida como evaluación sobre dominios no vistos, en particular sobre `weebly.com`.

**Limitaciones**

- Las métricas globales de validación y prueba no estiman el rendimiento poblacional.
- El umbral elegido en validación estará dominado por `google.com`.
- La prueba de `weebly.com` mide una plataforma concreta, no “phishing en general”.
- Es imprescindible reportar métricas por dominio y no afirmar generalización.

**Uso recomendado:** conservarla como **prueba de estrés por dominio** y complementarla con análisis por dominio. No usarla como única base para afirmar superioridad general de un modelo.

### B. Holdout con tope de concentración positiva en evaluación

**Idea**

- Los grupos con positivos se ordenan de mayor a menor.
- Si un grupo supera el tope permitido para validación o prueba, se envía a entrenamiento.
- Los demás se asignan por carga normalizada, con cuotas globales de filas y positivos.
- Los grupos sin positivos se asignan por déficit de filas.

Se simuló en memoria con topes del 5 %, 7,5 %, 10 % y 15 % de los positivos de cada conjunto de evaluación. Resultados con la semilla vigente:

| Tope | Validación: máx. dominio | Prueba: máx. dominio | Top 5 validación | Top 5 prueba | Dominios efectivos val./prueba |
|---:|---:|---:|---:|---:|---:|
| 5 % | 4,34 % (`dropbox.com`) | 4,54 % (`weeblysite.com`) | 17,41 % | 17,48 % | 89,5 / 89,9 |
| 7,5 % | 6,31 % (`web.app`) | 6,60 % (`webflow.io`) | 24,99 % | 25,19 % | 50,6 / 50,2 |
| 10 % | 9,65 % (`r2.dev`) | 8,52 % (`q-r.to`) | 37,65 % | 37,61 % | 26,0 / 26,6 |
| 15 % | 13,22 % (`qrco.de`) | 14,38 % (`hsforms.com`) | 45,56 % | 45,72 % | 19,6 / 19,2 |

Con tope del 10 % y la semilla vigente:

| Partición | Filas | Positivos | Tasa clase 1 | Dominio positivo principal | % de positivos | Top 5 positivos | Dominios positivos | Dominios efectivos |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| Entrenamiento | 80 662 | 11 615 | 14,400 % | `weebly.com` (2 444) | 21,04 % | 52,12 % | 3 036 | 13,5 |
| Validación | 17 285 | 2 486 | 14,382 % | `r2.dev` (240) | 9,65 % | 37,65 % | 654 | 26,0 |
| Prueba | 17 284 | 2 489 | 14,401 % | `q-r.to` (212) | 8,52 % | 37,61 % | 658 | 26,6 |

- Totales exactos: 115 231 filas; 11 615 / 2 486 / 2 489 positivos.
- Ningún dominio en más de una partición.
- En 30 semillas, el máximo por dominio se mantuvo en 8,52–9,65 % y el top 5 en 37,61–37,65 %; la desviación de la tasa de clase fue ≤0,02 puntos porcentuales.

**Ventajas**

- Reduce drásticamente la concentración de evaluación: de 98,03 % a menos del 10 %.
- Conserva la tasa global de clase 1 y los totales.
- Es reproducible y no separa dominios.
- Tiene una regla explícita y defendible: ningún dominio aporta más del 10 % de los positivos de validación o prueba.

**Limitaciones**

- Todos los dominios positivos grandes quedan en entrenamiento; la evaluación representa dominios pequeños y medianos, no la masa de URL.
- El entrenamiento se concentra más: top 5 = 52,12 % y `weebly.com` = 21,04 %.
- El top 5 de evaluación sigue en ≈37,6 %; el tope del 10 % no elimina la cola, solo evita el dominio único.
- Cambia el estimando: no es una muestra representativa de la población; es una evaluación “fuera de los dominios dominantes”.
- Exigiría regenerar índices, tablas y el reporte de Fase 3 si se adopta como partición principal.

El tope del 5 % produce una evaluación más diversa, pero deja fuera a casi todos los dominios medianos; el del 15 % se acerca demasiado a la concentración actual. El 10 % es un compromiso razonable, no una solución perfecta. El 7,5 % es una alternativa más estricta si se prioriza diversidad de dominios sobre representatividad de los medianos.

### C. Validación cruzada agrupada (`GroupKFold`)

**Idea:** dividir los dominios en \(k\) folds, de modo que cada dominio aparezca completo en un solo fold y todos los folds se usen como evaluación en algún momento.

**Ventajas**

- Cada dominio grande aparece en evaluación en algún fold; no se decide su destino con una sola semilla.
- Permite reportar media, desviación y rango entre folds, en lugar de una única estimación.
- Es más adecuada para comparar modelos y analizar estabilidad.
- Evita la ilusión de que un único holdout es “la” muestra representativa.

**Limitaciones**

- Requiere más cómputo y un protocolo de agregación.
- La media de folds puede seguir dominada por el fold que contiene `weebly.com`; por eso deben reportarse también métricas por fold y por dominio.
- No encaja directamente con el diseño actual de “evaluar prueba una sola vez”; requiere aprobar un cambio de protocolo.
- No sustituye la necesidad de declarar que el dataset no es una muestra aleatoria de toda la web.

**Uso recomendado:** evaluación principal de modelos en la fase posterior, con la partición actual como prueba de estrés secundaria.

### D. Otras variantes no recomendadas sin más evidencia

- **Reservar solo los primeros \(k\) dominios y repartir el resto al azar:** puede reducir la concentración, pero el resultado depende de \(k\) y de la semilla; no se simuló con suficiente detalle.
- **Reparticionar hasta obtener una prueba “bonita”:** rechazado. Aumenta el riesgo de sesgo de selección y de elegir la partición por sus resultados.
- **Eliminar `weebly.com`, `google.com` o sus registros:** rechazado. Altera la población, reduce la evidencia y no corrige el problema metodológico.
- **Mezclar registros del mismo dominio entre particiones:** rechazado. Introduce fuga de información.

## 4. Comparación conceptual

| Criterio | Actual | Tope 10 % | `GroupKFold` |
|---|---|---|---|
| Sin fuga por dominio | Sí | Sí | Sí |
| Totales y tasa de clase | Sí | Sí | Sí, por fold |
| Máximo positivo por dominio en evaluación | 98,03 % | ≤9,65 % | Depende del fold |
| Diversidad de evaluación | Muy baja en prueba | Media | Alta entre folds |
| Representa la masa de URL | No | No; evalúa dominios no dominantes | Parcial; depende de folds |
| Entrenamiento representativo | Parcial | No; concentra los grandes | Parcial |
| Costo de implementación | Nulo | Medio | Medio-alto |
| Requiere cambiar Fase 3/informe | No | Sí | Sí, protocolo |
| Riesgo de conclusión engañosa | Alto si se usan métricas globales sin contexto | Medio | Bajo si se reporta por fold/dominio |

## 5. Recomendación

1. **No reemplazar la partición actual todavía.** La partición es válida para evitar fuga y para una prueba de estrés por dominio; el problema es de interpretación, no de integridad.
2. **Documentar el alcance:** en el informe y la guía, indicar que la prueba está dominada por `weebly.com` (98,03 % de positivos) y la validación por `google.com` (57,95 %). No afirmar generalización poblacional con métricas globales.
3. **Considerar `GroupKFold` agrupado como análisis de sensibilidad**, solo si el código confirma que `dom_normalizado` define los grupos y si se autoriza la instalación de `scikit-learn`. Reportar media, desviación y resultados por fold/dominio; no reemplaza automáticamente la partición de referencia.
4. **Si el docente exige un único holdout 70/15/15, adoptar la variante con tope del 10 % como partición de sensibilidad**, no como reemplazo silencioso de la actual. Etiquetarla explícitamente como “evaluación fuera de los dominios dominantes”.
5. **Mantener la partición actual como prueba de estrés secundaria** y no usarla para seleccionar hiperparámetros ni umbrales.
6. **Cualquier cambio de partición requiere aprobación explícita**, regenerar índices y tablas, repetir los controles de fuga y actualizar el informe. No se debe implementar en esta tarea.

## 6. Pruebas mínimas antes de adoptar una nueva partición

- [ ] Los totales de filas y clases reconcilian exactamente con 115 231 / 98 641 / 16 590.
- [ ] La tasa de clase 1 por partición se desvía ≤0,05 puntos porcentuales de la tasa global.
- [ ] Ningún dominio aparece en más de una partición.
- [ ] Ninguna URL aparece en más de una partición.
- [ ] El máximo de positivos por dominio en validación y prueba es ≤10 %.
- [ ] El top 5 de positivos en validación y prueba es ≤40 %.
- [ ] Los dominios efectivos de validación y prueba son ≥20.
- [ ] La asignación es reproducible con una semilla registrada.
- [ ] El barrido de semillas no cambia las garantías anteriores.
- [ ] La prueba no se usa para seleccionar modelo, hiperparámetros ni umbral.
- [ ] El informe declara que la evaluación no representa la masa de URL si se usa el tope.
- [ ] `Dataset.csv` conserva su hash.

## 7. Archivos y trazabilidad

- `src/preprocessing.py`: implementación de `assign_grouped_split` y de la partición actual.
- `results/tables/20_particion_agrupada_indices.csv`: índices verificados.
- `results/tables/22_resumen_particion_principal.csv`: totales y concentración actual.
- `results/tables/24_dominios_contradictorios_particion.csv`: `google.com` y `weebly.com` con etiquetas mixtas.
- `results/phase3_preprocessing.md`: reporte de la Fase 3.
- `docs/auditoria/auditoria_final.md`: hallazgo C1 sobre la concentración positiva.
- `results/model_design.md`: protocolo que deberá respetar cualquier cambio.

La simulación de la alternativa B se ejecutó en memoria con `.venv/bin/python`; **no se guardaron índices ni archivos de partición nuevos**. El barrido de semillas de la partición actual usó 60 semillas (0–59) y la semilla vigente se verificó por separado. El barrido de la alternativa B usó 30 semillas (0–29).

## 8. Decisión provisional registrada

**Decisión del usuario (2026-10-25):** conservar la partición agrupada actual como **partición de referencia**; considerar `GroupKFold` agrupado como alternativa de sensibilidad **solo si el código confirma los grupos y su viabilidad técnica**; no cambiar la partición en silencio.

- El código sí define los grupos con `dom_normalizado` y la partición actual no comparte dominios.
- `GroupKFold` no se ejecutó porque `scikit-learn` no está instalado; su adopción requiere autorización e instalación.
- La variante con tope del 10 % no se adopta en esta etapa; queda documentada como alternativa si se necesita un único holdout más diverso.
- Cualquier cambio futuro de partición requiere aprobación explícita, regenerar índices y tablas, repetir los controles de fuga y actualizar el informe.

Las opciones 2, 3 y 4 quedan disponibles para una fase posterior, pero no se implementan ahora.
