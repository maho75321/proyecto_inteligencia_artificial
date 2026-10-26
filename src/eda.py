#!/usr/bin/env python3
"""Análisis exploratorio de datos del dataset de detección de phishing.

El script no modifica el CSV original. Genera tablas en results/tables/ y
figuras en figures/. Las rutas pueden cambiarse con argumentos de línea de
comandos o mediante importación de ``run_eda``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = PROJECT_ROOT / "Dataset.csv"
DEFAULT_FIGURES = PROJECT_ROOT / "figures"
DEFAULT_TABLES = PROJECT_ROOT / "results" / "tables"

CLASSES = (0, 1)
CLASS_LABELS = {0: "Clase 0", 1: "Clase 1"}
CLASS_COLORS = {0: "#4C72B0", 1: "#C44E52"}

HIST_FEATURES = [
    "url_len",
    "dom_len",
    "letter_cnt",
    "digit_cnt",
    "special_cnt",
    "entropy",
    "path_len",
    "query_len",
]
BOX_FEATURES = [
    "url_len",
    "dom_len",
    "digit_cnt",
    "special_cnt",
    "entropy",
    "path_len",
]
CATEGORICAL_FEATURES = ["is_https", "is_ip"]


def configure_style() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
        }
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_data(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el dataset: {path}")
    df = pd.read_csv(path)
    required = {"url", "dom", "label"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas obligatorias: {sorted(missing)}")
    if df["label"].isna().any():
        raise ValueError("La variable label contiene valores faltantes.")
    observed = set(df["label"].dropna().unique().tolist())
    if not observed.issubset(set(CLASSES)):
        raise ValueError(f"label contiene valores no esperados: {sorted(observed)}")
    return df


def numeric_features(df: pd.DataFrame) -> list[str]:
    return [
        column
        for column in df.select_dtypes(include=[np.number]).columns
        if column != "label"
    ]


def save_table(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    df.to_csv(path, index=index, encoding="utf-8")


def build_dimension_table(df: pd.DataFrame) -> pd.DataFrame:
    numeric_total = len(df.select_dtypes(include=[np.number]).columns)
    rows = [
        ("filas", len(df)),
        ("columnas", df.shape[1]),
        ("celdas_totales", int(df.shape[0] * df.shape[1])),
        ("columnas_numericas_totales", numeric_total),
        ("variables_numericas_predictoras", len(numeric_features(df))),
        ("columnas_de_texto", len(df.select_dtypes(exclude=[np.number]).columns)),
        ("memoria_en_memoria_mb", round(df.memory_usage(deep=True).sum() / 1024**2, 3)),
    ]
    table = pd.DataFrame(rows, columns=["metrica", "valor"])
    table["valor"] = table["valor"].map(
        lambda value: str(value)
        if isinstance(value, int)
        else f"{value:.3f}".rstrip("0").rstrip(".")
    )
    return table


def build_type_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in df.columns:
        series = df[column]
        non_null = series.dropna()
        example = "" if non_null.empty else str(non_null.iloc[0])[:120]
        rows.append(
            {
                "columna": column,
                "tipo_dato": str(series.dtype),
                "no_nulos": int(series.notna().sum()),
                "nulos": int(series.isna().sum()),
                "porcentaje_nulos": round(float(series.isna().mean() * 100), 6),
                "valores_unicos": int(series.nunique(dropna=False)),
                "ejemplo": example,
            }
        )
    return pd.DataFrame(rows)


def build_label_table(df: pd.DataFrame) -> pd.DataFrame:
    counts = df["label"].value_counts().reindex(CLASSES, fill_value=0)
    table = pd.DataFrame(
        {
            "label": CLASSES,
            "registros": counts.values,
        }
    )
    table["porcentaje"] = table["registros"] / len(df) * 100
    return table


def build_missing_table(df: pd.DataFrame) -> pd.DataFrame:
    table = pd.DataFrame(
        {
            "columna": df.columns,
            "nulos": df.isna().sum().values,
            "no_nulos": df.notna().sum().values,
        }
    )
    table["porcentaje"] = table["nulos"] / len(df) * 100
    return table.sort_values(["nulos", "columna"], ascending=[False, True]).reset_index(
        drop=True
    )


def build_descriptive_table(df: pd.DataFrame) -> pd.DataFrame:
    features = numeric_features(df)
    description = df[features].describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).T
    description = description.rename(
        columns={
            "count": "conteo",
            "mean": "media",
            "std": "desv_est",
            "min": "min",
            "1%": "p01",
            "25%": "p25",
            "50%": "mediana",
            "75%": "p75",
            "99%": "p99",
            "max": "max",
        }
    )
    description["asimetria"] = df[features].skew().values
    description["curtosis"] = df[features].kurtosis().values
    description.index.name = "variable"
    return description.reset_index()


def _url_variation_groups(df: pd.DataFrame) -> int:
    repeated = df[df["url"].duplicated(keep=False)]
    count = 0
    for _, group in repeated.groupby("url", dropna=False):
        if len(group.drop_duplicates()) > 1:
            count += 1
    return count


def build_duplicate_table(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    duplicate_mask = df.duplicated(keep=False)
    duplicate_groups = int(df.loc[duplicate_mask].drop_duplicates().shape[0])
    duplicate_excess = int(df.duplicated(keep="first").sum())
    duplicate_rows = int(duplicate_mask.sum())

    url_counts = df["url"].value_counts(dropna=False)
    url_groups = int((url_counts > 1).sum())
    url_excess = int((url_counts - 1).clip(lower=0).sum())
    url_rows = int(url_counts[url_counts > 1].sum())
    url_variation = _url_variation_groups(df)

    domain_counts = df["dom"].value_counts(dropna=False)
    domain_groups = int((domain_counts > 1).sum())
    domain_excess = int((domain_counts - 1).clip(lower=0).sum())
    domain_rows = int(domain_counts[domain_counts > 1].sum())

    rows = [
        {
            "tipo": "filas_completas",
            "grupos_repetidos": duplicate_groups,
            "filas_sobrantes": duplicate_excess,
            "filas_involucradas": duplicate_rows,
            "porcentaje_sobrante": duplicate_excess / total * 100,
            "nota": "Grupos de filas idénticas en las 26 columnas.",
        },
        {
            "tipo": "url_repetida",
            "grupos_repetidos": url_groups,
            "filas_sobrantes": url_excess,
            "filas_involucradas": url_rows,
            "porcentaje_sobrante": url_excess / total * 100,
            "nota": (
                "Grupos de URL repetida; "
                f"{url_variation} grupo(s) presentan filas no idénticas."
            ),
        },
        {
            "tipo": "dominio_repetido",
            "grupos_repetidos": domain_groups,
            "filas_sobrantes": domain_excess,
            "filas_involucradas": domain_rows,
            "porcentaje_sobrante": domain_excess / total * 100,
            "nota": "No equivale a filas duplicadas: un dominio agrupa muchas URL.",
        },
    ]
    return pd.DataFrame(rows)


def build_domain_tables(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    domains = df["dom"].fillna("(faltante)")
    cross = pd.crosstab(domains, df["label"])
    cross = cross.reindex(columns=CLASSES, fill_value=0)
    table = pd.DataFrame(
        {
            "dominio": cross.index.astype(str),
            "registros": cross.sum(axis=1).astype(int).values,
            "clase_0": cross[0].astype(int).values,
            "clase_1": cross[1].astype(int).values,
        }
    )
    table["porcentaje_clase_0_en_dominio"] = (
        table["clase_0"] / table["registros"] * 100
    )
    table["porcentaje_clase_1_en_dominio"] = (
        table["clase_1"] / table["registros"] * 100
    )
    table["porcentaje_del_total"] = table["registros"] / len(df) * 100
    table["contradictorio"] = (table["clase_0"] > 0) & (table["clase_1"] > 0)
    table = table.sort_values(
        ["registros", "dominio"], ascending=[False, True]
    ).reset_index(drop=True)

    contradictory = table.loc[table["contradictorio"]].copy()
    contradictory = contradictory.sort_values(
        ["registros", "dominio"], ascending=[False, True]
    ).reset_index(drop=True)

    summary = pd.DataFrame(
        {
            "categoria": ["solo_clase_0", "solo_clase_1", "ambas_clases"],
            "dominios": [
                int(((table["clase_0"] > 0) & (table["clase_1"] == 0)).sum()),
                int(((table["clase_0"] == 0) & (table["clase_1"] > 0)).sum()),
                int(table["contradictorio"].sum()),
            ],
        }
    )
    summary["registros"] = [
        int(table.loc[(table["clase_0"] > 0) & (table["clase_1"] == 0), "registros"].sum()),
        int(table.loc[(table["clase_0"] == 0) & (table["clase_1"] > 0), "registros"].sum()),
        int(table.loc[table["contradictorio"], "registros"].sum()),
    ]

    top = table.head(30).copy()
    return table, summary, contradictory, top


def build_domain_normalization_table(df: pd.DataFrame) -> pd.DataFrame:
    domains = df["dom"].fillna("(faltante)")
    www_mask = domains.str.startswith("www.")
    normalized = domains.str.replace(r"^www\.", "", regex=True)

    def contradictions(series: pd.Series) -> int:
        cross = pd.crosstab(series, df["label"]).reindex(columns=CLASSES, fill_value=0)
        return int(((cross[0] > 0) & (cross[1] > 0)).sum())

    without_www = set(normalized.loc[www_mask])
    base_domains = set(domains.loc[~www_mask])
    pairs = len(without_www.intersection(base_domains))

    rows = [
        ("filas_con_dom_que_inicia_con_www", int(www_mask.sum())),
        ("valores_dom_unicos_con_www", int(domains.loc[www_mask].nunique())),
        ("dominios_unicos_original", int(domains.nunique())),
        ("dominios_unicos_al_quitar_www", int(normalized.nunique())),
        ("pares_www_y_sin_www", int(pairs)),
        ("dominios_contradictorios_original", contradictions(domains)),
        ("dominios_contradictorios_al_quitar_www", contradictions(normalized)),
    ]
    table = pd.DataFrame(rows, columns=["metrica", "valor"])
    table["valor"] = table["valor"].astype(str)
    table["nota"] = [
        "El prefijo no está normalizado en toda la columna.",
        "Solo una parte de dom conserva el prefijo www.",
        "Recuento directo sobre la columna dom.",
        "Recuento tras eliminar el prefijo www.",
        "Dominios que aparecen en ambas formas.",
        "Recuento reproducible con la columna original.",
        "La normalización no cambia el número de dominios contradictorios.",
    ]
    return table


def build_constant_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in df.columns:
        if column == "label":
            continue
        counts = df[column].value_counts(dropna=False)
        if counts.empty:
            continue
        top_value = counts.index[0]
        top_count = int(counts.iloc[0])
        top_share = top_count / len(df)
        unique = int(df[column].nunique(dropna=False))
        if unique == 1 or top_share >= 0.99:
            rows.append(
                {
                    "columna": column,
                    "valores_unicos": unique,
                    "valor_mas_frecuente": str(top_value),
                    "frecuencia": top_count,
                    "porcentaje": top_share * 100,
                    "clasificacion": "constante" if unique == 1 else "casi_constante",
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "columna",
            "valores_unicos",
            "valor_mas_frecuente",
            "frecuencia",
            "porcentaje",
            "clasificacion",
        ],
    )


def build_outlier_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in numeric_features(df):
        series = df[column].dropna()
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = (series < lower) | (series > upper)
        mean = float(series.mean())
        std = float(series.std())
        skew = float(series.skew())
        rows.append(
            {
                "variable": column,
                "min": float(series.min()),
                "p01": float(series.quantile(0.01)),
                "q1": q1,
                "mediana": float(series.median()),
                "q3": q3,
                "p99": float(series.quantile(0.99)),
                "max": float(series.max()),
                "media": mean,
                "desv_est": std,
                "coef_variacion": std / mean if abs(mean) > 1e-12 else np.nan,
                "asimetria": skew,
                "curtosis": float(series.kurtosis()),
                "limite_inferior_iqr": lower,
                "limite_superior_iqr": upper,
                "n_atipicos_iqr": int(outliers.sum()),
                "porcentaje_atipicos_iqr": float(outliers.mean() * 100),
                "n_ceros": int((series == 0).sum()),
                "porcentaje_ceros": float((series == 0).mean() * 100),
                "asimetria_alta": bool(abs(skew) > 1),
            }
        )
    return pd.DataFrame(rows)


def build_correlation_tables(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    features = numeric_features(df)
    correlation = df[features].corr(method="pearson")
    correlation.index.name = "variable"

    pairs: list[dict[str, Any]] = []
    for i, first in enumerate(features):
        for second in features[i + 1 :]:
            value = float(correlation.loc[first, second])
            pairs.append(
                {
                    "variable_1": first,
                    "variable_2": second,
                    "r_pearson": value,
                    "abs_r": abs(value),
                }
            )
    pairs_table = pd.DataFrame(pairs)
    high = pairs_table.loc[pairs_table["abs_r"] >= 0.90].sort_values(
        "abs_r", ascending=False
    )

    with_label = df[features].corrwith(df["label"], method="pearson")
    label_table = pd.DataFrame(
        {"variable": features, "r_con_label": with_label.values}
    )
    label_table["abs_r"] = label_table["r_con_label"].abs()
    label_table["direccion"] = np.where(
        label_table["r_con_label"] >= 0, "positiva", "negativa"
    )
    label_table = label_table.sort_values("abs_r", ascending=False).reset_index(
        drop=True
    )
    return correlation, high.reset_index(drop=True), label_table


def build_class_comparison(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in numeric_features(df):
        group_0 = df.loc[df["label"] == 0, column].dropna()
        group_1 = df.loc[df["label"] == 1, column].dropna()
        if group_0.empty or group_1.empty:
            continue
        statistic, pvalue = stats.mannwhitneyu(
            group_1, group_0, alternative="two-sided"
        )
        rank_biserial = 2 * statistic / (len(group_1) * len(group_0)) - 1
        rows.append(
            {
                "variable": column,
                "n_clase_0": len(group_0),
                "n_clase_1": len(group_1),
                "media_clase_0": float(group_0.mean()),
                "media_clase_1": float(group_1.mean()),
                "diferencia_medias_1_menos_0": float(
                    group_1.mean() - group_0.mean()
                ),
                "mediana_clase_0": float(group_0.median()),
                "mediana_clase_1": float(group_1.median()),
                "diferencia_medianas_1_menos_0": float(
                    group_1.median() - group_0.median()
                ),
                "desv_est_clase_0": float(group_0.std()),
                "desv_est_clase_1": float(group_1.std()),
                "U_mannwhitney": float(statistic),
                "p_valor": float(pvalue),
                "rank_biserial": float(rank_biserial),
                "significativo_alpha_0_05": bool(pvalue < 0.05),
            }
        )
    table = pd.DataFrame(rows)
    return table.sort_values("rank_biserial", key=np.abs, ascending=False).reset_index(
        drop=True
    )


def build_categorical_frequencies(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for column in CATEGORICAL_FEATURES:
        if column not in df.columns:
            continue
        for value in sorted(df[column].dropna().unique().tolist()):
            subset = df[df[column] == value]
            rows.append(
                {
                    "variable": column,
                    "valor": value,
                    "total": len(subset),
                    "clase_0": int((subset["label"] == 0).sum()),
                    "porcentaje_clase_0": float(
                        (subset["label"] == 0).mean() * 100
                    ),
                    "clase_1": int((subset["label"] == 1).sum()),
                    "porcentaje_clase_1": float(
                        (subset["label"] == 1).mean() * 100
                    ),
                }
            )
    return pd.DataFrame(rows)


def plot_class_distribution(df: pd.DataFrame, path: Path) -> None:
    counts = df["label"].value_counts().reindex(CLASSES, fill_value=0)
    percentages = counts / len(df) * 100
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(
        [CLASS_LABELS[value] for value in CLASSES],
        counts.values,
        color=[CLASS_COLORS[value] for value in CLASSES],
        width=0.55,
    )
    for bar, count, percentage in zip(bars, counts.values, percentages.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + len(df) * 0.012,
            f"{count:,}\n({percentage:.2f} %)",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_ylabel("Número de registros")
    ax.set_xlabel("Clase")
    ax.set_title("Distribución de la variable objetivo label")
    ax.set_ylim(0, counts.max() * 1.18)
    fig.text(
        0.5,
        0.01,
        f"Total de registros: {len(df):,}. Desbalance aproximado 6:1.",
        ha="center",
        fontsize=8,
    )
    fig.savefig(path)
    plt.close(fig)


def plot_missing_values(missing: pd.DataFrame, path: Path) -> None:
    ordered = missing.sort_values("porcentaje", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 8))
    colors = [
        CLASS_COLORS[1] if count > 0 else "#B8B8B8"
        for count in ordered["nulos"].values
    ]
    ax.barh(ordered["columna"], ordered["porcentaje"], color=colors)
    maximum = max(0.02, float(ordered["porcentaje"].max()) * 1.35)
    for index, (count, percentage) in enumerate(
        zip(ordered["nulos"].values, ordered["porcentaje"].values)
    ):
        if count > 0:
            ax.text(
                percentage + maximum * 0.012,
                index,
                f"{count:,} ({percentage:.3f} %)",
                va="center",
                fontsize=8,
            )
    ax.set_xlim(0, maximum)
    ax.set_xlabel("Porcentaje de valores faltantes")
    ax.set_ylabel("Columna")
    ax.set_title("Valores faltantes por columna")
    fig.text(
        0.5,
        0.01,
        "Solo tld presenta faltantes; 13 de los 14 casos son URL con IP.",
        ha="center",
        fontsize=8,
    )
    fig.savefig(path)
    plt.close(fig)


def plot_numeric_distributions(df: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    axes = axes.ravel()
    for ax, column in zip(axes, HIST_FEATURES):
        series = df[column].dropna()
        upper = float(series.quantile(0.995))
        displayed = series[series <= upper]
        ax.hist(displayed, bins=50, color="#4C72B0", edgecolor="white", alpha=0.9)
        ax.axvline(
            float(series.median()),
            color="#222222",
            linestyle="--",
            linewidth=1,
            label=f"Mediana: {series.median():.2f}",
        )
        ax.set_yscale("log")
        ax.set_title(column)
        ax.set_xlabel(f"Valor (recorte P99.5 = {upper:.2f})")
        ax.set_ylabel("Frecuencia (escala log)")
        ax.legend(loc="upper right", fontsize=7)
    fig.suptitle(
        "Distribuciones de características numéricas relevantes "
        f"(n = {len(df):,})",
        fontsize=13,
    )
    fig.text(
        0.5,
        0.005,
        "El eje x se recorta al percentil 99.5 para visualizar el cuerpo de la distribución; "
        "los extremos se documentan en la tabla 12.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(path)
    plt.close(fig)


def plot_class_comparison(df: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    axes = axes.ravel()
    for ax, column in zip(axes, BOX_FEATURES):
        subset = df[[column, "label"]].dropna()
        upper = float(subset[column].quantile(0.995))
        displayed = subset[subset[column] <= upper]
        sns.boxplot(
            data=displayed,
            x="label",
            y=column,
            hue="label",
            palette=CLASS_COLORS,
            showfliers=False,
            legend=False,
            ax=ax,
        )
        for index, value in enumerate(CLASSES):
            median = float(displayed.loc[displayed["label"] == value, column].median())
            ax.text(
                index,
                median,
                f"{median:.2f}",
                ha="center",
                va="bottom",
                fontsize=7,
                color="#111111",
                bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
            )
        ax.set_title(column)
        ax.set_xlabel("Clase")
        ax.set_ylabel(f"Valor (recorte P99.5 = {upper:.2f})")
        ax.set_xticks([0, 1])
        ax.set_xticklabels([CLASS_LABELS[value] for value in CLASSES])
    fig.suptitle(
        "Comparación de características numéricas por clase "
        f"(n = {len(df):,})",
        fontsize=13,
    )
    fig.text(
        0.5,
        0.005,
        "Diagramas de caja sin valores extremos gráficos y eje y recortado al percentil 99.5. "
        "Los valores mostrados son medianas.",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.96))
    fig.savefig(path)
    plt.close(fig)


def plot_correlation_matrix(
    correlation: pd.DataFrame, path: Path, n_rows: int
) -> None:
    fig, ax = plt.subplots(figsize=(14, 12))
    sns.heatmap(
        correlation,
        ax=ax,
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
        center=0,
        square=True,
        linewidths=0.3,
        cbar_kws={"shrink": 0.75, "label": "Correlación de Pearson"},
    )
    ax.set_title(
        f"Matriz de correlación de Pearson entre características numéricas (n = {n_rows:,})",
        fontsize=12,
        pad=14,
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    plt.setp(ax.get_yticklabels(), rotation=0, fontsize=8)
    fig.text(
        0.5,
        0.01,
        "Coeficientes lineales; no implican causalidad. "
        "Las razones letter_ratio, digit_ratio y spec_ratio son composiciones de la URL.",
        ha="center",
        fontsize=8,
    )
    fig.savefig(path)
    plt.close(fig)


def plot_contradictory_domains(contradictory: pd.DataFrame, path: Path) -> None:
    ordered = contradictory.sort_values("registros", ascending=True)
    figures, ax = plt.subplots(figsize=(10, 9))
    positions = np.arange(len(ordered))
    share_0 = ordered["porcentaje_clase_0_en_dominio"].values
    share_1 = ordered["porcentaje_clase_1_en_dominio"].values
    ax.barh(positions, share_0, color=CLASS_COLORS[0], label=CLASS_LABELS[0])
    ax.barh(positions, share_1, left=share_0, color=CLASS_COLORS[1], label=CLASS_LABELS[1])
    ax.set_yticks(positions)
    ax.set_yticklabels(ordered["dominio"], fontsize=8)
    ax.set_xlim(0, 112)
    ax.set_xlabel("Porcentaje de registros dentro del dominio")
    ax.set_ylabel("Dominio")
    ax.set_title(
        "Composición por clase de los dominios con etiquetas contradictorias "
        f"(n = {len(ordered)} dominios)",
        pad=26,
    )
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.005),
        ncol=2,
        frameon=False,
    )
    for position, total in zip(positions, ordered["registros"].values):
        ax.text(
            101.5,
            position,
            f"n={int(total):,}",
            va="center",
            fontsize=7,
        )
    figures.text(
        0.5,
        0.01,
        "Barras normalizadas al 100 % dentro de cada dominio; el total de registros "
        "se muestra a la derecha.",
        ha="center",
        fontsize=8,
    )
    figures.savefig(path)
    plt.close(figures)


def verify_outputs(
    df: pd.DataFrame,
    labels: pd.DataFrame,
    missing: pd.DataFrame,
    domains: pd.DataFrame,
    contradictory: pd.DataFrame,
    figure_paths: list[Path],
    table_paths: list[Path],
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    checks["total_label_igual_filas"] = bool(labels["registros"].sum() == len(df))
    checks["porcentajes_label_suman_100"] = bool(
        abs(labels["porcentaje"].sum() - 100) < 1e-9
    )
    checks["total_dominios_igual_filas"] = bool(domains["registros"].sum() == len(df))
    checks["dominios_contradictorios_reproducidos"] = int(len(contradictory))
    checks["suma_faltantes_igual_celdas_faltantes"] = bool(
        int(missing["nulos"].sum()) == int(df.isna().sum().sum())
    )
    checks["filas_tabla_tipos_igual_columnas"] = bool(len(missing) == df.shape[1])
    checks["figuras_existentes_y_no_vacias"] = bool(
        all(path.exists() and path.stat().st_size > 0 for path in figure_paths)
    )
    checks["tablas_existentes_y_no_vacias"] = bool(
        all(path.exists() and path.stat().st_size > 0 for path in table_paths)
    )
    if not all(
        [
            checks["total_label_igual_filas"],
            checks["porcentajes_label_suman_100"],
            checks["total_dominios_igual_filas"],
            checks["suma_faltantes_igual_celdas_faltantes"],
            checks["filas_tabla_tipos_igual_columnas"],
            checks["figuras_existentes_y_no_vacias"],
            checks["tablas_existentes_y_no_vacias"],
        ]
    ):
        raise AssertionError(f"Falló un control de calidad: {checks}")
    return checks


def run_eda(
    data_path: Path | str = DEFAULT_DATA,
    figures_dir: Path | str = DEFAULT_FIGURES,
    tables_dir: Path | str = DEFAULT_TABLES,
) -> dict[str, Any]:
    data_path = Path(data_path)
    figures_dir = Path(figures_dir)
    tables_dir = Path(tables_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    configure_style()

    print(f"[1/6] Leyendo dataset: {data_path}")
    df = load_data(data_path)
    print(f"      Filas: {len(df):,} | Columnas: {df.shape[1]}")

    print("[2/6] Calculando tablas descriptivas y de calidad")
    dimensions = build_dimension_table(df)
    types = build_type_table(df)
    labels = build_label_table(df)
    missing = build_missing_table(df)
    description = build_descriptive_table(df)
    duplicates = build_duplicate_table(df)
    domains, domain_summary, contradictory, top_domains = build_domain_tables(df)
    domain_normalization = build_domain_normalization_table(df)
    constants = build_constant_table(df)
    outliers = build_outlier_table(df)

    print("[3/6] Calculando correlaciones y comparaciones entre clases")
    correlation, high_correlations, label_correlations = build_correlation_tables(df)
    class_comparison = build_class_comparison(df)
    categorical_frequencies = build_categorical_frequencies(df)

    table_paths = {
        "01_dimensiones.csv": dimensions,
        "02_tipos_datos.csv": types,
        "03_distribucion_label.csv": labels,
        "04_estadisticas_descriptivas.csv": description,
        "05_valores_faltantes.csv": missing,
        "06_duplicados_resumen.csv": duplicates,
        "07_distribucion_etiquetas_por_dominio.csv": domains,
        "08_resumen_dominios.csv": domain_summary,
        "09_dominios_contradictorios.csv": contradictory,
        "10_top_dominios.csv": top_domains,
        "11_constantes_casi_constantes.csv": constants,
        "12_valores_extremos.csv": outliers,
        "13_matriz_correlacion_pearson.csv": correlation,
        "14_pares_correlacion_alta.csv": high_correlations,
        "15_correlacion_con_label.csv": label_correlations,
        "16_comparacion_clases.csv": class_comparison,
        "17_frecuencias_categoricas_por_clase.csv": categorical_frequencies,
        "18_observacion_normalizacion_dom.csv": domain_normalization,
    }
    for filename, table in table_paths.items():
        save_table(
            table,
            tables_dir / filename,
            index=filename == "13_matriz_correlacion_pearson.csv",
        )

    print("[4/6] Generando figuras")
    figure_paths = [
        figures_dir / "fig01_distribucion_clases.png",
        figures_dir / "fig02_valores_faltantes.png",
        figures_dir / "fig03_distribuciones_numericas.png",
        figures_dir / "fig04_comparacion_clases.png",
        figures_dir / "fig05_matriz_correlacion.png",
        figures_dir / "fig06_dominios_contradictorios.png",
    ]
    plot_class_distribution(df, figure_paths[0])
    plot_missing_values(missing, figure_paths[1])
    plot_numeric_distributions(df, figure_paths[2])
    plot_class_comparison(df, figure_paths[3])
    plot_correlation_matrix(correlation, figure_paths[4], len(df))
    plot_contradictory_domains(contradictory, figure_paths[5])

    print("[5/6] Verificando totales y archivos")
    checks = verify_outputs(
        df,
        labels,
        missing,
        domains,
        contradictory,
        figure_paths,
        [tables_dir / name for name in table_paths],
    )

    summary = {
        "fecha_ejecucion_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(data_path),
        "sha256_dataset": sha256_file(data_path),
        "filas": int(len(df)),
        "columnas": int(df.shape[1]),
        "distribucion_label": {
            str(row.label): {
                "registros": int(row.registros),
                "porcentaje": round(float(row.porcentaje), 6),
            }
            for row in labels.itertuples(index=False)
        },
        "valores_faltantes": {
            "total_celdas": int(df.isna().sum().sum()),
            "columnas_con_faltantes": int((missing["nulos"] > 0).sum()),
            "detalle": {
                row.columna: int(row.nulos)
                for row in missing.loc[missing["nulos"] > 0].itertuples(index=False)
            },
        },
        "duplicados": {
            row.tipo: {
                "grupos": int(row.grupos_repetidos),
                "filas_sobrantes": int(row.filas_sobrantes),
            }
            for row in duplicates.itertuples(index=False)
        },
        "urls_unicas": int(df["url"].nunique(dropna=False)),
        "dominios_unicos": int(df["dom"].nunique(dropna=False)),
        "dominios_contradictorios": int(len(contradictory)),
        "normalizacion_dom": {
            row.metrica: row.valor
            for row in domain_normalization.itertuples(index=False)
        },
        "constantes_o_casi_constantes": constants["columna"].tolist(),
        "variables_con_asimetria_alta": outliers.loc[
            outliers["asimetria_alta"], "variable"
        ].tolist(),
        "pares_correlacion_abs_r_ge_0_90": int(len(high_correlations)),
        "figuras": [str(path) for path in figure_paths],
        "tablas": [str(tables_dir / name) for name in table_paths],
        "verificaciones": checks,
        "versiones": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
            "seaborn": sns.__version__,
            "scipy": __import__("scipy").__version__,
        },
    }
    with (tables_dir / "00_resumen_general.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    print("[6/6] Análisis completado")
    print(f"      Tablas: {tables_dir}")
    print(f"      Figuras: {figures_dir}")
    print(f"      Dominios contradictorios: {len(contradictory)}")
    print(f"      Control de calidad: {'OK' if all(checks.values()) else 'REVISAR'}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EDA reproducible del dataset de detección de phishing."
    )
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--figures", type=Path, default=DEFAULT_FIGURES)
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES)
    args = parser.parse_args()
    run_eda(args.data, args.figures, args.tables)


if __name__ == "__main__":
    main()
