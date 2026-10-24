"""API REST local para estimar la pérdida crediticia esperada (ECL)."""

from __future__ import annotations

import json
import logging
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, cast

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from api.jobs import (
    JobManager,
    JobNoEncontrado,
    JobNoListo,
    normalizar_id,
    rangos_entrenamiento,
)
from api.schemas import (
    CampoOrden,
    Contribucion,
    HealthResponse,
    HistoryItem,
    JobCreatedResponse,
    JobStatusResponse,
    JobSummaryResponse,
    LoanPrediction,
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
    RowsResponse,
    TotalesCartera,
)
from api.settings import Settings, settings
from predict import calcular_totales
from src.ecl.model import ModeloECL
from src.ecl.preprocessing import COLUMNAS_ENTRADA

logger = logging.getLogger(__name__)

AVISO = (
    "Estimación a nivel de cartera. No es un detector de fraude ni debe "
    "usarse para aprobar o rechazar créditos individuales."
)

SUPUESTOS = [
    "La pérdida real usa la definición A: los intereses cobrados no restan "
    "pérdida.",
    "La ECL real es 0 para créditos sin default; este supuesto no está "
    "confirmado con el organizador.",
    "La recuperación se infiere como residuo de los pagos registrados.",
    "La validación usa particiones aleatorias del mismo conjunto; el "
    "desempeño en otra época puede ser peor.",
    "La PD discrimina de forma moderada, por lo que el poder predictivo es "
    "limitado.",
]

LIMITES = [
    "No debe usarse para aprobar o rechazar créditos individuales.",
    "No es un detector de fraude.",
    "El margen de conservadurismo (q y s) se calibró para las restricciones "
    "del reto y no es un parámetro regulatorio.",
    "Los resultados dependen de que la cartera de entrada tenga la misma "
    "definición y calidad de datos que el conjunto de entrenamiento.",
]


def _cargar_metadata(ruta: Path) -> dict[str, object]:
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo de metadatos: {ruta}")
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ValueError(f"El archivo de metadatos no es un objeto JSON: {ruta}")
    return cast(dict[str, object], datos)


def _modelo(request: Request) -> ModeloECL:
    return cast(ModeloECL, request.app.state.modelo)


def _metadata(request: Request) -> dict[str, object]:
    return cast(dict[str, object], request.app.state.metadata)


def _jobs(request: Request) -> JobManager:
    return cast(JobManager, request.app.state.jobs)


def _advertencias_por_fila(
    df: pd.DataFrame,
    metadata: dict[str, object],
) -> list[list[str]]:
    advertencias: list[list[str]] = [[] for _ in range(len(df))]
    for columna, (minimo, maximo) in rangos_entrenamiento(metadata).items():
        if columna not in df.columns:
            continue
        serie = pd.to_numeric(df[columna], errors="coerce")
        fuera = serie.notna() & ((serie < minimo) | (serie > maximo))
        for posicion in np.flatnonzero(fuera.to_numpy()):
            indice = int(posicion)
            advertencias[indice].append(
                f"'{columna}'={float(serie.iloc[indice])} está fuera del "
                f"rango de entrenamiento [{minimo}, {maximo}]."
            )
    return advertencias


def _contribuciones_por_fila(
    modelo: ModeloECL,
    df: pd.DataFrame,
) -> list[list[Contribucion]]:
    df_woe = modelo.prep.transform(df)
    coeficientes = modelo.modelo_pd.coef_[0].astype(float)
    valores_woe = df_woe[modelo.cols_pd].to_numpy(dtype=float)
    matriz = valores_woe * coeficientes

    resultado: list[list[Contribucion]] = []
    for i in range(matriz.shape[0]):
        items = [
            Contribucion(
                variable=columna.removesuffix("_woe"),
                valor_woe=float(valores_woe[i, j]),
                coeficiente=float(coeficientes[j]),
                contribucion=float(matriz[i, j]),
            )
            for j, columna in enumerate(modelo.cols_pd)
        ]
        items.sort(key=lambda item: item.contribucion)
        resultado.append(items)
    return resultado


def _construir_predicciones(
    modelo: ModeloECL,
    df: pd.DataFrame,
    metadata: dict[str, object],
) -> tuple[list[LoanPrediction], TotalesCartera, list[list[str]]]:
    salida = modelo.predecir(df)
    contribuciones = _contribuciones_por_fila(modelo, df)
    advertencias = _advertencias_por_fila(df, metadata)
    ids = df["id"].to_numpy() if "id" in df.columns else df.index.to_numpy()

    creditos: list[LoanPrediction] = []
    for i in range(len(salida)):
        fila = salida.iloc[i]
        creditos.append(
            LoanPrediction(
                id=normalizar_id(ids[i]),
                pd=float(fila["pd"]),
                lgd=float(fila["lgd"]),
                ead=float(fila["ead"]),
                ecl_calibrado=float(fila["ecl_calibrado"]),
                ecl_final=float(fila["ecl_final"]),
                marcado=bool(fila["marcado"]),
                banda_riesgo=int(fila["banda_riesgo"]),
                advertencias=advertencias[i],
                contribuciones=contribuciones[i],
            )
        )

    salida_totales = salida.copy()
    salida_totales["funded_amnt"] = df["funded_amnt"].to_numpy(dtype=float)
    totales = TotalesCartera(**calcular_totales(salida_totales))
    return creditos, totales, advertencias


