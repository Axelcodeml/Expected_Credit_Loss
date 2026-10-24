from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from src.ecl.evaluation import (
    metricas_holdout,
    robustez_bootstrap,
    verificar_restricciones,
)
from src.ecl.model import (
    ModeloECL,
    aplicar_margen,
    asignar_bandas,
    calcular_ecl_calibrado,
    construir_reales,
)
from src.ecl.preprocessing import COLUMNAS_ENTRADA
from predict import predecir_cartera


def test_construir_reales_usa_definicion_a() -> None:
    df = pd.DataFrame(
        {
            "y": [1, 0],
            "funded_amnt": [1_000.0, 1_000.0],
            "princ_rec": [200.0, 1_000.0],
            "interest_rec": [100.0, 200.0],
            "late_fees_rec": [0.0, 0.0],
            "paym_rec_for_tot_amnt_fund": [400.0, 1_200.0],
        }
    )

    reales = construir_reales(df)

    assert reales.loc[0, "ead_real"] == 800.0
    assert reales.loc[0, "recuperado"] == 100.0
    assert reales.loc[0, "lgd_real"] == pytest.approx(0.875)
    assert reales.loc[0, "ecl_real_A"] == pytest.approx(700.0)
    assert reales.loc[1, "ead_real"] == 0.0
    assert reales.loc[1, "ecl_real_A"] == 0.0
    assert reales.loc[1, "ecl_real_B"] == 0.0


def test_calcular_ecl_calibrado() -> None:
    resultado = calcular_ecl_calibrado([0.1, 0.2], [0.5, 0.5], [1_000.0, 2_000.0])
    np.testing.assert_allclose(resultado, [50.0, 200.0])


def test_aplicar_margen_solo_afecta_marcados() -> None:
    ecl, marcado = aplicar_margen(
        ecl_calibrado=[100.0, 100.0, 100.0],
        pd_hat=[0.01, 0.50, 0.99],
        funded_amnt=[1_000.0, 1_000.0, 1_000.0],
        s=0.95,
        corte=0.10,
        criterio="pd",
    )
    np.testing.assert_allclose(ecl, [100.0, 950.0, 950.0])
    np.testing.assert_array_equal(marcado, [False, True, True])


def test_asignar_bandas_ordenadas() -> None:
    bandas = asignar_bandas([0.05, 0.15, 0.25, 0.95], [0.10, 0.20, 0.90])
    np.testing.assert_array_equal(bandas, [1, 2, 3, 4])


def test_predecir_no_requiere_variables_de_desempeno(
    cartera_sintetica: pd.DataFrame,
    modelo_entrenado: ModeloECL,
) -> None:
    entrada = cartera_sintetica.loc[:, list(COLUMNAS_ENTRADA)]
    predicciones = modelo_entrenado.predecir(entrada)

    assert len(predicciones) == len(entrada)
    assert list(predicciones.columns) == [
        "pd",
        "lgd",
        "ead",
        "ecl_calibrado",
        "ecl_final",
        "marcado",
        "banda_riesgo",
    ]
    assert predicciones["pd"].between(0, 1).all()
    assert predicciones["lgd"].between(0, 1).all()
    assert (predicciones["ead"] >= 0).all()
    assert (predicciones["ecl_final"] >= predicciones["ecl_calibrado"]).all()
    assert predicciones["banda_riesgo"].between(1, 10).all()


def test_contribuciones_tienen_una_columna_por_feature(
    cartera_sintetica: pd.DataFrame,
    modelo_entrenado: ModeloECL,
) -> None:
    entrada = cartera_sintetica.loc[:, list(COLUMNAS_ENTRADA)]
    contribuciones = modelo_entrenado.contribuciones(entrada)

    assert contribuciones.shape == (len(entrada), 14)
    assert list(contribuciones.columns) == modelo_entrenado.cols_pd
    assert np.isfinite(contribuciones.to_numpy()).all()


def test_serializacion_conserva_predicciones(
    cartera_sintetica: pd.DataFrame,
    modelo_entrenado: ModeloECL,
    tmp_path: Path,
) -> None:
    entrada = cartera_sintetica.loc[:, list(COLUMNAS_ENTRADA)]
    ruta = modelo_entrenado.guardar(tmp_path / "modelo.joblib")
    cargado = ModeloECL.cargar(ruta)

    pd.testing.assert_frame_equal(
        modelo_entrenado.predecir(entrada),
        cargado.predecir(entrada),
    )
    assert cargado.margen == modelo_entrenado.margen


