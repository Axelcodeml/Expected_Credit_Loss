"""Configuración central del pipeline de pérdida crediticia esperada (ECL).

Las rutas se derivan de la ubicación del repositorio y pueden sobreescribirse
mediante variables de entorno. No se almacenan credenciales ni rutas absolutas
locales en el código.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parents[2]

SEED: int = int(os.getenv("ECL_SEED", "42"))

DATA_DIR: Path = Path(os.getenv("ECL_DATA_DIR", str(BASE_DIR / "data")))
RAW_DATA_DIR: Path = DATA_DIR / "raw"
SAMPLES_DIR: Path = DATA_DIR / "samples"
PREDICTIONS_DIR: Path = DATA_DIR / "predictions"

MODELS_DIR: Path = Path(os.getenv("ECL_MODELS_DIR", str(BASE_DIR / "models")))
MODEL_PATH: Path = MODELS_DIR / "ecl_model.joblib"
METADATA_PATH: Path = MODELS_DIR / "metadata.json"

TEST_SIZE: float = 0.2
VALIDATION_SIZE: float = 0.2

Q_GRID: tuple[float, ...] = tuple(round(0.10 + 0.01 * i, 2) for i in range(31))
S_GRID: tuple[float, ...] = tuple(round(0.60 + 0.05 * i, 2) for i in range(9))

OBJ_VIOL: float = 0.09
OBJ_R1: float = 1.02
CRITERIO: str = "pd_por_monto"
MAX_VIOLACIONES: float = 0.10

PISO_MAPE: float = 1.0
N_BOOTSTRAP: int = 500

MODEL_VERSION: str = "1.0.0"

COLUMNAS_ID: tuple[str, ...] = ("id", "credito_id")
