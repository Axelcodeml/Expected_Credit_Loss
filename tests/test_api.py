from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from api.settings import Settings
from src.ecl.model import ModeloECL
from src.ecl.preprocessing import COLUMNAS_ENTRADA


def _metadata(cartera: pd.DataFrame) -> dict[str, object]:
    rangos: dict[str, dict[str, float]] = {}
    for columna in COLUMNAS_ENTRADA:
        serie = cartera[columna].dropna()
        rangos[columna] = {
            "min": float(serie.min()),
            "max": float(serie.max()),
        }
    return {
        "version_modelo": "test-1.0.0",
        "seed": 42,
        "rangos_entrenamiento": rangos,
    }


@pytest.fixture()
def cliente(
    cartera_sintetica: pd.DataFrame,
    modelo_entrenado: ModeloECL,
    tmp_path: Path,
) -> Iterator[TestClient]:
    ajustes = Settings(
        model_path=tmp_path / "model.joblib",
        metadata_path=tmp_path / "metadata.json",
        predictions_dir=tmp_path / "predictions",
        uploads_dir=tmp_path / "uploads",
        cors_origins="http://localhost:3000",
    )
    app = create_app(
        modelo=modelo_entrenado,
        metadata=_metadata(cartera_sintetica),
        ajustes=ajustes,
    )
    with TestClient(app) as client:
        yield client


def _creditos_json(cartera: pd.DataFrame, n: int) -> list[dict[str, object]]:
    datos = cartera.head(n)[list(COLUMNAS_ENTRADA)].to_json(orient="records")
    return json.loads(datos)


def _esperar_job(cliente: TestClient, job_id: str) -> dict[str, object]:
    for _ in range(200):
        respuesta = cliente.get(f"/jobs/{job_id}")
        assert respuesta.status_code == 200
        estado = respuesta.json()
        if estado["status"] in {"done", "error"}:
            return estado
        time.sleep(0.05)
    raise AssertionError("El job no terminó dentro del tiempo esperado.")


def test_health_y_model_info(cliente: TestClient) -> None:
    health = cliente.get("/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "model_version": "test-1.0.0",
        "seed": 42,
    }

    info = cliente.get("/model/info")
    assert info.status_code == 200
    cuerpo = info.json()
    assert cuerpo["metadata"]["seed"] == 42
    assert cuerpo["supuestos"]
    assert cuerpo["limites"]
    assert "No es un detector de fraude" in cuerpo["aviso"]


