# Detección de phishing mediante características de URL

Proyecto académico de **Inteligencia Artificial — Segunda unidad**, de la carrera de **Ingeniería de Sistemas** de la **Universidad Andina del Cusco**.

El proyecto analiza un conjunto de URL etiquetadas como benignas o de phishing, documenta el análisis exploratorio, construye una partición agrupada por dominio y diseña tres modelos candidatos de aprendizaje automático. **Los modelos están diseñados, pero todavía no han sido entrenados ni evaluados.** Por lo tanto, este repositorio no contiene métricas de rendimiento, modelos serializados ni conclusiones predictivas.

## Estado actual

- EDA ejecutado y documentado.
- Preprocesamiento y partición agrupada 70/15/15 ejecutados.
- Diseño preliminar de modelos documentado.
- Informe académico en APA 7 con 27 páginas.
- **Modelos entrenados: 0.**
- **Métricas de rendimiento calculadas: ninguna.**
- **Licencia del código: pendiente de decisión del autor.**
- Repositorio Git local inicializado en `main`, sin commit ni push.


## Dataset

- **Nombre:** URL-Phish: A Feature-Engineered Dataset for Phishing Detection.
- **Versión:** 2.
- **Autores:** Linh Dam Minh y Hung Tran Cong.
- **Editor:** Mendeley Data.
- **DOI:** [10.17632/65z9twcx3r.2](https://doi.org/10.17632/65z9twcx3r.2).
- **Licencia verificada:** Creative Commons Attribution 4.0 International (**CC BY 4.0**), SPDX `cc-by-4.0`.
- **Archivo local:** `Dataset.csv`, 15 149 338 bytes.
- **SHA-256:** `d68b3cd0648dcf9c775347416ad1a8995e8a025921fbe3871ca6158d4db3c3a1`.
- **Contenido:** 116 600 filas y 26 columnas; 100 000 casos benignos (`label = 0`) y 16 600 de phishing (`label = 1`).

La licencia permite compartir y adaptar el conjunto con atribución. El archivo se distribuye sin modificaciones, conserva su licencia original y no se relicencia bajo la licencia del código. La atribución, el DOI, el hash y las condiciones están detalladas en [docs/FUENTE_DATOS.md](docs/FUENTE_DATOS.md).

> **Advertencia:** el dataset contiene URL que pueden ser maliciosas o fraudulentas. No abras esas URL en un navegador. Trátalas como texto y procesa el archivo en un entorno controlado.

## Estructura del repositorio

```text
.
├── Dataset.csv
├── README.md
├── AGENTS.md
├── requirements.txt
├── requirements-report.txt
├── figures/
│   └── fig01…fig06 (.png)
├── notebooks/
│   └── 01_analisis_exploratorio.ipynb
├── results/
│   ├── eda_summary.md
│   ├── model_design.md
│   ├── partition_audit.md
│   ├── phase3_preprocessing.md
│   └── tables/
│       └── 00…29 (.csv/.json)
└── src/
    ├── eda.py
    ├── generate_report.py
    └── preprocessing.py
```

No se versionan `.venv/`, `__pycache__/`, archivos `*.pyc`, logs locales ni temporales. Los logs permanecen en el equipo, pero están excluidos mediante `.gitignore`.

## Requisitos

- Python 3.12.3.
- Dependencias del análisis: ver [requirements.txt](requirements.txt).
- Dependencias del informe: ver [requirements-report.txt](requirements-report.txt).
- LibreOffice 24.2 o compatible, con el módulo UNO, para actualizar campos y exportar el PDF.
- `scikit-learn`, `joblib` y `xgboost` **no están instalados**; se requieren únicamente para una fase posterior de entrenamiento, todavía no autorizada.

## Instalación

Desde la raíz del repositorio:

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

En el equipo donde se preparó el proyecto, `python3 -m venv` no pudo crear el entorno porque faltaba `ensurepip` (`python3.12-venv`). Se usó `python3 -m virtualenv .venv`. Si ocurre lo mismo, instala el paquete del sistema correspondiente o utiliza `virtualenv`.

## Ejecución

Los comandos de ayuda se verificaron durante la preparación del repositorio; no se reejecutaron el EDA ni el preprocesamiento para evitar sobrescribir resultados existentes.

```bash
.venv/bin/python src/eda.py --help
.venv/bin/python src/preprocessing.py --help
```

Ejecución completa, solo si se desea reproducir o actualizar los resultados:

```bash
.venv/bin/python src/eda.py
.venv/bin/python src/preprocessing.py
```

Advertencia: estos scripts escriben en `figures/` y `results/tables/`. Reejecutarlos puede sobrescribir los resultados versionados. Conserva una copia antes de hacerlo.

### Regenerar el PDF del informe

El DOCX es el archivo editable principal. El PDF se puede regenerar con:

```bash
libreoffice --headless --convert-to pdf --outdir report report/informe_segunda_unidad.docx
```

También existe `src/generate_report.py`, que construye el DOCX con `python-docx` y LibreOffice/UNO. Requiere el Python del sistema, no el `.venv`, y no se reejecutó durante la preparación del repositorio. No se debe ejecutar si solo se quiere leer o entregar el informe ya terminado.

## Metodología

1. **EDA:** revisión de dimensiones, tipos, faltantes, duplicados, distribuciones, correlaciones, dominios y posibles fugas de información.
2. **Limpieza:** eliminación de 1 369 duplicados exactos; quedaron 115 231 filas.
3. **Predictores:** 21 variables numéricas. `url`, `dom` y `tld` se excluyeron como predictores; `dom` normalizado se usó solo para agrupar. `is_ip` quedó fuera del conjunto primario por ser casi constante.
4. **Partición principal:** agrupada por dominio, 70/15/15, semilla `20261025`. No hay dominios compartidos entre entrenamiento y prueba.
5. **Comparación:** la partición aleatoria se usó solo como diagnóstico de fuga; compartía 1 653 dominios y el 23,75 % de la prueba con entrenamiento.
6. **Diseño de modelos:** Regresión Logística como línea base, Random Forest y XGBoost condicionado. La selección se haría con validación y la prueba se reservaría para una evaluación final única.
7. **Estado:** el diseño está documentado; el entrenamiento y la evaluación no se ejecutaron.

### Concentración de dominios

La partición agrupada evita compartir dominios, pero no elimina la concentración estructural:

- `google.com` concentra el 57,95 % de los positivos de validación.
- `weebly.com` concentra el 98,03 % de los positivos de prueba.
- Solo 49 positivos de prueba quedan fuera de `weebly.com`.

Por eso, las futuras métricas globales deberán interpretarse como una prueba de estrés del dominio dominante, no como evidencia de generalización poblacional. El análisis está en [results/partition_audit.md](results/partition_audit.md).

## Modelos diseñados

| Modelo | Rol | Estado |
|---|---|---|
| Regresión Logística | Línea base interpretable | Diseñada, no entrenada |
| Random Forest | Relaciones no lineales e interacciones | Diseñado, no entrenado |
| XGBoost | Boosting regularizado, candidato condicional | Diseñado, no entrenado; dependencia no instalada |

No existen resultados de accuracy, precision, recall, F1, ROC-AUC ni PR-AUC. Cualquier cifra de rendimiento que no esté acompañada por un artefacto reproducible debe considerarse inválida.

El diseño completo, las configuraciones y el protocolo de evaluación están en [results/model_design.md](results/model_design.md).

## Resultados y evidencia

- [Informe del EDA](results/eda_summary.md).
- [Preprocesamiento y partición](results/phase3_preprocessing.md).
- [Auditoría de la partición](results/partition_audit.md).
- [Diseño de modelos](results/model_design.md).
- [Tablas y resúmenes](results/tables/).
- [Figuras](figures/).
- [Verificación de entrega](docs/auditoria/verificacion_entrega.md).
- [Auditoría APA e índices](docs/auditoria/auditoria_apa_indices.md).
- [Auditoría histórica](docs/auditoria/auditoria_final.md).
- [Auditoría de preparación del repositorio](docs/auditoria/auditoria_repositorio.md).

## Limitaciones

- No hay validación temporal: no se dispone de fecha de recolección por URL.
- No hay validación externa en otro dataset o periodo.
- La partición es agrupada por dominio, pero la evaluación futura estaría dominada por pocos dominios.
- Las características son solo léxicas y estructurales de la URL; no se analiza el contenido de la página.
- Existen 24 dominios con etiquetas contradictorias, conservados y documentados.
- El desbalance es fuerte: aproximadamente 6,02 casos benignos por cada caso de phishing.
- `is_https` podría actuar como artefacto del proceso de recolección.
- No se han entrenado modelos ni calculado métricas; no se puede afirmar capacidad predictiva.

## Reproducibilidad y trazabilidad

- El SHA-256 de `Dataset.csv` se verificó antes y después del preprocesamiento y al preparar el repositorio; no cambió.
- La partición se puede reconstruir desde `results/tables/20_particion_agrupada_indices.csv`.
- Los resultados del EDA y de la Fase 3 se conservan en `results/tables/`.
- Los documentos de continuidad registran decisiones, límites y pendientes.
- Los logs de ejecución son locales y no se versionan; la evidencia versionada son las tablas, figuras y reportes.

## Licencia

- **Dataset:** CC BY 4.0, con atribución a Dam Minh y Tran Cong (2026), versión 2, DOI `10.17632/65z9twcx3r.2`. El dataset no se relicencia.
- **Código:** no se ha creado un archivo `LICENSE`. La licencia del código queda pendiente de decisión del autor y no debe inferirse de la licencia del dataset.

## Referencia principal del dataset

Dam Minh, L., & Tran Cong, H. (2026). *URL-Phish: A feature-engineered dataset for phishing detection* (Version 2) [Data set]. Mendeley Data. https://doi.org/10.17632/65z9twcx3r.2
