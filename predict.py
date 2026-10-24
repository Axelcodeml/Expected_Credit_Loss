"""Genera predicciones ECL para una cartera y persiste los resultados."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.ecl.config import MODEL_PATH, PREDICTIONS_DIR
from src.ecl.model import ModeloECL

TipoResumen = str | int | float | bool | None


@dataclass(frozen=True)
class ResultadoCartera:
    """Rutas y resumen de una ejecución de predicción."""

    csv_path: Path
    parquet_path: Path
    resumen_path: Path
    resumen: dict[str, TipoResumen]


def calcular_totales(salida: pd.DataFrame) -> dict[str, float | int | None]:
    """Calcula los totales de una cartera ya predicha."""
    n = int(len(salida))
    calibrado_total = float(salida["ecl_calibrado"].sum()) if n > 0 else 0.0
    final_total = float(salida["ecl_final"].sum()) if n > 0 else 0.0
    return {
        "n": n,
        "exposicion_total": float(salida["funded_amnt"].sum()) if n > 0 else 0.0,
        "ecl_calibrado_total": calibrado_total,
        "ecl_final_total": final_total,
        "ratio_final_calibrado": (
            final_total / calibrado_total if calibrado_total > 0 else None
        ),
        "pct_marcados": float(salida["marcado"].mean()) if n > 0 else 0.0,
        "pd_media": float(salida["pd"].mean()) if n > 0 else 0.0,
    }


def predecir_cartera(
    df: pd.DataFrame,
    modelo: ModeloECL,
    output_dir: str | Path = PREDICTIONS_DIR,
    job_id: str | None = None,
) -> ResultadoCartera:
    """Predice una cartera, guarda CSV/Parquet y devuelve un resumen JSON."""
    modelo.prep.validar_entrada(df)
    predicciones = modelo.predecir(df)

    if "id" in df.columns:
        nombre_id = "id"
        identificador = df["id"].to_numpy()
    else:
        nombre_id = "credito_id"
        identificador = df.index.to_numpy()

    salida = pd.DataFrame(
        {
            nombre_id: identificador,
            "funded_amnt": df["funded_amnt"].to_numpy(dtype=float),
        }
    )
    salida = pd.concat(
        [salida, predicciones.reset_index(drop=True)],
        axis=1,
    )

    totales = calcular_totales(salida)
    resumen: dict[str, TipoResumen] = {
        "version_modelo": modelo.version,
        "seed": modelo.seed,
        "criterio": modelo.criterio,
        "n_creditos": totales["n"],
        **totales,
    }

    destino = Path(output_dir)
    destino.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    base = f"ecl_{job_id}" if job_id else f"ecl_{timestamp}"
    csv_path = destino / f"{base}.csv"
    parquet_path = destino / f"{base}.parquet"
    resumen_path = destino / f"{base}_resumen.json"

    salida.to_csv(csv_path, index=False, encoding="utf-8")
    salida.to_parquet(parquet_path, index=False)
    resumen_path.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return ResultadoCartera(
        csv_path=csv_path,
        parquet_path=parquet_path,
        resumen_path=resumen_path,
        resumen=resumen,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Predice ECL para una cartera.")
    parser.add_argument("--input", required=True, help="Archivo CSV de entrada.")
    parser.add_argument(
        "--output-dir",
        default=str(PREDICTIONS_DIR),
        help="Directorio para CSV, Parquet y resumen JSON.",
    )
    parser.add_argument(
        "--model",
        default=str(MODEL_PATH),
        help="Ruta del artefacto joblib del modelo.",
    )
    args = parser.parse_args()

    modelo = ModeloECL.cargar(args.model)
    df = pd.read_csv(args.input)
    resultado = predecir_cartera(df, modelo, args.output_dir)

    print(f"CSV: {resultado.csv_path}")
    print(f"Parquet: {resultado.parquet_path}")
    print(f"Resumen: {resultado.resumen_path}")
    print(
        "ECL final total: "
        f"{resultado.resumen['ecl_final_total']:.2f}; "
        f"marcados: {100.0 * float(resultado.resumen['pct_marcados'] or 0.0):.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
