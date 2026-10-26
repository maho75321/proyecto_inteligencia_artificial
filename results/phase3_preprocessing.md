# Fase 3: preprocesamiento y partición de datos

**Proyecto:** Análisis comparativo de algoritmos de aprendizaje automático para la detección de sitios web de phishing mediante características de las URL  
**Curso:** Inteligencia Artificial — Segunda unidad  
**Fecha de ejecución:** 2026-10-25 (UTC)  
**Script:** `src/preprocessing.py`  
**Semilla:** `20261025`  
**Alcance:** preprocesamiento y partición; **no se entrenó ni evaluó ningún modelo**.

---

## 1. Resumen de la fase

Se identificó la procedencia del dataset, se confirmó la semántica de `label`, se eliminaron los duplicados exactos, se definió el conjunto inicial de predictores y se compararon dos esquemas de partición:

- partición aleatoria estratificada por clase;
- partición agrupada por dominio normalizado.

Se adoptó como **partición principal** la agrupada por dominio, con proporciones 70/15/15 para entrenamiento/validación/prueba. El conjunto original no fue modificado.

| Resultado | Valor |
|---|---:|
| Filas originales | 116 600 |
| Duplicados exactos eliminados | 1 369 |
| Filas para modelado | 115 231 |
| Predictores primarios | 21 |
| Partición principal | Agrupada por dominio |
| Semilla | 20261025 |
| SHA-256 del dataset | `d68b3cd0648dcf9c775347416ad1a8995e8a025921fbe3871ca6158d4db3c3a1` |
| Dataset modificado | No |

---

## 2. Procedencia y semántica de la etiqueta

El archivo local coincide con la **versión 2** del dataset **URL-Phish**:

- **Título:** URL-Phish: A Feature-Engineered Dataset for Phishing Detection
- **Autores:** Linh Dam Minh y Hung Tran Cong
- **Versión:** 2
- **DOI:** `10.17632/65z9twcx3r.2`
- **Publicación:** 9 de marzo de 2026
- **Licencia:** CC BY 4.0
- **URL:** https://data.mendeley.com/datasets/65z9twcx3r/2

La descripción de la versión 2 indica:

- 116 600 URL;
- 100 000 muestras benignas con `label = 0`;
- 16 600 muestras de phishing con `label = 1`;
- 22 características numéricas;
- tres columnas de referencia (`url`, `dom`, `tld`);
- una columna objetivo;
- 26 columnas en total.

**Semántica confirmada:** `0 = benigno` y `1 = phishing`. Ya no es una hipótesis inferida a partir de los datos. El reporte del EDA se conserva sin cambios por trazabilidad; su nota sobre la semántica pendiente queda resuelta en esta fase.

**Evidencia de identificación:** coinciden el número de filas, la distribución exacta de clases, las 26 columnas, los nombres de las características y la fecha del archivo local (9 de marzo de 2026). **Verificación posterior (2026-10-25):** el tamaño y el SHA-256 locales coinciden con los metadatos del archivo publicado en Mendeley v2, lo que confirma la identificación.

**Observación:** la versión 2 describe las URL como únicas y declara haber eliminado duplicados, pero el archivo publicado contiene 1 369 filas exactamente duplicadas. La coincidencia de tamaño y SHA-256 con los metadatos publicados confirma que la discrepancia está en la fuente, no en la copia local. Se documentó y se resolvió en la limpieza.

---

## 3. Integridad del archivo original

| Control | Resultado |
|---|---|
| Tamaño | 15 149 338 bytes |
| Filas × columnas | 116 600 × 26 |
| SHA-256 antes | `d68b3cd0648dcf9c775347416ad1a8995e8a025921fbe3871ca6158d4db3c3a1` |
| SHA-256 después | `d68b3cd0648dcf9c775347416ad1a8995e8a025921fbe3871ca6158d4db3c3a1` |
| Archivo modificado | No |

El hash se calculó antes y después de ejecutar `src/preprocessing.py`. Los resultados coinciden.

---

## 4. Limpieza y decisiones sobre los datos

### 4.1 Duplicados exactos

**Observación:** había 1 369 filas sobrantes en 1 007 grupos de filas idénticas en las 26 columnas. Las URL repetidas correspondían exactamente a esas mismas filas.

