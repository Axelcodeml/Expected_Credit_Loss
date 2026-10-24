"""Métricas de desempeño, restricciones de negocio y robustez bootstrap."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

from src.ecl.config import MAX_VIOLACIONES, N_BOOTSTRAP, PISO_MAPE

TipoMetrica = float | int | bool


def _calcular_ks(
    y_true: Sequence[int] | np.ndarray,
    y_score: Sequence[float] | np.ndarray,
) -> float:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    return float(np.max(tpr - fpr))


def verificar_restricciones(
    ecl_final: Sequence[float] | np.ndarray,
    ecl_real: Sequence[float] | np.ndarray,
    max_violaciones: float = MAX_VIOLACIONES,
) -> dict[str, TipoMetrica]:
    """Verifica las restricciones R1 (cobertura) y R2 (violaciones)."""
    ecl = np.asarray(ecl_final, dtype=float)
    real = np.asarray(ecl_real, dtype=float)

    total_ecl = float(ecl.sum())
    total_real = float(real.sum())
    violaciones = float((ecl < real).mean())
    ratio = total_ecl / total_real if total_real > 0 else float("nan")

    return {
        "ecl_total": total_ecl,
        "ecl_real_total": total_real,
        "ratio_ecl_real": ratio,
        "violaciones": violaciones,
        "violaciones_pct": 100.0 * violaciones,
        "r1_cobertura": bool(total_ecl > total_real),
        "r2_violaciones": bool(violaciones <= max_violaciones),
        "cumple_restricciones": bool(
            total_ecl > total_real and violaciones <= max_violaciones
        ),
    }


def metricas_holdout(
    y_true: Sequence[int] | np.ndarray,
    pd_hat: Sequence[float] | np.ndarray,
    marcado: Sequence[bool] | np.ndarray,
    ecl_final: Sequence[float] | np.ndarray,
    ecl_real: Sequence[float] | np.ndarray,
    piso_mape: float = PISO_MAPE,
) -> dict[str, TipoMetrica]:
    """Calcula métricas de clasificación, ECL y restricciones sobre holdout."""
    y_true_arr = np.asarray(y_true, dtype=int)
    pd_arr = np.asarray(pd_hat, dtype=float)
    marcado_arr = np.asarray(marcado, dtype=bool)
    ecl_arr = np.asarray(ecl_final, dtype=float)
    real_arr = np.asarray(ecl_real, dtype=float)

    if not (
        len(y_true_arr)
        == len(pd_arr)
        == len(marcado_arr)
        == len(ecl_arr)
        == len(real_arr)
    ):
        raise ValueError("Todas las entradas deben tener la misma longitud.")

    tn, fp, fn, tp = confusion_matrix(
        y_true_arr,
        marcado_arr.astype(int),
        labels=[0, 1],
    ).ravel()
    tn, fp, fn, tp = int(tn), int(fp), int(fn), int(tp)

    precision = tp / (tp + fp) if (tp + fp) > 0 else float("nan")
    recall = tp / (tp + fn) if (tp + fn) > 0 else float("nan")
    especificidad = tn / (tn + fp) if (tn + fp) > 0 else float("nan")
    exactitud = (tp + tn) / len(y_true_arr) if len(y_true_arr) > 0 else float("nan")
    tasa_default = float(y_true_arr.mean()) if len(y_true_arr) > 0 else float("nan")
    lift = precision / tasa_default if tasa_default > 0 else float("nan")

    diferencia = np.abs(ecl_arr - real_arr)
    mae = float(diferencia.mean()) if len(diferencia) > 0 else float("nan")
    wape = (
        float(diferencia.sum() / real_arr.sum())
        if real_arr.sum() > 0
        else float("nan")
    )

    mascara_mape = real_arr >= piso_mape
    if mascara_mape.any():
        errores_porcentuales = diferencia[mascara_mape] / real_arr[mascara_mape]
        mape = float(errores_porcentuales.mean())
        ape_mediano = float(np.median(errores_porcentuales))
    else:
        mape = float("nan")
        ape_mediano = float("nan")

    auc = float(roc_auc_score(y_true_arr, pd_arr))

    metricas: dict[str, TipoMetrica] = {
        "n": int(len(y_true_arr)),
        "auc": auc,
        "gini": 2.0 * auc - 1.0,
        "ks": _calcular_ks(y_true_arr, pd_arr),
        "precision": float(precision),
        "recall": float(recall),
        "especificidad": float(especificidad),
        "exactitud": float(exactitud),
        "lift": float(lift),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "pct_marcados": float(marcado_arr.mean()),
        "mae": mae,
        "wape": wape,
        "mape": mape,
        "ape_mediano": ape_mediano,
    }
    metricas.update(verificar_restricciones(ecl_arr, real_arr))
    return metricas


def robustez_bootstrap(
    ecl_final: Sequence[float] | np.ndarray,
    ecl_real: Sequence[float] | np.ndarray,
    n: int = N_BOOTSTRAP,
    seed: int = 42,
) -> dict[str, float | int]:
    """Evalúa la estabilidad del ratio ECL/real mediante bootstrap."""
    ecl = np.asarray(ecl_final, dtype=float)
    real = np.asarray(ecl_real, dtype=float)

    if len(ecl) != len(real):
        raise ValueError("ecl_final y ecl_real deben tener la misma longitud.")
    if len(ecl) == 0:
        raise ValueError("No hay observaciones para el bootstrap.")

    rng = np.random.default_rng(seed)
    ratios = np.empty(n, dtype=float)
    violaciones = np.empty(n, dtype=float)

    for i in range(n):
        indices = rng.integers(0, len(ecl), size=len(ecl))
        ecl_muestra = ecl[indices]
        real_muestra = real[indices]
        ratios[i] = ecl_muestra.sum() / real_muestra.sum()
        violaciones[i] = float((ecl_muestra < real_muestra).mean())

    return {
        "ratio_medio": float(ratios.mean()),
        "ratio_p05": float(np.percentile(ratios, 5)),
        "ratio_p50": float(np.percentile(ratios, 50)),
        "ratio_p95": float(np.percentile(ratios, 95)),
        "p_ratio_menor_1": float((ratios < 1).mean()),
        "violaciones_media": float(violaciones.mean()),
        "violaciones_p95": float(np.percentile(violaciones, 95)),
        "n_bootstrap": int(n),
    }
