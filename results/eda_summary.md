# Informe de análisis exploratorio de datos (EDA)

## Proyecto

**Título provisional:** Análisis comparativo de algoritmos de aprendizaje automático para la detección de sitios web de phishing mediante características de las URL.

**Dataset:** `Dataset.csv`  
**Ruta:** `Dataset.csv`  
**SHA-256 del archivo analizado:** `d68b3cd0648dcf9c775347416ad1a8995e8a025921fbe3871ca6158d4db3c3a1`  
**Fecha de ejecución del análisis:** 2026-10-25 (UTC)  
**Entorno:** Python 3.12.3, pandas 3.1.0, numpy 2.5.4, matplotlib 3.11.2, seaborn 0.13.2, scipy 1.18.1.

Este documento distingue, cuando corresponde, entre **observación** (resultado medido), **hipótesis** (explicación posible no contrastada) e **interpretación** (lectura prudente de los resultados). El dataset original no fue modificado. No se eliminaron registros ni se cambiaron etiquetas.

---

## 1. Método

1. Se leyó el CSV completo con `pandas`, sin reemplazar el archivo ni aplicar filtros.
2. Se verificaron dimensiones, tipos de datos, faltantes, duplicados, repeticiones de URL y dominios, constantes, valores extremos, asimetría y correlaciones.
3. Se compararon las clases mediante estadísticos descriptivos, prueba de Mann-Whitney y tamaño del efecto de rango biserial.
4. Se generaron 18 tablas principales y 6 figuras mediante `src/eda.py`.
5. Se ejecutaron controles automáticos de totales, porcentajes y existencia de archivos.
6. El notebook `notebooks/01_analisis_exploratorio.ipynb` reproduce el análisis paso a paso.

**Alcance:** el EDA describe y mide. No entrena modelos, no hace la partición definitiva y no decide todavía qué registros se eliminarán o transformarán.

---

## 2. Dimensiones y estructura

| Métrica | Valor |
|---|---:|
| Registros | 116 600 |
| Columnas | 26 |
| Celdas | 3 031 600 |
| Columnas numéricas totales | 23 |
| Variables numéricas predictoras | 22 |
| Columnas de texto | 3 (`url`, `dom`, `tld`) |
| Memoria en memoria | 42,269 MB |

**Observación:** el número de registros coincide con la cifra de 116 600 informada en la descripción inicial. No se detectaron filas con distinto número de campos.

**Variable objetivo:** `label`, entera, con valores 0 y 1.  
**Hipótesis pendiente de documentación:** 0 = sitio legítimo y 1 = phishing. Los ejemplos observados son compatibles con esa lectura, pero el archivo no contiene un diccionario de etiquetas. No debe afirmarse como hecho sin verificar la fuente.

**Cardinalidad observada:**

| Columna | Valores únicos |
|---|---:|
| `url` | 115 231 |
| `dom` | 90 860 |
| `tld` | 1 258 |

`url` y `dom` son identificadores de alta cardinalidad. `tld` también es categórica de alta cardinalidad para efectos de codificación.

---

## 3. Distribución de la variable objetivo

| `label` | Registros | Porcentaje |
|---:|---:|---:|
| 0 | 100 000 | 85,7633 % |
| 1 | 16 600 | 14,2367 % |
| **Total** | **116 600** | **100,0000 %** |

**Observación:** existe un desbalance aproximado de 6:1.  
**Interpretación:** la exactitud (*accuracy*) no será una métrica suficiente en la Fase 4; deberán reportarse, como mínimo, precisión, recall, F1, ROC-AUC y PR-AUC por clase.  
**Hipótesis:** que la clase 0 tenga exactamente 100 000 registros sugiere una selección o muestreo deliberado del conjunto original; no se dispone de documentación para confirmarlo.

---

## 4. Calidad de los datos

### 4.1 Valores faltantes

| Columna | Faltantes | Porcentaje |
|---|---:|---:|
| `tld` | 14 | 0,012007 % |
| Resto de columnas | 0 | 0 % |