**Decisión:** eliminar los duplicados exactos conservando la primera aparición.

| Concepto | Valor |
|---|---:|
| Filas eliminadas | 1 369 |
| Eliminadas de clase 0 | 1 359 |
| Eliminadas de clase 1 | 10 |
| Filas resultantes | 115 231 |
| Clase 0 resultante | 98 641 |
| Clase 1 resultante | 16 590 |
| URL únicas resultantes | 115 231 |

**Justificación:** los duplicados exactos no aportan información nueva y, si se reparten entre entrenamiento y prueba, producen una evaluación optimista. Al conservar una sola copia se mantiene la observación original sin introducir duplicación artificial.

**Trazabilidad:** las 1 369 filas eliminadas, con su `fila_id`, posición original, fila conservada, URL, dominio y etiqueta, están en `results/tables/26_duplicados_eliminados.csv`.

### 4.2 Dominios con etiquetas contradictorias

**Observación:** después de eliminar duplicados exactos permanecen 24 dominios con ambas etiquetas, que agrupan 4 391 filas (3,81 % del conjunto de modelado).

**Decisión:** conservarlos, no reetiquetarlos y no excluirlos. La partición agrupada asigna cada dominio completo a una sola partición.

**Justificación:** la fuente combina dominios benignos con URL de phishing alojadas en servicios legítimos o compartidos. Casos como `google.com`, `weebly.com`, `dropbox.com` o `blogspot.com` pueden contener tanto páginas benignas como URL de phishing reales. Eliminarlos o reetiquetarlos sin evidencia introduciría una decisión no respaldada. Al agrupar por dominio se evita que el mismo dominio quede en entrenamiento y prueba.

Los casos principales, ya sin duplicados, son:

| Dominio | Filas | Clase 0 | Clase 1 | % clase 1 | Partición |
|---|---:|---:|---:|---:|---|
| `weebly.com` | 2 455 | 11 | 2 444 | 99,55 | prueba |
| `google.com` | 1 450 | 11 | 1 439 | 99,24 | validación |
| `wixsite.com` | 160 | 10 | 150 | 93,75 | entrenamiento |
| `dropbox.com` | 109 | 1 | 108 | 99,08 | entrenamiento |
| `blogspot.com` | 63 | 4 | 59 | 93,65 | entrenamiento |
| `wordpress.com` | 39 | 38 | 1 | 2,56 | entrenamiento |
| `adobe.com` | 23 | 1 | 22 | 95,65 | entrenamiento |
| `amazonaws.com` | 18 | 2 | 16 | 88,89 | entrenamiento |

El detalle de los 24 dominios está en `results/tables/24_dominios_contradictorios_particion.csv`.

**Riesgo residual (filas):** `google.com` representa el 8,39 % de validación y `weebly.com` el 14,21 % de prueba. **Medido sobre la clase positiva:** `google.com` concentra el 57,95 % de los positivos de validación y `weebly.com` el 98,03 % de los de prueba; solo 49 positivos de prueba quedan fuera de `weebly.com`. Esto se debe a que la partición conserva el dominio completo y esas agrupaciones son grandes. No se corrigió artificialmente para no ocultar la estructura real; la revisión está en `results/partition_audit.md`.

### 4.3 Normalización de `dom`

**Observación:** 226 filas y 32 valores de `dom` conservaban el prefijo `www.`. Además, ocho filas tenían mayúsculas en el dominio.

**Decisión:** crear `dom_normalizado` para agrupar, aplicando minúsculas, eliminación de espacios exteriores, eliminación del punto final y eliminación de prefijos `www.` o `wwwN.`.

**Resultado:** se obtuvieron 90 858 dominios únicos después de la limpieza. El EDA había reportado 90 859 al quitar solo `www.`; la diferencia adicional proviene de uniformar mayúsculas. La eliminación de duplicados exactos no cambia el número de dominios únicos. Los 24 dominios contradictorios se mantienen.

**Alcance:** `dom_normalizado` se usa para agrupar la partición, no como predictor.

### 4.4 Faltantes en `tld`

**Observación:** 14 registros no tienen `tld`; 13 son direcciones IP y uno es una URL malformada. En los 14 casos, `tld_len = 0`.

**Decisión:** como `tld` no forma parte del conjunto primario de predictores, no se imputa. Si en un experimento posterior se usa como variable categórica, se codificará como `sin_tld`, sin inventar un TLD.