def create_app(
    modelo: ModeloECL | None = None,
    metadata: dict[str, object] | None = None,
    ajustes: Settings | None = None,
) -> FastAPI:
    """Crea la aplicación; permite inyectar modelo y metadatos en pruebas."""
    configuracion = ajustes or settings

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        modelo_cargado = modelo or ModeloECL.cargar(configuracion.model_path)
        metadata_cargada = metadata or _cargar_metadata(
            configuracion.metadata_path
        )
        app.state.modelo = modelo_cargado
        app.state.metadata = metadata_cargada
        app.state.jobs = JobManager(
            modelo_cargado,
            metadata_cargada,
            configuracion.predictions_dir,
            configuracion.uploads_dir,
        )
        try:
            yield
        finally:
            cast(JobManager, app.state.jobs).cerrar()

    app = FastAPI(
        title=configuracion.api_title,
        version=configuracion.api_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=configuracion.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def manejador_excepcion(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Error no controlado en %s", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servicio."},
        )

    @app.get("/health", response_model=HealthResponse)
    def health(request: Request) -> HealthResponse:
        metadata_actual = _metadata(request)
        seed_raw = metadata_actual.get("seed")
        seed = (
            int(seed_raw)
            if isinstance(seed_raw, (int, float)) and not isinstance(seed_raw, bool)
            else None
        )
        return HealthResponse(
            status="ok",
            model_version=str(
                metadata_actual.get("version_modelo", "desconocida")
            ),
            seed=seed,
        )

    @app.get("/model/info", response_model=ModelInfoResponse)
    def model_info(request: Request) -> ModelInfoResponse:
        return ModelInfoResponse(
            metadata=_metadata(request),
            supuestos=SUPUESTOS,
            limites=LIMITES,
            aviso=AVISO,
        )

    @app.post("/predict", response_model=PredictResponse)
    def predict(payload: PredictRequest, request: Request) -> PredictResponse:
        modelo_actual = _modelo(request)
        metadata_actual = _metadata(request)
        df = pd.DataFrame(
            [credito.model_dump() for credito in payload.creditos]
        )
        if df["id"].isna().all():
            df = df.drop(columns=["id"])

        try:
            creditos, totales, advertencias = _construir_predicciones(
                modelo_actual,
                df,
                metadata_actual,
            )
        except Exception as exc:
            logger.exception("Error al predecir en /predict")
            raise HTTPException(
                status_code=500,
                detail=(
                    "No fue posible calcular la ECL. Verifique los datos de "
                    "entrada."
                ),
            ) from exc

        globales = (
            [
                "Algunos valores están fuera del rango de entrenamiento; "
                "revise las advertencias por crédito."
            ]
            if any(advertencias)
            else []
        )
        return PredictResponse(
            creditos=creditos,
            totales=totales,
            advertencias=globales,
        )

    @app.post(
        "/portfolio",
        response_model=JobCreatedResponse,
        status_code=202,
    )
    def portfolio(
        request: Request,
        file: UploadFile = File(...),
    ) -> JobCreatedResponse:
        if file.filename is None or not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=422,
                detail="El archivo debe tener extensión .csv.",
            )

        manager = _jobs(request)
        job_id = manager.nuevo_id()
        destino = manager.ruta_upload(job_id)
        try:
            with destino.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer, length=1024 * 1024)
        except OSError as exc:
            logger.exception("No se pudo guardar el CSV del job %s", job_id)
            raise HTTPException(
                status_code=500,
                detail="No fue posible guardar el archivo CSV.",
            ) from exc

        manager.crear_job(job_id, destino, file.filename)
        return JobCreatedResponse(job_id=job_id, status="queued")

    @app.get("/jobs/{job_id}", response_model=JobStatusResponse)
    def estado_job(job_id: str, request: Request) -> JobStatusResponse:
        estado = _jobs(request).estado(job_id)
        if estado is None:
            raise HTTPException(
                status_code=404,
                detail=f"Job '{job_id}' no encontrado.",
            )
        return estado

    @app.get(
        "/jobs/{job_id}/summary",
        response_model=JobSummaryResponse,
    )
    def resumen_job(job_id: str, request: Request) -> JobSummaryResponse:
        try:
            return _jobs(request).leer_resumen(job_id)
        except JobNoEncontrado as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Job '{job_id}' no encontrado.",
            ) from exc
        except JobNoListo as exc:
            raise HTTPException(
                status_code=409,
                detail=f"El job '{job_id}' todavía no tiene resultados.",
            ) from exc

    @app.get("/jobs/{job_id}/rows", response_model=RowsResponse)
    def filas_job(
        job_id: str,
        request: Request,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=50, ge=1, le=200),
        sort_by: CampoOrden = Query(default="ecl_final"),
        order: Literal["asc", "desc"] = Query(default="desc"),
        min_pd: float | None = Query(default=None, ge=0, le=1),
        marcado: bool | None = Query(default=None),
    ) -> RowsResponse:
        try:
            return _jobs(request).leer_filas(
                job_id,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                order=order,
                min_pd=min_pd,
                marcado=marcado,
            )
        except JobNoEncontrado as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Job '{job_id}' no encontrado.",
            ) from exc
        except JobNoListo as exc:
            raise HTTPException(
                status_code=409,
                detail=f"El job '{job_id}' todavía no tiene resultados.",
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/jobs/{job_id}/download")
    def descargar_job(job_id: str, request: Request) -> FileResponse:
        try:
            ruta = _jobs(request).ruta_csv(job_id)
        except JobNoEncontrado as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Job '{job_id}' no encontrado.",
            ) from exc
        except JobNoListo as exc:
            raise HTTPException(
                status_code=409,
                detail=f"El job '{job_id}' todavía no tiene resultados.",
            ) from exc
        return FileResponse(
            ruta,
            media_type="text/csv",
            filename=ruta.name,
        )

    @app.get("/history", response_model=list[HistoryItem])
    def historial(request: Request) -> list[HistoryItem]:
        return _jobs(request).listar_historial()

    return app


app = create_app()