**Observación:** solo `tld` presenta faltantes. De los 14 casos, 13 corresponden a URL con IP (`is_ip=1`) y 1 a una URL malformada (`https://www.ucatolica.edu.coeasyweb/`, con `dom=coeasyweb`).  
**Interpretación:** el faltante es estructural para las IP y no debe imputarse con un TLD inventado. En la Fase 3 deberá definirse una categoría explícita, por ejemplo `sin_tld`, o una estrategia equivalente documentada.

### 4.2 Duplicados y repeticiones

| Tipo | Grupos | Filas sobrantes | Filas involucradas | % del dataset |
|---|---:|---:|---:|---:|
| Filas completas duplicadas | 1 007 | 1 369 | 2 376 | 1,1741 % |
| URL repetidas | 1 007 | 1 369 | 2 376 | 1,1741 % |
| Dominios repetidos | 5 258 | 25 740 | 30 998 | 22,0755 % |

**Observación:** los 1 007 grupos de URL repetida tienen filas exactamente idénticas en las 26 columnas; no hay una misma URL con características distintas ni etiquetas contradictorias. Las cifras de filas completas y URL repetidas coinciden.  
**Observación:** los dominios repetidos no equivalen a filas duplicadas: un mismo dominio puede agrupar muchas URL diferentes.  
**Interpretación:** antes de la partición deberá decidirse si se eliminan los 1 369 duplicados exactos. Si no se eliminan, la misma observación podría quedar en entrenamiento y prueba y producir una evaluación optimista. Esta decisión corresponde a la Fase 3.

### 4.3 Distribución de etiquetas por dominio

| Categoría | Dominios | Registros |
|---|---:|---:|
| Solo clase 0 | 86 512 | 99 875 |
| Solo clase 1 | 4 324 | 12 323 |
| Ambas clases | 24 | 4 402 |

**Observación:** se reprodujeron exactamente **24 dominios con etiquetas contradictorias**. Agrupan 4 402 registros, el 3,7753 % del dataset. Los casos más grandes son:

| Dominio | Registros | Clase 0 | Clase 1 | % clase 1 |
|---|---:|---:|---:|---:|
| `weebly.com` | 2 465 | 11 | 2 454 | 99,55 % |
| `google.com` | 1 450 | 11 | 1 439 | 99,24 % |
| `wixsite.com` | 160 | 10 | 150 | 93,75 % |
| `dropbox.com` | 109 | 1 | 108 | 99,08 % |
| `blogspot.com` | 63 | 4 | 59 | 93,65 % |
| `wordpress.com` | 39 | 38 | 1 | 2,56 % |
| `uk.com` | 17 | 16 | 1 | 5,88 % |
| `archive.org` | 10 | 8 | 2 | 20,00 % |

**Hipótesis:** la etiqueta no depende solo del dominio ni de la URL; en varios casos parece depender del contenido de la página o del uso concreto del servicio de alojamiento.  
**Interpretación:** parte de estas contradicciones podría ser ruido de etiqueta, pero también podría reflejar páginas de phishing reales alojadas en servicios legítimos. No es posible decidirlo con este EDA. Es un riesgo metodológico que debe discutirse en la Fase 3 y en el informe académico.

### 4.4 Normalización inconsistente de `dom`

**Observación:** 226 filas (32 valores de `dom`) conservan el prefijo `www.`, mientras que la mayoría de los dominios no lo conserva. Al eliminar el prefijo, los dominios únicos pasan de 90 860 a 90 859 y los dominios contradictorios siguen siendo 24.

**Interpretación:** la columna `dom` no está normalizada de forma uniforme. No se corrigió en esta fase. Si se usa como variable categórica, esta inconsistencia debe resolverse antes del modelado, y la decisión debe documentarse.

### 4.5 Variables constantes o casi constantes

| Columna | Valores únicos | Valor más frecuente | Frecuencia | Porcentaje |
|---|---:|---:|---:|---:|
| `is_ip` | 2 | 0 | 116 587 | 99,9889 % |