`tld_len` sí se conserva como predictor numérico y no tiene faltantes. El detalle está en `results/tables/27_tld_faltantes_tratamiento.csv`.

### 4.5 Variables excluidas como predictores

| Variable | Decisión | Motivo |
|---|---|---|
| `url` | Excluida | Identificador único de alta cardinalidad; no debe usarse como predictor. |
| `dom` | Solo agrupación | Alta cardinalidad y riesgo de fuga; se usa para definir los grupos. |
| `tld` | Excluida del conjunto primario | 1 257 categorías observadas (1 258 con `sin_tld`); una codificación one-hot produciría una matriz muy dispersa. |
| `is_ip` | Excluida del conjunto primario | Solo 13 valores 1; baja variabilidad y aporte potencialmente inestable. |

`is_ip` se conserva en los datos para un análisis de sensibilidad posterior, pero no forma parte de los 21 predictores primarios.

---

## 5. Conjunto de predictores

Se definieron **21 predictores numéricos**:

`url_len`, `dom_len`, `tld_len`, `subdom_cnt`, `letter_cnt`, `digit_cnt`, `special_cnt`, `eq_cnt`, `qm_cnt`, `amp_cnt`, `dot_cnt`, `dash_cnt`, `under_cnt`, `letter_ratio`, `digit_ratio`, `spec_ratio`, `is_https`, `slash_cnt`, `entropy`, `path_len`, `query_len`.

**Decisiones:**

- No se aplicó imputación porque los 21 predictores no tienen faltantes.
- No se eliminaron valores extremos; pueden ser URL reales y son parte del fenómeno.
- No se eliminaron variables por correlación en esta fase. `url_len`–`letter_cnt` y `eq_cnt`–`amp_cnt` son redundantes, pero la decisión final depende del algoritmo y se evaluará en la Fase 4.
- `is_https` se conserva, aunque su diferencia entre clases puede reflejar un artefacto de recolección. Se recomienda comparar modelos con y sin esta variable en la fase posterior.
- `tld_len` se conserva; no equivale a usar la categoría `tld`.

El detalle está en `results/tables/25_predictores_tratamiento.csv`.

---

## 6. Comparación de esquemas de partición

Ambos esquemas se aplicaron sobre las 115 231 filas que quedaron después de eliminar duplicados exactos y usaron la semilla `20261025`.

### 6.1 Partición aleatoria estratificada

Se asignaron filas al azar dentro de cada clase, con proporciones objetivo 70/15/15. No hay filas ni URL repetidas entre particiones después de la limpieza, porque las URL ya son únicas.

| Partición | Filas | % | Clase 0 | Clase 1 | Tasa clase 1 |
|---|---:|---:|---:|---:|---:|
| Entrenamiento | 80 661 | 70,00 | 69 048 | 11 613 | 14,397 % |
| Validación | 17 284 | 15,00 | 14 796 | 2 488 | 14,395 % |
| Prueba | 17 286 | 15,00 | 14 797 | 2 489 | 14,399 % |

**Problema:** 1 653 dominios aparecen simultáneamente en entrenamiento y prueba. Esos dominios cubren 4 106 filas de prueba, el **23,75 %** de la partición de prueba. Esto constituye fuga de información a nivel de dominio y favorece una evaluación demasiado optimista si el modelo aprende patrones del dominio.

### 6.2 Partición agrupada por dominio

Se usó `dom_normalizado` como grupo. La asignación se hizo en dos estratos:

1. dominios que solo contienen clase 0;
2. dominios que contienen al menos un caso de clase 1.

Dentro de cada estrato, los grupos se ordenaron por tamaño descendente con desempate aleatorio y se asignaron a la partición con menor carga combinada de filas y casos de clase 1. Esto mantiene las proporciones de filas y clases sin separar un dominio entre particiones.

| Partición | Filas | % | Clase 0 | Clase 1 | Tasa clase 1 | Dominios | Dominio principal (filas; positivos) |
|---|---:|---:|---:|---:|---:|---:|---|
| Entrenamiento | 80 658 | 69,997 | 69 044 | 11 614 | 14,399 % | 64 110 | `pages.dev` (1,30 %; 9,04 %) |
| Validación | 17 291 | 15,006 | 14 808 | 2 483 | 14,360 % | 13 722 | `google.com` (8,39 %; 57,95 %) |
| Prueba | 17 282 | 14,998 | 14 789 | 2 493 | 14,425 % | 13 026 | `weebly.com` (14,21 %; 98,03 %) |

