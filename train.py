"""Entrena el modelo ECL, guarda el artefacto y registra sus metadatos."""

from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow
import sklearn
from sklearn.model_selection import train_test_split

from src.ecl.config import (
    METADATA_PATH,
    MODEL_PATH,
    MODELS_DIR,
    N_BOOTSTRAP,
    RAW_DATA_DIR,
    SEED,
    TEST_SIZE,
)
from src.ecl.evaluation import metricas_holdout, robustez_bootstrap
from src.ecl.model import ModeloECL, construir_reales
from src.ecl.preprocessing import COLUMNAS_ENTRADA


def _a_json(valor: object) -> object:
    if isinstance(valor, dict):
        return {str(clave): _a_json(contenido) for clave, contenido in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_a_json(contenido) for contenido in valor]
    if isinstance(valor, np.ndarray):
        return [_a_json(contenido) for contenido in valor.tolist()]
    if isinstance(valor, np.integer):
        return int(valor)
    if isinstance(valor, np.floating):
        return float(valor)
    if isinstance(valor, np.bool_):
        return bool(valor)
    if isinstance(valor, np.generic):
        return valor.item()
    if isinstance(valor, Path):
        return str(valor)
    return valor


def _rangos_entrenamiento(train: pd.DataFrame) -> dict[str, dict[str, float | None]]:
    rangos: dict[str, dict[str, float | None]] = {}
    for columna in COLUMNAS_ENTRADA:
        serie = train[columna].dropna()
        rangos[columna] = {
            "min": float(serie.min()) if not serie.empty else None,
            "max": float(serie.max()) if not serie.empty else None,
        }
    return rangos


def entrenar(
    data_dir: str | Path,
    out_dir: str | Path,
    seed: int = SEED,
) -> dict[str, object]:
    """Ejecuta el entrenamiento completo y devuelve los metadatos generados."""
    data_path = Path(data_dir)
    out_path = Path(out_dir)
    x_path = data_path / "X.csv"
    y_path = data_path / "target.csv"

    if not x_path.exists():
        raise FileNotFoundError(f"No existe el archivo de features: {x_path}")
    if not y_path.exists():
        raise FileNotFoundError(f"No existe el archivo de target: {y_path}")

    X = pd.read_csv(x_path)
    y = pd.read_csv(y_path)

    if len(X) != len(y):
        raise ValueError(
            f"X.csv y target.csv tienen distinto número de filas: {len(X)} vs {len(y)}."
        )
    if "y" not in y.columns:
        raise ValueError("target.csv debe contener una columna llamada 'y'.")

    data = X.copy()
    data["y"] = y["y"].to_numpy()

    train, test = train_test_split(
        data,
        test_size=TEST_SIZE,
        random_state=seed,
        stratify=data["y"],
    )

    modelo = ModeloECL()
    modelo.seed = seed
    modelo.fit(train)

    test_crudo = test[list(COLUMNAS_ENTRADA)]
    predicciones = modelo.predecir(test_crudo)
    reales_test = construir_reales(test)

    metricas = metricas_holdout(
        test["y"].to_numpy(),
        predicciones["pd"].to_numpy(),
        predicciones["marcado"].to_numpy(),
        predicciones["ecl_final"].to_numpy(),
        reales_test["ecl_real_A"].to_numpy(),
    )
    robustez = robustez_bootstrap(
        predicciones["ecl_final"].to_numpy(),
        reales_test["ecl_real_A"].to_numpy(),
        n=N_BOOTSTRAP,
        seed=seed,
    )

    out_path.mkdir(parents=True, exist_ok=True)
    model_path = out_path / MODEL_PATH.name
    metadata_path = out_path / METADATA_PATH.name

    modelo.guardar(model_path)

    metadata: dict[str, object] = {
        "version_modelo": modelo.version,
        "seed": seed,
        "fecha_entrenamiento": datetime.now(timezone.utc).isoformat(),
        "librerias": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit-learn": sklearn.__version__,
            "joblib": joblib.__version__,
            "pyarrow": pyarrow.__version__,
        },
        "criterio": modelo.criterio,
        "margen": dict(modelo.margen),
        "cortes_bandas": [float(valor) for valor in modelo.cortes_bandas],
        "columnas_entrada": list(COLUMNAS_ENTRADA),
        "columnas_pd": list(modelo.cols_pd),
        "train_size": int(len(train)),
        "test_size": int(len(test)),
        "rangos_entrenamiento": _rangos_entrenamiento(train),
        "metricas_holdout": metricas,
        "robustez_bootstrap": robustez,
    }

    with metadata_path.open("w", encoding="utf-8") as archivo:
        json.dump(_a_json(metadata), archivo, ensure_ascii=False, indent=2)

    print(f"Modelo guardado en: {model_path}")
    print(f"Metadatos guardados en: {metadata_path}")
    print(
        "Margen: "
        f"q={modelo.margen['q']:.2f}, s={modelo.margen['s']:.2f}, "
        f"corte={modelo.margen['corte']:.6g}"
    )
    print(
        "Holdout: "
        f"AUC={metricas['auc']:.4f}, KS={metricas['ks']:.4f}, "
        f"ECL/real={metricas['ratio_ecl_real']:.4f}, "
        f"violaciones={metricas['violaciones_pct']:.4f}%, "
        f"MAE={metricas['mae']:.2f}"
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Entrena el modelo ECL.")
    parser.add_argument(
        "--data-dir",
        default=str(RAW_DATA_DIR),
        help="Directorio con X.csv y target.csv.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(MODELS_DIR),
        help="Directorio donde guardar ecl_model.joblib y metadata.json.",
    )
    parser.add_argument("--seed", type=int, default=SEED, help="Semilla aleatoria.")
    args = parser.parse_args()

    entrenar(args.data_dir, args.out_dir, seed=args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