**Observación:** `is_ip` solo tiene 13 registros con valor 1 (6 de clase 0 y 7 de clase 1).  
**Interpretación:** su capacidad predictiva es muy limitada y su asociación con `label` es prácticamente nula (r = 0,0120). No se elimina en esta fase; su inclusión deberá evaluarse en la Fase 3.

### 4.6 Valores extremos y asimetría

**Observación:** 18 de las 22 variables numéricas presentan asimetría absoluta mayor que 1. Las excepciones son `subdom_cnt`, `dot_cnt`, `spec_ratio` e `is_https`. Los máximos observados incluyen `url_len=1 202`, `path_len=670`, `query_len=1 148`, `letter_cnt=1 037`, `digit_cnt=321`, `special_cnt=234` y `entropy=6,03`.

El criterio de 1,5 × IQR marca porcentajes altos en varias variables discretas o acotadas:

| Variable | % atípicos IQR | Comentario |
|---|---:|---|
| `subdom_cnt` | 24,37 % | El límite superior es 1; cualquier valor 2 o más se marca. |
| `slash_cnt` | 29,30 % | El límite superior es 3; valores 4 o más se marcan. |
| `tld_len` | 20,29 % | Variable discreta con cola derecha. |
| `dash_cnt` | 19,62 % | Distribución concentrada en cero. |
| `path_len` | 17,79 % | Muchos valores cero y cola larga. |
| `special_cnt` | 14,09 % | Variable discreta acotada inferiormente. |

**Interpretación:** el criterio IQR es poco informativo para variables discretas con muchos ceros o con límites artificiales. Los valores extremos no deben eliminarse automáticamente: pueden ser URL largas reales o casos relevantes de phishing. En la Fase 3 se decidirá si se usan modelos robustos a escalas, transformaciones o criterios específicos.

---

## 5. Estadísticas descriptivas y comparación entre clases

### 5.1 Resumen general

| Variable | Media | Mediana | Desv. est. | Mín. | Máx. |
|---|---:|---:|---:|---:|---:|
| `url_len` | 32,953 | 27 | 29,370 | 12 | 1 202 |
| `dom_len` | 12,846 | 11 | 5,141 | 4 | 62 |
| `letter_cnt` | 25,007 | 20 | 22,396 | 4 | 1 037 |
| `digit_cnt` | 0,944 | 0 | 5,948 | 0 | 321 |
| `special_cnt` | 7,002 | 6 | 3,996 | 4 | 234 |
| `entropy` | 3,864 | 3,831 | 0,360 | 2,654 | 6,033 |
| `path_len` | 6,391 | 1 | 17,589 | 0 | 670 |
| `query_len` | 1,601 | 0 | 19,274 | 0 | 1 148 |
| `is_https` | 0,431 | 0 | 0,495 | 0 | 1 |

**Observación:** `is_https` tiene media 0,431, es decir, el 43,11 % de los registros usa HTTPS. La distribución de `digit_cnt`, `path_len` y `query_len` está fuertemente concentrada en cero.

### 5.2 Comparación por clase

| Variable | Media clase 0 | Media clase 1 | Mediana clase 0 | Mediana clase 1 | Efecto rango biserial |
|---|---:|---:|---:|---:|---:|
| `entropy` | 3,789 | 4,316 | 3,782 | 4,175 | 0,718 |
| `spec_ratio` | 0,243 | 0,184 | 0,243 | 0,185 | -0,594 |
| `is_https` | 0,351 | 0,914 | 0 | 1 | 0,563 |
| `url_len` | 29,076 | 56,305 | 26 | 38 | 0,546 |
| `digit_cnt` | 0,146 | 5,753 | 0 | 1 | 0,535 |
| `digit_ratio` | 0,0031 | 0,0738 | 0 | 0,0377 | 0,535 |
| `letter_cnt` | 22,260 | 41,555 | 19 | 29 | 0,488 |
| `path_len` | 4,605 | 17,153 | 1 | 6 | 0,337 |
| `dom_len` | 13,012 | 11,843 | 12 | 10 | -0,175 |