**Resultado de fuga:** no hay filas, URL ni dominios compartidos entre entrenamiento, validación y prueba. Las tres comparaciones tienen cero coincidencias.

### 6.3 Comparación directa

| Criterio | Aleatoria estratificada | Agrupada por dominio |
|---|---|---|
| Filas de entrenamiento | 80 661 | 80 658 |
| Filas de validación | 17 284 | 17 291 |
| Filas de prueba | 17 286 | 17 282 |
| Tasa de clase 1 en prueba | 14,399 % | 14,425 % |
| Dominios compartidos train–prueba | 1 653 | 0 |
| Filas de prueba con dominio visto en train | 4 106 (23,75 %) | 0 |
| URL compartidas | 0 | 0 |
| Filas exactas compartidas | 0 | 0 |

### 6.4 Esquema elegido

Se elige la **partición agrupada por dominio** como partición principal.

**Justificación:** evalúa la capacidad de generalizar a dominios no vistos y elimina la fuga por dominio. La partición aleatoria se conserva solo como referencia comparativa. La partición agrupada mantiene una proporción de clases prácticamente idéntica a la original y conserva un tamaño de prueba suficiente (17 282 filas).

**Costo:** la evaluación estará influida por la composición de los dominios grandes. En particular, `weebly.com` concentra el 14,21 % de las filas y el **98,03 % de los positivos** de prueba; `google.com`, el 8,39 % de las filas y el **57,95 % de los positivos** de validación. No se manipuló la asignación para ocultarlo; se reporta como limitación y se recomienda complementar las métricas globales con análisis por dominio en la fase posterior.

---

## 7. Preprocesamiento ajustado solo con entrenamiento

No se aplicó escalado, codificación ni imputación durante esta fase. Las únicas operaciones con efecto sobre el modelado son la eliminación de duplicados exactos y la asignación de particiones.

Se calcularon estadísticas descriptivas **solo con el conjunto de entrenamiento**: conteo, faltantes, media, desviación estándar, mínimo, cuartiles, mediana, máximo y rango intercuartílico de los 21 predictores. Están en `results/tables/28_estadisticas_entrenamiento.csv`.

**Regla para la Fase 4:** cualquier escalador, imputador, codificador o selección de variables que use información de los datos deberá ajustarse exclusivamente con entrenamiento y aplicarse después a validación y prueba. La prueba no debe usarse para elegir transformaciones ni hiperparámetros.

No se creó una matriz transformada ni se guardó un modelo. Los índices de partición permiten reconstruir los conjuntos sin duplicar el CSV original.

---

## 8. Reproducibilidad

Ejecución:

```bash
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python src/preprocessing.py
```

El script:

- lee `Dataset.csv` sin modificarlo;
- elimina duplicados exactos conservando la primera aparición;
- genera la partición aleatoria y la agrupada;
- escribe índices, tablas de diagnóstico y un resumen JSON;
- falla si no se cumplen los controles de integridad.

Los registros de consola y de validación se conservan localmente en `results/` y están excluidos de Git. La evidencia versionada es `results/tables/29_resumen_fase3.json` y las tablas de la partición.

---

## 9. Controles ejecutados

| Control | Resultado |
|---|---|
| SHA-256 del dataset antes y después | Igual |
| Filas de las tres particiones suman 115 231 | Verdadero |
| Clases de las tres particiones reconcilian con el conjunto limpio | Verdadero |
| Se eliminaron los 1 369 duplicados exactos | Verdadero |
| No quedaron URL repetidas en el conjunto de modelado | Verdadero |
| Ningún dominio aparece en dos particiones | Verdadero |
| Cero dominios compartidos entrenamiento–prueba en la partición principal | Verdadero |
| Cero URL compartidas entrenamiento–prueba | Verdadero |
| Cero filas compartidas entrenamiento–prueba | Verdadero |
| Todos los grupos fueron asignados | Verdadero |
| Los 21 predictores no tienen faltantes | Verdadero |
| Estadísticas ajustadas solo con entrenamiento | Verdadero |
| Dataset original no modificado | Verdadero |
| Modelos entrenados | Ninguno |

