"""Genera una muestra de cartera con las 16 columnas de entrada del modelo."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ecl.config import RAW_DATA_DIR, SAMPLES_DIR, SEED
from src.ecl.preprocessing import COLUMNAS_ENTRADA

FRONTEND_SAMPLE_PATH = ROOT_DIR / "frontend" / "public" / "cartera_demo.csv"


def generar_muestra(
    input_path: str | Path,
    output_path: str | Path,
    n: int = 1000,
    seed: int = SEED,
) -> Path:
    """Toma una muestra aleatoria reproducible y la guarda como CSV."""
    if n <= 0:
        raise ValueError("El tamaño de la muestra debe ser mayor que cero.")

    origen = Path(input_path)
    destino = Path(output_path)
    if not origen.exists():
        raise FileNotFoundError(f"No existe el archivo de entrada: {origen}")

    datos = pd.read_csv(origen, usecols=list(COLUMNAS_ENTRADA))
    muestra = datos.sample(n=min(n, len(datos)), random_state=seed)
    muestra = muestra.loc[:, list(COLUMNAS_ENTRADA)].reset_index(drop=True)

    destino.parent.mkdir(parents=True, exist_ok=True)
    muestra.to_csv(destino, index=False, encoding="utf-8")
    return destino


def publicar_en_frontend(
    origen: str | Path,
    destino: str | Path = FRONTEND_SAMPLE_PATH,
) -> Path | None:
    """Copia la muestra al directorio público del frontend si existe."""
    ruta_destino = Path(destino)
    if not ruta_destino.parent.exists():
        return None

    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(origen), ruta_destino)
    return ruta_destino


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera una muestra de cartera.")
    parser.add_argument(
        "--input",
        default=str(RAW_DATA_DIR / "X.csv"),
        help="CSV de features de origen.",
    )
    parser.add_argument(
        "--output",
        default=str(SAMPLES_DIR / "cartera_demo.csv"),
        help="CSV de salida.",
    )
    parser.add_argument("--n", type=int, default=1000, help="Filas de la muestra.")
    parser.add_argument("--seed", type=int, default=SEED, help="Semilla aleatoria.")
    parser.add_argument(
        "--skip-frontend-copy",
        action="store_true",
        help="No copia la muestra a frontend/public.",
    )
    args = parser.parse_args()

    destino = generar_muestra(args.input, args.output, n=args.n, seed=args.seed)
    print(f"Muestra guardada en: {destino}")

    if not args.skip_frontend_copy:
        copia = publicar_en_frontend(destino)
        if copia is not None:
            print(f"Muestra publicada para el frontend en: {copia}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