**Observación:** la clase 1 tiende a presentar URL más largas, más dígitos, mayor entropía, mayor longitud de ruta y mayor proporción de HTTPS. La clase 0 tiende a tener mayor proporción de caracteres especiales y dominios ligeramente más largos.  
**Interpretación:** estas son diferencias descriptivas, no relaciones causales. Además, la prueba de Mann-Whitney resulta significativa en casi todas las variables debido al tamaño muestral; por eso el tamaño del efecto es más informativo que el valor `p`.

La diferencia de HTTPS es especialmente marcada:

| `is_https` | Total | Clase 0 | Clase 1 |
|---:|---:|---:|---:|
| 0 (HTTP) | 66 329 | 64 907 (97,86 %) | 1 422 (2,14 %) |
| 1 (HTTPS) | 50 271 | 35 093 (69,81 %) | 15 178 (30,19 %) |

**Observación:** el 35,09 % de la clase 0 usa HTTPS, frente al 91,43 % de la clase 1.  
**Hipótesis:** esta diferencia podría reflejar distintos periodos o fuentes de recolección, no una propiedad universal del phishing.  
**Interpretación:** si el modelo aprende principalmente `is_https`, podría estar capturando un artefacto del proceso de recolección. En la Fase 4 conviene comparar un modelo con y sin esta variable.

### 5.3 Correlaciones

| Par de variables | r de Pearson |
|---|---:|
| `url_len` — `letter_cnt` | 0,9720 |
| `eq_cnt` — `amp_cnt` | 0,9277 |
| `path_len` — `special_cnt` | 0,7822 |
| `spec_ratio` — `entropy` | -0,7261 |
| `dot_cnt` — `subdom_cnt` | 0,6808 |
| `slash_cnt` — `path_len` | 0,6800 |

**Observación:** solo dos pares superan |r| ≥ 0,90, pero varios pares adicionales muestran asociaciones fuertes. Las razones `letter_ratio`, `digit_ratio` y `spec_ratio` son composiciones de la URL, por lo que su correlación con otras variables no es independiente.  
**Interpretación:** existe redundancia que debe evaluarse antes de elegir el conjunto final de predictores. Esto no implica eliminar variables automáticamente; depende del algoritmo y del objetivo.

Variables con mayor asociación lineal con `label`:

| Variable | r con `label` |
|---|---:|
| `digit_ratio` | 0,5178 |
| `entropy` | 0,5127 |
| `is_https` | 0,3975 |
| `spec_ratio` | -0,3846 |
| `digit_cnt` | 0,3295 |
| `url_len` | 0,3240 |

---

## 6. Interpretación de las figuras

### Figura 1. Distribución de clases

**Archivo:** `figures/fig01_distribucion_clases.png`

Muestra las barras de 100 000 registros de clase 0 (85,76 %) y 16 600 de clase 1 (14,24 %). La figura hace visible el desbalance. No demuestra que la población real de URL tenga esa proporción; refleja la composición del dataset analizado.

### Figura 2. Valores faltantes por columna

**Archivo:** `figures/fig02_valores_faltantes.png`

Solo `tld` aparece con faltantes: 14 casos (0,012 %). El resto de columnas tiene cero faltantes. De los 14, 13 corresponden a URL con IP y uno a una URL malformada. La figura no debe interpretarse como ausencia de problemas de calidad: los faltantes son escasos, pero hay duplicados y contradicciones de etiquetas.

### Figura 3. Distribuciones numéricas relevantes

**Archivo:** `figures/fig03_distribuciones_numericas.png`

Presenta histogramas de `url_len`, `dom_len`, `letter_cnt`, `digit_cnt`, `special_cnt`, `entropy`, `path_len` y `query_len`, con frecuencia en escala logarítmica y mediana marcada. Se observan colas derechas en casi todas las variables y concentraciones en cero en `digit_cnt`, `path_len` y `query_len`. El eje x está recortado en el percentil 99,5 para visualizar el cuerpo de la distribución; los valores extremos completos están en `results/tables/12_valores_extremos.csv`. El recorte es solo visual y no elimina datos.

