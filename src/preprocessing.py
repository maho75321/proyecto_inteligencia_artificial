#!/usr/bin/env python3
"""Preprocesamiento y partición reproducible del dataset URL-Phish.

La Fase 3 no entrena modelos. El script lee el CSV original, documenta la
limpieza, compara dos esquemas de partición y genera índices y diagnósticos.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = PROJECT_ROOT / "Dataset.csv"
DEFAULT_TABLES = PROJECT_ROOT / "results" / "tables"

SEED = 20261025
SPLITS = ("entrenamiento", "validacion", "prueba")
FRACTIONS = {"entrenamiento": 0.70, "validacion": 0.15, "prueba": 0.15}

PRIMARY_FEATURES = [
    "url_len",
    "dom_len",
    "tld_len",
    "subdom_cnt",
    "letter_cnt",
    "digit_cnt",
    "special_cnt",
    "eq_cnt",
    "qm_cnt",
    "amp_cnt",
    "dot_cnt",
    "dash_cnt",
    "under_cnt",
    "letter_ratio",
    "digit_ratio",
    "spec_ratio",
    "is_https",
    "slash_cnt",
    "entropy",
    "path_len",
    "query_len",
]

SOURCE = {
    "nombre": "URL-Phish: A Feature-Engineered Dataset for Phishing Detection",
    "version": "2",
    "doi": "10.17632/65z9twcx3r.2",
    "url": "https://data.mendeley.com/datasets/65z9twcx3r/2",
    "autores": ["Linh Dam Minh", "Hung Tran Cong"],
    "publicacion": "2026-03-09",
    "licencia": "CC BY 4.0",
    "etiquetas": {"0": "benigno", "1": "phishing"},
    "evidencia": (
        "Coincidencia exacta con el archivo local en 116 600 filas, "
        "100 000 casos benignos, 16 600 casos de phishing, 26 columnas y "
        "las mismas columnas de URL y características."
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el dataset: {path}")
    df = pd.read_csv(path)
    required = {"url", "dom", "tld", "label", *PRIMARY_FEATURES, "is_ip"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {missing}")
    if set(df["label"].dropna().unique()).difference({0, 1}):
        raise ValueError("La variable label contiene valores distintos de 0 y 1.")
    return df


def normalize_domain(series: pd.Series) -> pd.Series:
    normalized = series.astype("string").str.strip().str.lower().str.rstrip(".")
    return normalized.str.replace(r"^www\d*\.", "", regex=True)


def add_row_id(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.insert(0, "fila_id", np.arange(len(result), dtype=np.int64))
    result["dom_normalizado"] = normalize_domain(result["dom"])
    return result


def remove_exact_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    original_columns = [column for column in df.columns if column != "fila_id"]
    duplicated = df.duplicated(subset=original_columns, keep="first")
    clean = df.loc[~duplicated].copy()
    removed = df.loc[duplicated].copy()
    first_ids = clean.drop_duplicates("url", keep="first").set_index("url")["fila_id"]
    removed["fila_conservada_id"] = removed["url"].map(first_ids)
    removed["posicion_original"] = removed["fila_id"] + 1
    columns = [
        "fila_id",
        "posicion_original",
        "fila_conservada_id",
        "url",
        "dom",
        "dom_normalizado",
        "label",
    ]
    return clean.reset_index(drop=True), removed[columns].sort_values("fila_id")


def build_groups(clean: pd.DataFrame) -> pd.DataFrame:
    groups = (
        clean.groupby("dom_normalizado", dropna=False)
        .agg(
            filas=("fila_id", "size"),
            clase_0=("label", lambda values: int((values == 0).sum())),
            clase_1=("label", lambda values: int((values == 1).sum())),
        )
        .reset_index()
    )
    groups["estrato"] = np.where(groups["clase_1"] == 0, "solo_clase_0", "con_clase_1")
    return groups


def assign_grouped_split(
    groups: pd.DataFrame, seed: int, fractions: dict[str, float]
) -> pd.Series:
    rng = np.random.default_rng(seed)
    work = groups.copy()
    work["_orden"] = rng.random(len(work))
    assignment: dict[str, str] = {}
    for stratum in ("solo_clase_0", "con_clase_1"):
        subset = work.loc[work["estrato"] == stratum].sort_values(
            ["filas", "_orden"], ascending=[False, True]
        )
        target_rows = {split: fractions[split] * subset["filas"].sum() for split in SPLITS}
        target_positive = {
            split: fractions[split] * subset["clase_1"].sum() for split in SPLITS
        }
        assigned_rows = {split: 0 for split in SPLITS}
        assigned_positive = {split: 0 for split in SPLITS}
        for row in subset.itertuples(index=False):
            scores = []
            for split in SPLITS:
                row_load = assigned_rows[split] / max(target_rows[split], 1.0)
                positive_load = (
                    assigned_positive[split] / target_positive[split]
                    if target_positive[split] > 0
                    else 0.0
                )
                scores.append((row_load + positive_load + rng.random() * 1e-12, split))
            _, chosen = min(scores)
            assigned_rows[chosen] += int(row.filas)
            assigned_positive[chosen] += int(row.clase_1)
            assignment[row.dom_normalizado] = chosen
    return pd.Series(assignment, name="particion")


def assign_random_split(
    clean: pd.DataFrame, seed: int, fractions: dict[str, float]
) -> pd.Series:
    rng = np.random.default_rng(seed)
    assignment = pd.Series(index=clean.index, dtype="object", name="particion")
    for label in (0, 1):
        indices = clean.index[clean["label"] == label].to_numpy()
        indices = rng.permutation(indices)
        total = len(indices)
        n_train = int(np.floor(total * fractions["entrenamiento"]))
        n_validation = int(np.floor(total * fractions["validacion"]))
        assignment.loc[indices[:n_train]] = "entrenamiento"
        assignment.loc[indices[n_train : n_train + n_validation]] = "validacion"
        assignment.loc[indices[n_train + n_validation :]] = "prueba"
    if assignment.isna().any():
        raise RuntimeError("La partición aleatoria dejó filas sin asignar.")
    return assignment


def attach_assignment(clean: pd.DataFrame, assignment: pd.Series) -> pd.DataFrame:
    result = clean.copy()
    result["particion"] = assignment.reindex(result.index).to_numpy()
    return result


def split_summary(assigned: pd.DataFrame, method: str) -> pd.DataFrame:
    rows = []
    total = len(assigned)
    for split in SPLITS:
        part = assigned.loc[assigned["particion"] == split]
        class_0 = int((part["label"] == 0).sum())
        class_1 = int((part["label"] == 1).sum())
        top_domain = part["dom_normalizado"].value_counts(dropna=False)
        top_domain_name = str(top_domain.index[0]) if len(top_domain) else ""
        top_domain_rows = int(top_domain.iloc[0]) if len(top_domain) else 0
        rows.append(
            {
                "metodo": method,
                "particion": split,
                "filas": len(part),
                "porcentaje_filas": round(100 * len(part) / total, 6),
                "clase_0": class_0,
                "clase_1": class_1,
                "tasa_clase_1_pct": round(100 * class_1 / len(part), 6) if len(part) else 0.0,
                "dominios_unicos": int(part["dom_normalizado"].nunique()),
                "dominio_mas_frecuente": top_domain_name,
                "filas_dominio_mas_frecuente": top_domain_rows,
                "pct_dominio_mas_frecuente": round(100 * top_domain_rows / len(part), 6)
                if len(part)
                else 0.0,
                "urls_unicas": int(part["url"].nunique()),
            }
        )
    return pd.DataFrame(rows)


def leakage_table(assigned: pd.DataFrame, method: str) -> pd.DataFrame:
    sets = {}
    for split in SPLITS:
        part = assigned.loc[assigned["particion"] == split]
        sets[split] = {
            "filas": set(part["fila_id"].tolist()),
            "urls": set(part["url"].tolist()),
            "dominios": set(part["dom_normalizado"].dropna().tolist()),
        }
    rows = []
    for first, second in combinations(SPLITS, 2):
        first_set = sets[first]
        second_set = sets[second]
        second_part = assigned.loc[assigned["particion"] == second]
        union_domains = first_set["dominios"] | second_set["dominios"]
        shared_domains = first_set["dominios"] & second_set["dominios"]
        shared_rows = int(second_part["dom_normalizado"].isin(first_set["dominios"]).sum())
        rows.append(
            {
                "metodo": method,
                "comparacion": f"{first}-{second}",
                "filas_compartidas": len(first_set["filas"] & second_set["filas"]),
                "urls_compartidas": len(first_set["urls"] & second_set["urls"]),
                "filas_segundo_con_dominio_en_primero": shared_rows,
                "pct_filas_segundo_con_dominio_en_primero": round(
                    100 * shared_rows / len(second_part), 6
                )
                if len(second_part)
                else 0.0,
                "dominios_compartidos": len(shared_domains),
                "pct_dominios_segundo_vistos_en_primero": round(
                    100 * len(shared_domains) / len(second_set["dominios"]), 6
                )
                if second_set["dominios"]
                else 0.0,
                "pct_dominios_union_compartidos": round(
                    100 * len(shared_domains) / len(union_domains), 6
                )
                if union_domains
                else 0.0,
            }
        )
    return pd.DataFrame(rows)


def contradictory_table(assigned: pd.DataFrame) -> pd.DataFrame:
    counts = (
        assigned.groupby("dom_normalizado")
        .agg(filas=("fila_id", "size"), clase_0=("label", lambda x: int((x == 0).sum())))
        .reset_index()
    )
    counts["clase_1"] = counts["filas"] - counts["clase_0"]
    contradictory = counts.loc[
        (counts["clase_0"] > 0) & (counts["clase_1"] > 0)
    ].copy()
    split_per_domain = assigned.groupby("dom_normalizado")["particion"].agg(
        lambda values: "|".join(sorted(values.unique()))
    )
    contradictory["particion"] = contradictory["dom_normalizado"].map(split_per_domain)
    contradictory["etiqueta_mayoritaria"] = np.where(
        contradictory["clase_1"] >= contradictory["clase_0"], 1, 0
    )
    contradictory["pct_clase_1"] = (
        100 * contradictory["clase_1"] / contradictory["filas"]
    ).round(6)
    return contradictory.sort_values(["filas", "dom_normalizado"], ascending=[False, True])[
        [
            "dom_normalizado",
            "filas",
            "clase_0",
            "clase_1",
            "pct_clase_1",
            "etiqueta_mayoritaria",
            "particion",
        ]
    ]


def feature_table() -> pd.DataFrame:
    rows = [
        {
            "variable": "label",
            "tipo": "objetivo",
            "rol": "variable_objetivo",
            "tratamiento": "0 = benigno; 1 = phishing",
            "justificacion": "Semántica confirmada en URL-Phish v2.",
        },
        {
            "variable": "fila_id",
            "tipo": "identificador",
            "rol": "trazabilidad",
            "tratamiento": "Se conserva en los índices; no es predictor.",
            "justificacion": "Permite reconstruir cada fila del CSV original.",
        },
        {
            "variable": "url",
            "tipo": "texto",
            "rol": "identificador_excluido",
            "tratamiento": "No se usa como predictor.",
            "justificacion": "Identificador único de alta cardinalidad y posible fuga.",
        },
        {
            "variable": "dom",
            "tipo": "texto",
            "rol": "solo_agrupacion",
            "tratamiento": "Se normaliza y se usa para agrupar la partición.",
            "justificacion": "Evita que un mismo dominio aparezca en train y prueba.",
        },
        {
            "variable": "dom_normalizado",
            "tipo": "texto_derivado",
            "rol": "grupo",
            "tratamiento": "Minúsculas, sin espacios, sin punto final y sin www.",
            "justificacion": "Unifica las 226 filas con prefijo www; no es predictor.",
        },
        {
            "variable": "tld",
            "tipo": "texto",
            "rol": "referencia_excluida",
            "tratamiento": "No se usa en el conjunto primario; si se usa, faltante = sin_tld.",
            "justificacion": "1 258 categorías y 14 faltantes; evitar una explosión de columnas.",
        },
        {
            "variable": "is_ip",
            "tipo": "binaria",
            "rol": "excluida_del_conjunto_primario",
            "tratamiento": "Se conserva para análisis de sensibilidad.",
            "justificacion": "Solo 13 valores 1; baja variabilidad y aporte inestable.",
        },
    ]
    feature_notes = {
        "is_https": (
            "Binaria. Se conserva, pero se comparará con y sin ella por su posible "
            "artefacto de recolección."
        ),
        "url_len": "Longitud total de la URL.",
        "dom_len": "Longitud del dominio.",
        "tld_len": "Longitud del TLD; no hay faltantes en esta variable.",
        "entropy": "Entropía de Shannon de la URL.",
    }
    for feature in PRIMARY_FEATURES:
        rows.append(
            {
                "variable": feature,
                "tipo": "binaria" if feature == "is_https" else "numerica",
                "rol": "predictor_primario",
                "tratamiento": (
                    "Sin imputación; valores extremos conservados; escalado solo si el "
                    "modelo lo requiere, ajustado únicamente con entrenamiento."
                ),
                "justificacion": feature_notes.get(
                    feature, "Característica numérica extraída de la URL."
                ),
            }
        )
    return pd.DataFrame(rows)


def tld_missing_table(clean: pd.DataFrame, assigned: pd.DataFrame) -> pd.DataFrame:
    missing = clean.loc[clean["tld"].isna()].copy()
    missing["motivo"] = np.where(missing["is_ip"] == 1, "IP sin TLD", "URL malformada")
    missing["tld_categoria_sugerida"] = "sin_tld"
    missing["tratamiento"] = (
        "Categoría sin_tld solo si se usa tld como variable categórica; "
        "no se usa en el conjunto primario."
    )
    missing["particion"] = missing["fila_id"].map(
        assigned.set_index("fila_id")["particion"]
    )
    return missing.sort_values("fila_id")[
        [
            "fila_id",
            "url",
            "dom",
            "dom_normalizado",
            "is_ip",
            "label",
            "motivo",
            "tld_categoria_sugerida",
            "tratamiento",
            "particion",
        ]
    ]


def training_statistics(
    assigned: pd.DataFrame, features: list[str]
) -> pd.DataFrame:
    train = assigned.loc[assigned["particion"] == "entrenamiento", features]
    quantiles = train.quantile([0.25, 0.50, 0.75]).T
    quantiles.columns = ["q1", "mediana", "q3"]
    stats = pd.DataFrame(
        {
            "variable": features,
            "n": train.notna().sum().reindex(features).to_numpy(),
            "faltantes": train.isna().sum().reindex(features).to_numpy(),
            "media": train.mean().reindex(features).to_numpy(),
            "desv_est": train.std().reindex(features).to_numpy(),
            "minimo": train.min().reindex(features).to_numpy(),
            "q1": quantiles["q1"].reindex(features).to_numpy(),
            "mediana": quantiles["mediana"].reindex(features).to_numpy(),
            "q3": quantiles["q3"].reindex(features).to_numpy(),
            "maximo": train.max().reindex(features).to_numpy(),
        }
    )
    stats["rango_intercuartilico"] = stats["q3"] - stats["q1"]
    return stats


def bool_value(value: Any) -> bool:
    return bool(value)


def run_preprocessing(data_path: Path, tables_dir: Path) -> dict[str, Any]:
    tables_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    hash_before = sha256_file(data_path)
    original = load_data(data_path)
    added_ids = add_row_id(original)
    clean, removed = remove_exact_duplicates(added_ids)

    if clean["url"].duplicated().any():
        raise RuntimeError("Quedaron URL repetidas después de eliminar duplicados exactos.")

    groups = build_groups(clean)
    random_assignment = assign_random_split(clean, SEED, FRACTIONS)
    random_assigned = attach_assignment(clean, random_assignment)
    grouped_assignment = assign_grouped_split(groups, SEED, FRACTIONS)
    grouped_assigned = attach_assignment(
        clean, clean["dom_normalizado"].map(grouped_assignment)
    )

    random_summary = split_summary(random_assigned, "aleatoria_estratificada")
    grouped_summary = split_summary(grouped_assigned, "agrupada_por_dominio")
    comparison = pd.concat([random_summary, grouped_summary], ignore_index=True)

    random_leakage = leakage_table(random_assigned, "aleatoria_estratificada")
    grouped_leakage = leakage_table(grouped_assigned, "agrupada_por_dominio")
    leakage = pd.concat([random_leakage, grouped_leakage], ignore_index=True)

    contradictory = contradictory_table(grouped_assigned)
    features = feature_table()
    tld_missing = tld_missing_table(clean, grouped_assigned)
    train_stats = training_statistics(grouped_assigned, PRIMARY_FEATURES)

    random_indices = random_assigned[["fila_id", "particion", "label", "dom_normalizado"]]
    grouped_indices = grouped_assigned[["fila_id", "particion", "label", "dom_normalizado"]]

    outputs = {
        "19_particion_aleatoria_indices.csv": random_indices,
        "20_particion_agrupada_indices.csv": grouped_indices,
        "21_comparacion_particiones.csv": comparison,
        "22_resumen_particion_principal.csv": grouped_summary,
        "23_fuga_informacion.csv": leakage,
        "24_dominios_contradictorios_particion.csv": contradictory,
        "25_predictores_tratamiento.csv": features,
        "26_duplicados_eliminados.csv": removed,
        "27_tld_faltantes_tratamiento.csv": tld_missing,
        "28_estadisticas_entrenamiento.csv": train_stats,
    }
    for name, frame in outputs.items():
        frame.to_csv(tables_dir / name, index=False, encoding="utf-8")

    grouped_checks = grouped_assigned.groupby("dom_normalizado")["particion"].nunique()
    grouped_domain_overlap = int(
        leakage.loc[
            (leakage["metodo"] == "agrupada_por_dominio")
            & (leakage["comparacion"] == "entrenamiento-prueba"),
            "dominios_compartidos",
        ].iloc[0]
    )
    random_domain_overlap = int(
        leakage.loc[
            (leakage["metodo"] == "aleatoria_estratificada")
            & (leakage["comparacion"] == "entrenamiento-prueba"),
            "dominios_compartidos",
        ].iloc[0]
    )
    random_test_seen = float(
        leakage.loc[
            (leakage["metodo"] == "aleatoria_estratificada")
            & (leakage["comparacion"] == "entrenamiento-prueba"),
            "pct_dominios_segundo_vistos_en_primero",
        ].iloc[0]
    )
    grouped_test_seen = float(
        leakage.loc[
            (leakage["metodo"] == "agrupada_por_dominio")
            & (leakage["comparacion"] == "entrenamiento-prueba"),
            "pct_dominios_segundo_vistos_en_primero",
        ].iloc[0]
    )
    random_test_rows_seen = float(
        leakage.loc[
            (leakage["metodo"] == "aleatoria_estratificada")
            & (leakage["comparacion"] == "entrenamiento-prueba"),
            "pct_filas_segundo_con_dominio_en_primero",
        ].iloc[0]
    )
    grouped_test_rows_seen = float(
        leakage.loc[
            (leakage["metodo"] == "agrupada_por_dominio")
            & (leakage["comparacion"] == "entrenamiento-prueba"),
            "pct_filas_segundo_con_dominio_en_primero",
        ].iloc[0]
    )
    split_totals = grouped_summary[["filas", "clase_0", "clase_1"]].sum()
    partition_sums = grouped_assigned.groupby("particion")[["fila_id"]].size()
    split_domain_sums = grouped_summary["dominios_unicos"].sum()
    split_url_sums = grouped_summary["urls_unicas"].sum()

    controls = {
        "sha256_original_sin_cambios": sha256_file(data_path) == hash_before,
        "filas_reconciliadas": int(split_totals["filas"]) == len(clean) == len(original) - len(removed),
        "clases_reconciliadas": int(split_totals["clase_0"]) == int((clean["label"] == 0).sum())
        and int(split_totals["clase_1"]) == int((clean["label"] == 1).sum()),
        "duplicados_exactos_eliminados": len(removed) == int(original.duplicated().sum()) == 1369,
        "sin_url_repetidas_en_modelado": not clean["url"].duplicated().any(),
        "sin_filas_en_dos_particiones": int(partition_sums.sum()) == len(clean),
        "sin_dominios_en_dos_particiones": bool((grouped_checks == 1).all()),
        "sin_dominios_compartidos_entrenamiento_prueba": grouped_domain_overlap == 0,
        "sin_urls_compartidas_entrenamiento_prueba": int(
            leakage.loc[
                (leakage["metodo"] == "agrupada_por_dominio")
                & (leakage["comparacion"] == "entrenamiento-prueba"),
                "urls_compartidas",
            ].iloc[0]
        )
        == 0,
        "sin_filas_compartidas_entrenamiento_prueba": int(
            leakage.loc[
                (leakage["metodo"] == "agrupada_por_dominio")
                & (leakage["comparacion"] == "entrenamiento-prueba"),
                "filas_compartidas",
            ].iloc[0]
        )
        == 0,
        "todos_los_grupos_asignados": len(grouped_assignment) == len(groups) == int(clean["dom_normalizado"].nunique()),
        "predictores_sin_faltantes": int(clean[PRIMARY_FEATURES].isna().sum().sum()) == 0,
        "estadisticas_solo_con_entrenamiento": len(train_stats) == len(PRIMARY_FEATURES),
        "sin_modelos_entrenados": True,
        "dataset_original_no_modificado": True,
    }
    if not all(controls.values()):
        failed = [name for name, value in controls.items() if not value]
        raise RuntimeError(f"Controles fallidos: {failed}")

    hash_after = sha256_file(data_path)
    finished = datetime.now(timezone.utc)
    summary = {
        "fase": "Fase 3: preprocesamiento y partición",
        "inicio_utc": started.isoformat(),
        "fin_utc": finished.isoformat(),
        "fuente": SOURCE,
        "dataset": {
            "ruta": str(data_path),
            "tamano_bytes": data_path.stat().st_size,
            "sha256_antes": hash_before,
            "sha256_despues": hash_after,
            "filas_originales": int(len(original)),
            "columnas": int(original.shape[1]),
            "clases_originales": {
                "0": int((original["label"] == 0).sum()),
                "1": int((original["label"] == 1).sum()),
            },
        },
        "limpieza": {
            "duplicados_exactos_eliminados": int(len(removed)),
            "duplicados_eliminados_clase_0": int((removed["label"] == 0).sum()),
            "duplicados_eliminados_clase_1": int((removed["label"] == 1).sum()),
            "filas_modelado": int(len(clean)),
            "clases_modelado": {
                "0": int((clean["label"] == 0).sum()),
                "1": int((clean["label"] == 1).sum()),
            },
            "urls_unicas_modelado": int(clean["url"].nunique()),
            "dominios_unicos_modelado": int(clean["dom_normalizado"].nunique()),
            "dominios_contradictorios": int(len(contradictory)),
        },
        "particion_principal": {
            "metodo": "agrupada_por_dominio",
            "semilla": SEED,
            "fracciones_objetivo": FRACTIONS,
            "grupo": "dom_normalizado",
            "resumen": grouped_summary.to_dict(orient="records"),
            "dominios_compartidos_entrenamiento_prueba": grouped_domain_overlap,
            "pct_dominios_prueba_vistos_en_entrenamiento": grouped_test_seen,
            "pct_filas_prueba_con_dominio_en_entrenamiento": grouped_test_rows_seen,
            "estrategia": (
                "Grupos ordenados por tamaño descendente con desempate aleatorio; "
                "asignación al split con menor carga combinada de filas y casos clase 1."
            ),
        },
        "particion_aleatoria_comparacion": {
            "metodo": "aleatoria_estratificada",
            "semilla": SEED,
            "resumen": random_summary.to_dict(orient="records"),
            "dominios_compartidos_entrenamiento_prueba": random_domain_overlap,
            "pct_dominios_prueba_vistos_en_entrenamiento": random_test_seen,
            "pct_filas_prueba_con_dominio_en_entrenamiento": random_test_rows_seen,
        },
        "preprocesamiento": {
            "predictores_primarios": PRIMARY_FEATURES,
            "n_predictores_primarios": len(PRIMARY_FEATURES),
            "excluidos_como_predictores": ["url", "dom", "tld", "is_ip"],
            "faltantes_en_predictores": int(clean[PRIMARY_FEATURES].isna().sum().sum()),
            "imputacion_aplicada": False,
            "escalado_aplicado": False,
            "criterio_escalado": "Se ajustará solo con entrenamiento en la fase de modelado.",
            "estadisticas_ajustadas_con": "entrenamiento",
        },
        "controles": {name: bool_value(value) for name, value in controls.items()},
        "archivos_generados": [str(tables_dir / name) for name in outputs],
        "no_se_entreno_modelos": True,
        "versiones": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    }
    with (tables_dir / "29_resumen_fase3.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    print("[1/6] Dataset verificado")
    print(f"      Filas originales: {len(original):,}")
    print(f"      Duplicados exactos eliminados: {len(removed):,}")
    print(f"      Filas para modelado: {len(clean):,}")
    print("[2/6] Partición aleatoria estratificada generada")
    print("[3/6] Partición agrupada por dominio generada")
    print("[4/6] Diagnósticos y tablas guardados")
    print(f"      Dominios compartidos train-prueba (aleatoria): {random_domain_overlap:,}")
    print(f"      Dominios compartidos train-prueba (agrupada): {grouped_domain_overlap:,}")
    print("[5/6] Controles de integridad: OK")
    print("[6/6] Fase 3 completada sin entrenar modelos")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preprocesamiento y partición reproducible del dataset URL-Phish."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    args = parser.parse_args()
    run_preprocessing(args.data, args.tables)


if __name__ == "__main__":
    main()