def test_predict_lote_pequeno(
    cliente: TestClient,
    cartera_sintetica: pd.DataFrame,
) -> None:
    respuesta = cliente.post(
        "/predict",
        json={"creditos": _creditos_json(cartera_sintetica, 2)},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert len(cuerpo["creditos"]) == 2
    assert cuerpo["totales"]["n"] == 2
    for credito in cuerpo["creditos"]:
        assert set(credito) == {
            "id",
            "pd",
            "lgd",
            "ead",
            "ecl_calibrado",
            "ecl_final",
            "marcado",
            "banda_riesgo",
            "advertencias",
            "contribuciones",
        }
        assert 0.0 <= credito["pd"] <= 1.0
        assert 0.0 <= credito["lgd"] <= 1.0
        assert credito["ead"] >= 0.0
        assert credito["ecl_final"] >= credito["ecl_calibrado"]
        assert 1 <= credito["banda_riesgo"] <= 10
        assert len(credito["contribuciones"]) == 14
        contribuciones = [
            item["contribucion"] for item in credito["contribuciones"]
        ]
        assert contribuciones == sorted(contribuciones)


def test_predict_advierte_fuera_de_rango(
    cliente: TestClient,
    cartera_sintetica: pd.DataFrame,
) -> None:
    creditos = _creditos_json(cartera_sintetica, 1)
    creditos[0]["annual_income"] = 10_000_000.0
    respuesta = cliente.post("/predict", json={"creditos": creditos})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["advertencias"]
    assert any(
        "annual_income" in aviso
        for aviso in cuerpo["creditos"][0]["advertencias"]
    )


def test_predict_rechaza_plazo_invalido(cliente: TestClient) -> None:
    credito = {
        "funded_amnt": 1_000.0,
        "interest_rate": 10.0,
        "loan_term_months": 48,
        "monthly_payment": 100.0,
        "annual_income": 50_000.0,
        "dept_paym_income_ratio": 10.0,
        "issue_date_year": 2015,
        "earliest_cr_line_year": 2000,
        "num_rev_trades_op_in_24mths": 1.0,
        "num_inq_in_6mths": 1.0,
        "num_inq": 1.0,
        "num_derogatory_pub_rec": 0.0,
        "mths_since_last_installment_acc_op": 10.0,
        "bal_to_cred_lim": 10.0,
        "max_bal_owed": 1_000.0,
        "used_credit_share": 20.0,
    }
    respuesta = cliente.post("/predict", json={"creditos": [credito]})
    assert respuesta.status_code == 422


def test_portfolio_flujo_completo(
    cliente: TestClient,
    cartera_sintetica: pd.DataFrame,
) -> None:
    csv = cartera_sintetica.head(20)[list(COLUMNAS_ENTRADA)].to_csv(index=False)
    respuesta = cliente.post(
        "/portfolio",
        files={"file": ("cartera.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert respuesta.status_code == 202
    job_id = respuesta.json()["job_id"]
    assert respuesta.json()["status"] == "queued"

    estado = _esperar_job(cliente, job_id)
    assert estado["status"] == "done", estado["mensaje"]
    assert estado["totales"]["n"] == 20
    assert estado["reporte_calidad"]["filas_leidas"] == 20
    assert estado["reporte_calidad"]["filas_procesadas"] == 20

    resumen = cliente.get(f"/jobs/{job_id}/summary")
    assert resumen.status_code == 200
    cuerpo_resumen = resumen.json()
    assert len(cuerpo_resumen["histograma_pd"]) == 10
    assert len(cuerpo_resumen["por_decil"]) == 10
    assert len(cuerpo_resumen["por_plazo"]) == 2
    assert cuerpo_resumen["por_ano"]
    assert len(cuerpo_resumen["top_creditos"]) <= 20

    filas = cliente.get(
        f"/jobs/{job_id}/rows",
        params={
            "page": 1,
            "page_size": 5,
            "sort_by": "ecl_final",
            "order": "desc",
        },
    )
    assert filas.status_code == 200
    cuerpo_filas = filas.json()
    assert cuerpo_filas["total"] == 20
    assert len(cuerpo_filas["rows"]) == 5

    descarga = cliente.get(f"/jobs/{job_id}/download")
    assert descarga.status_code == 200
    assert descarga.headers["content-type"].startswith("text/csv")
    assert len(descarga.content) > 0

    historial = cliente.get("/history")
    assert historial.status_code == 200
    assert any(item["job_id"] == job_id for item in historial.json())


def test_portfolio_reporta_columnas_faltantes(cliente: TestClient) -> None:
    csv = "interest_rate\n10\n"
    respuesta = cliente.post(
        "/portfolio",
        files={"file": ("incompleto.csv", csv.encode("utf-8"), "text/csv")},
    )
    assert respuesta.status_code == 202
    job_id = respuesta.json()["job_id"]
    estado = _esperar_job(cliente, job_id)

    assert estado["status"] == "error"
    assert "Faltan columnas requeridas" in estado["mensaje"]
    assert "funded_amnt" in estado["reporte_calidad"]["columnas_faltantes"]


def test_portfolio_rechaza_archivo_no_csv(cliente: TestClient) -> None:
    respuesta = cliente.post(
        "/portfolio",
        files={"file": ("cartera.txt", b"contenido", "text/plain")},
    )
    assert respuesta.status_code == 422


def test_job_inexistente(cliente: TestClient) -> None:
    assert cliente.get("/jobs/no-existe").status_code == 404
    assert cliente.get("/jobs/no-existe/summary").status_code == 404
    assert cliente.get("/jobs/no-existe/rows").status_code == 404
    assert cliente.get("/jobs/no-existe/download").status_code == 404