### Figura 4. Comparación de características por clase

**Archivo:** `figures/fig04_comparacion_clases.png`

Compara cajas de `url_len`, `dom_len`, `digit_cnt`, `special_cnt`, `entropy` y `path_len` por clase, sin valores extremos gráficos y con el eje y recortado en el percentil 99,5. Se observa que la clase 1 tiene medianas más altas en longitud de URL, dígitos, entropía y longitud de ruta; la clase 0 tiene mediana de `dom_len` mayor. Las cajas describen la distribución central; no son una prueba de causalidad ni de separabilidad definitiva.

### Figura 5. Matriz de correlación

**Archivo:** `figures/fig05_matriz_correlacion.png`

Muestra la correlación de Pearson entre las 22 variables numéricas predictoras. Se aprecian bloques de asociación positiva entre variables de conteo y una relación negativa entre `spec_ratio` y `entropy`. Los pares `url_len`/`letter_cnt` y `eq_cnt`/`amp_cnt` superan 0,90. La matriz mide asociación lineal; relaciones no lineales no quedan reflejadas.

### Figura 6. Dominios con etiquetas contradictorias

**Archivo:** `figures/fig06_dominios_contradictorios.png`

Presenta la composición porcentual por clase de los 24 dominios que contienen ambas etiquetas, con el total de registros a la derecha. `weebly.com`, `google.com`, `wixsite.com`, `dropbox.com` y `blogspot.com` son mayoritariamente clase 1; `wordpress.com`, `uk.com` y `archive.org` son mayoritariamente clase 0. La barra está normalizada al 100 % dentro de cada dominio, por lo que no debe usarse para comparar volúmenes entre dominios; para eso está la columna `n`.

---

## 7. Inconsistencias y limitaciones de la descripción del dataset

1. **El conteo sí coincide:** se verificaron 116 600 registros, igual que la cifra informada. No hay inconsistencia en ese punto.
2. **No hay diccionario de datos:** el CSV no documenta el significado de `label`, la procedencia de las URL ni el periodo de recolección. La interpretación 0 = legítimo y 1 = phishing sigue siendo una hipótesis.
3. **La clase 0 tiene exactamente 100 000 registros:** esto es una observación; sugiere una posible selección o muestreo, pero no se puede confirmar sin la fuente original.
4. **Hay 1 369 filas duplicadas exactas:** un dataset presentado como limpio no debería contenerlas; su presencia afecta cualquier evaluación que no las trate.
5. **Hay 24 dominios con ambas etiquetas:** esto cuestiona que la etiqueta sea una propiedad estable del dominio y sugiere dependencia del contenido o de la URL específica.
6. **Hay 14 `tld` faltantes y una URL malformada:** son inconsistencias menores pero reales.
7. **`dom` no está normalizado uniformemente:** 226 filas conservan `www.` y el resto no. No cambia el número de dominios contradictorios, pero sí el recuento de dominios únicos.
8. **No se dispone de una descripción publicada más detallada:** por tanto, no es posible comparar el dataset con un perfil oficial de variables, clases o calidad. No se inventan referencias ni metadatos.

---

## 8. Limitaciones del EDA

- Es un análisis descriptivo; no permite afirmar causalidad ni predecir el desempeño de un modelo.
- Las pruebas de hipótesis tienen tamaños muestrales muy grandes; los valores `p` son casi siempre extremos y no miden relevancia práctica.
- La matriz de correlación solo detecta asociación lineal.
- Los histogramas y diagramas de caja están recortados visualmente en el percentil 99,5; los datos completos siguen en las tablas.
- El criterio IQR sobre variables discretas con muchos ceros produce porcentajes de “atípicos” poco interpretables.
- No se verificó la procedencia, fecha ni método de etiquetado del dataset.
- No se resolvieron los duplicados ni las contradicciones de dominio; solo se documentaron.
- La posible dependencia de la etiqueta respecto del contenido de la página no puede evaluarse con las columnas disponibles, que son únicamente de URL.
- No se ejecutó un modelo ni una partición, por lo que no hay estimaciones de generalización.