El resumen completo está en `results/tables/29_resumen_fase3.json`.

---

## 10. Limitaciones y riesgos residuales

1. La identificación de la fuente se apoya en la coincidencia de conteos, columnas y fecha, y en la coincidencia posterior de tamaño y SHA-256 con los metadatos del archivo publicado en Mendeley v2 (verificado el 2026-10-25).
2. El archivo publicado contiene 1 369 duplicados exactos aunque la versión 2 describe URL únicas y limpieza de duplicados. Se eliminaron para evitar duplicación, pero la discrepancia con la fuente queda registrada.
3. Los 24 dominios contradictorios se conservan. La etiqueta parece depender de la URL o del contenido, no solo del dominio; no se reetiquetaron sin evidencia.
4. La partición agrupada tiene concentración de dominios grandes en validación y prueba (`google.com` 57,95 % de positivos; `weebly.com` 98,03 %). Las métricas globales pueden estar dominadas por esos casos; se recomienda análisis por dominio y no afirmar generalización poblacional.
5. La partición es aleatoria respecto de grupos, no temporal. No se dispone de fecha de recolección por URL, por lo que no puede hacerse una validación temporal.
6. `is_https` puede capturar un artefacto de recolección. Se conserva inicialmente, pero debe evaluarse su impacto.
7. `is_ip` se excluyó del conjunto primario por baja variabilidad; su utilidad real debe comprobarse en un análisis de sensibilidad, no asumirse.
8. No se aplicó selección de variables. La redundancia entre predictores queda para la Fase 4.
9. La partición no demuestra por sí sola que el modelo generalice a datos externos; solo define un protocolo reproducible y sin fuga de dominio.

---

## 11. Entregables generados

| Archivo | Contenido |
|---|---|
| `results/tables/19_particion_aleatoria_indices.csv` | Índices de la partición aleatoria. |
| `results/tables/20_particion_agrupada_indices.csv` | Índices de la partición principal. |
| `results/tables/21_comparacion_particiones.csv` | Comparación de ambos esquemas. |
| `results/tables/22_resumen_particion_principal.csv` | Resumen de la partición elegida. |
| `results/tables/23_fuga_informacion.csv` | Solapamiento de filas, URL y dominios. |
| `results/tables/24_dominios_contradictorios_particion.csv` | Los 24 dominios y su partición. |
| `results/tables/25_predictores_tratamiento.csv` | Rol y tratamiento de cada variable. |
| `results/tables/26_duplicados_eliminados.csv` | Trazabilidad de los 1 369 duplicados. |
| `results/tables/27_tld_faltantes_tratamiento.csv` | Los 14 faltantes de `tld`. |
| `results/tables/28_estadisticas_entrenamiento.csv` | Estadísticas calculadas solo con entrenamiento. |
| `results/tables/29_resumen_fase3.json` | Resumen estructurado y controles. |
| `results/phase3_console.log` | Registro local de ejecución; no versionado. |
| `results/phase3_validation.log` | Validación local independiente; no versionada. |

---

## 12. Referencia de la fuente

Dam Minh, Linh; Tran Cong, Hung (2026). *URL-Phish: A Feature-Engineered Dataset for Phishing Detection* (Versión 2). Mendeley Data. DOI: `10.17632/65z9twcx3r.2`. Licencia CC BY 4.0. https://data.mendeley.com/datasets/65z9twcx3r/2

---

## 13. Criterio de cierre de la fase

La Fase 3 fue **reportada como completada por el usuario el 2026-10-25**, quien autorizó continuar con la Fase 4. Por tanto, se considera cerrada para efectos de continuidad del proyecto.

Las decisiones que sustentan esta fase son:

- la eliminación de los 1 369 duplicados exactos;
- la conservación de los 24 dominios contradictorios;
- la exclusión de `url`, `dom`, `tld` e `is_ip` como predictores;
- la partición agrupada 70/15/15 con semilla `20261025`;
- la concentración de dominios grandes en validación y prueba.

No se entrenaron modelos en esta fase. Cualquier entrenamiento posterior requiere aprobar el diseño de la Fase 4 y autorizar las dependencias necesarias.