def test_entrenamiento_es_reproducible(
    cartera_sintetica: pd.DataFrame,
    modelo_entrenado: ModeloECL,
) -> None:
    segundo = ModeloECL(obj_viol=1.0, obj_r1=0.0).fit(cartera_sintetica)
    entrada = cartera_sintetica.loc[:, list(COLUMNAS_ENTRADA)]

    assert segundo.margen == modelo_entrenado.margen
    pd.testing.assert_frame_equal(
        segundo.predecir(entrada),
        modelo_entrenado.predecir(entrada),
    )


def test_cargar_rechaza_artefacto_incorrecto(tmp_path: Path) -> None:
    ruta = tmp_path / "otro.joblib"
    joblib.dump({"no": "es un modelo"}, ruta)
    with pytest.raises(TypeError, match="no contiene un ModeloECL"):
        ModeloECL.cargar(ruta)


def test_predecir_cartera_escribe_artefactos(
    cartera_sintetica: pd.DataFrame,
    modelo_entrenado: ModeloECL,
    tmp_path: Path,
) -> None:
    entrada = cartera_sintetica.loc[:, list(COLUMNAS_ENTRADA)]
    resultado = predecir_cartera(entrada, modelo_entrenado, tmp_path)

    assert resultado.csv_path.exists()
    assert resultado.parquet_path.exists()
    assert resultado.resumen_path.exists()

    salida = pd.read_csv(resultado.csv_path)
    assert "credito_id" in salida.columns
    assert len(salida) == len(entrada)
    assert resultado.resumen["n_creditos"] == len(entrada)

    parquet = pd.read_parquet(resultado.parquet_path)
    assert len(parquet) == len(entrada)


def test_predecir_cartera_preserva_id_si_existe(
    cartera_sintetica: pd.DataFrame,
    modelo_entrenado: ModeloECL,
    tmp_path: Path,
) -> None:
    entrada = cartera_sintetica.loc[:, list(COLUMNAS_ENTRADA)].copy()
    entrada.insert(0, "id", np.arange(len(entrada)))
    resultado = predecir_cartera(entrada, modelo_entrenado, tmp_path)

    salida = pd.read_csv(resultado.csv_path)
    assert "id" in salida.columns
    assert "credito_id" not in salida.columns
    np.testing.assert_array_equal(salida["id"].to_numpy(), entrada["id"].to_numpy())


def test_metricas_holdout_y_restricciones(
    cartera_sintetica: pd.DataFrame,
    modelo_entrenado: ModeloECL,
) -> None:
    entrada = cartera_sintetica.loc[:, list(COLUMNAS_ENTRADA)]
    predicciones = modelo_entrenado.predecir(entrada)
    reales = construir_reales(cartera_sintetica)

    metricas = metricas_holdout(
        cartera_sintetica["y"].to_numpy(),
        predicciones["pd"].to_numpy(),
        predicciones["marcado"].to_numpy(),
        predicciones["ecl_final"].to_numpy(),
        reales["ecl_real_A"].to_numpy(),
    )

    assert metricas["n"] == len(cartera_sintetica)
    assert 0.0 <= float(metricas["auc"]) <= 1.0
    assert float(metricas["gini"]) == pytest.approx(2.0 * float(metricas["auc"]) - 1.0)
    assert 0.0 <= float(metricas["ks"]) <= 1.0
    assert float(metricas["mae"]) >= 0.0
    assert isinstance(metricas["cumple_restricciones"], bool)


def test_verificar_restricciones() -> None:
    cumple = verificar_restricciones([10.0, 10.0], [5.0, 5.0])
    assert cumple["r1_cobertura"] is True
    assert cumple["r2_violaciones"] is True

    no_cumple = verificar_restricciones([1.0, 20.0], [10.0, 10.0])
    assert no_cumple["r1_cobertura"] is True
    assert no_cumple["r2_violaciones"] is False
    assert no_cumple["cumple_restricciones"] is False


def test_robustez_bootstrap() -> None:
    rng = np.random.default_rng(7)
    ecl = rng.uniform(50, 150, 200)
    real = rng.uniform(50, 150, 200)
    resultado = robustez_bootstrap(ecl, real, n=25, seed=7)

    assert resultado["n_bootstrap"] == 25
    assert "ratio_p05" in resultado
    assert "violaciones_p95" in resultado
