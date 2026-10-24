from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ecl.preprocessing import (
    COLUMNAS_ENTRADA,
    PreprocesadorECL,
)


def test_num_open_trades_no_forma_parte_del_pipeline() -> None:
    assert "num_open_trades_in_6mths" not in COLUMNAS_ENTRADA
    preparador = PreprocesadorECL()
    assert "num_open_trades_in_6mths" not in preparador.variables_bins
    assert "num_open_trades_in_6mths_woe" not in preparador.get_features_finales()


def test_validar_entrada_detecta_columnas_faltantes(
    cartera_sintetica: pd.DataFrame,
) -> None:
    preparador = PreprocesadorECL()
    with pytest.raises(ValueError, match="Faltan columnas requeridas"):
        preparador.validar_entrada(cartera_sintetica.drop(columns=["funded_amnt"]))


def test_validar_entrada_rechaza_nulos_en_columnas_no_nulables(
    cartera_sintetica: pd.DataFrame,
) -> None:
    preparador = PreprocesadorECL()
    copia = cartera_sintetica.copy()
    copia.loc[copia.index[0], "interest_rate"] = np.nan
    with pytest.raises(ValueError, match="no admite valores faltantes"):
        preparador.validar_entrada(copia)


def test_preprocesador_aprende_imputaciones_y_genera_woe_sin_nulos(
    cartera_sintetica: pd.DataFrame,
) -> None:
    preparador = PreprocesadorECL()
    preparador.fit(cartera_sintetica)

    entrada = cartera_sintetica.drop(columns=["y"])
    salida = preparador.transform(entrada)
    features = preparador.get_features_finales()

    assert len(features) == 14
    assert not salida[features].isna().any().any()
    assert np.isfinite(salida[features].to_numpy()).all()


def test_transform_aplica_reglas_de_negocio(
    cartera_sintetica: pd.DataFrame,
) -> None:
    preparador = PreprocesadorECL()
    preparador.fit(cartera_sintetica)

    copia = cartera_sintetica.drop(columns=["y"]).copy()
    copia.loc[copia.index[0], "issue_date_year"] = 2010
    copia.loc[copia.index[0], "earliest_cr_line_year"] = 2000
    copia.loc[copia.index[0], "annual_income"] = 2_000_000
    copia.loc[copia.index[0], "mths_since_last_installment_acc_op"] = np.nan
    copia.loc[copia.index[0], "num_rev_trades_op_in_24mths"] = np.nan
    copia.loc[copia.index[0], "num_inq"] = np.nan

    salida = preparador.transform(copia)

    assert float(salida.loc[copia.index[0], "credit_history_length"]) == 10.0
    assert float(salida.loc[copia.index[0], "annual_income"]) == 1_000_000.0
    assert float(
        salida.loc[copia.index[0], "mths_since_last_installment_acc_op"]
    ) == 999.0
    assert float(salida.loc[copia.index[0], "num_rev_trades_op_in_24mths"]) == 0.0
    assert float(salida.loc[copia.index[0], "num_inq"]) == 0.0


def test_transform_sin_fit_falla(cartera_sintetica: pd.DataFrame) -> None:
    preparador = PreprocesadorECL()
    with pytest.raises(RuntimeError, match="no está ajustado"):
        preparador.transform(cartera_sintetica.drop(columns=["y"]))


def test_fit_exige_columna_objetivo(cartera_sintetica: pd.DataFrame) -> None:
    preparador = PreprocesadorECL()
    with pytest.raises(ValueError, match="columna objetivo"):
        preparador.fit(cartera_sintetica.drop(columns=["y"]))