---

## 9. Decisiones pendientes para la Fase 3

1. **Confirmar la semántica de `label` y la procedencia del dataset.** Si no se consigue documentación, declararlo como limitación explícita.
2. **Definir el tratamiento de los 1 369 duplicados exactos.** Opciones: eliminarlos antes de la partición o mantenerlos con una justificación; la primera evita fuga de información.
3. **Elegir el esquema de partición.** Comparar una partición estratificada aleatoria con una partición agrupada por dominio. La segunda es más realista para evaluar generalización a dominios no vistos y evita que el mismo dominio aparezca en entrenamiento y prueba.
4. **Definir el conjunto de predictores.** Excluir `url` como identificador; decidir si se excluye `dom`; evitar one-hot de `dom` y `tld` sin una estrategia de agrupación o codificación adecuada.
5. **Resolver el faltante de `tld`.** Crear una categoría `sin_tld` o una regla equivalente, sin inventar un TLD.
6. **Evaluar `is_ip`.** Tiene 13 casos positivos; probablemente aporta poco y podría introducir ruido. La decisión debe basarse en validación, no solo en el EDA.
7. **Abordar la redundancia.** Decidir entre `url_len` y `letter_cnt`, y revisar el uso simultáneo de conteos y ratios. Evaluar la importancia de variables con modelos o análisis de multicolinealidad.
8. **Tratar el posible artefacto de `is_https`.** Comparar resultados con y sin esta variable para estimar cuánto depende el modelo de una diferencia probablemente asociada a la recolección.
9. **Definir métricas y validación.** Usar validación estratificada, reportar recall, precisión, F1, ROC-AUC y PR-AUC, y considerar `class_weight` si el algoritmo lo permite.
10. **Documentar el desbalance y los dominios contradictorios.** No eliminarlos ni reetiquetarlos sin evidencia; si se excluyen, justificarlo y medir el impacto.
11. **Mantener el preprocesamiento ajustado solo con entrenamiento.** Cualquier imputación, codificación o escalado debe aprenderse en el conjunto de entrenamiento para evitar fuga.
12. **Conservar la trazabilidad.** Registrar versiones, rutas, semillas y decisiones antes de comparar algoritmos.

---

## 10. Reproducibilidad y control de calidad

### Comandos

```bash
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python src/eda.py
```

En este equipo, `python3 -m venv` no pudo crear el entorno porque faltaba `ensurepip` (`python3.12-venv`). Se creó `.venv` con `virtualenv` instalado en el sitio de usuario. Para otra computadora se recomienda el procedimiento estándar:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/eda.py
```

### Controles ejecutados

| Control | Resultado |
|---|---|
| Suma de clases = número de filas | Verdadero |
| Porcentajes de clase suman 100 % | Verdadero |
| Registros por dominio = número de filas | Verdadero |
| Suma de faltantes = celdas faltantes | Verdadero |
| Una fila por columna en tipos/faltantes | Verdadero |
| 24 dominios contradictorios reproducidos | Verdadero |
| 6 figuras existen y no están vacías | Verdadero |
| 18 tablas existen y no están vacías | Verdadero |

El script terminó sin errores el 2026-10-25 y dejó un registro local en `results/eda_console.log`, excluido de Git por `.gitignore`. La evidencia versionada son las tablas, las figuras y este informe. Las celdas de código del notebook se ejecutaron secuencialmente con el intérprete del entorno virtual; no se abrió mediante Jupyter porque Jupyter no está instalado y no forma parte de las dependencias solicitadas para esta fase.

### Limitación del entorno

La instalación de dependencias se hizo únicamente en `.venv`. No se modificó el CSV ni se alteró el entorno del sistema más allá de instalar `virtualenv` en el directorio de usuario para poder crear el entorno.
