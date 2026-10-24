"""Gestión de corridas de cartera en segundo plano y persistencia en disco."""

from __future__ import annotations

import copy
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd

from api.schemas import (
    AgrupacionAno,
    AgrupacionPlazo,
    DataQualityReport,
    DecilRiesgo,
    EstadoJob,
    HistogramaPD,
    HistoryItem,
    JobStatusResponse,
    JobSummaryResponse,
    LoanRow,
    RowsResponse,
    TopCredito,
    TotalesCartera,
    ValorFueraRango,
)
from predict import ResultadoCartera, calcular_totales, predecir_cartera
from src.ecl.model import ModeloECL
from src.ecl.preprocessing import COLUMNAS_ENTRADA, COLUMNAS_NO_NULABLES

logger = logging.getLogger(__name__)


class JobNoEncontrado(Exception):
    """No existe una corrida con el identificador solicitado."""


class JobNoListo(Exception):
    """La corrida existe pero todavía no tiene resultados disponibles."""


@dataclass
class Job:
    """Estado interno de una corrida."""

    job_id: str
    nombre_archivo: str
    created_at: str
    version_modelo: str
    status: EstadoJob = "queued"
    mensaje: str = "En cola."
    csv_path: Path | None = None
    parquet_path: Path | None = None
    resumen_path: Path | None = None
    summary_path: Path | None = None
    quality_path: Path | None = None
    totales: TotalesCartera | None = None
    reporte_calidad: DataQualityReport | None = None
    summary: JobSummaryResponse | None = None


def normalizar_id(valor: object) -> str | int | None:
    if valor is None:
        return None
    if isinstance(valor, np.integer):
        return int(valor)
    if isinstance(valor, np.floating):
        numero = float(valor)
        if np.isnan(numero):
            return None
        return int(numero) if numero.is_integer() else str(numero)
    if isinstance(valor, (int, str)):
        return valor
    if isinstance(valor, float):
        if np.isnan(valor):
            return None
        return int(valor) if valor.is_integer() else str(valor)
    if pd.isna(valor):
        return None
    return str(valor)


def _numero(valor: object, defecto: float = 0.0) -> float:
    if isinstance(valor, bool):
        return float(valor)
    if isinstance(valor, (int, float, np.integer, np.floating)):
        numero = float(valor)
        return numero if np.isfinite(numero) else defecto
    return defecto


def _texto(valor: object, defecto: str) -> str:
    return valor if isinstance(valor, str) else defecto


def rangos_entrenamiento(
    metadata: dict[str, object],
) -> dict[str, tuple[float, float]]:
    rangos_raw = metadata.get("rangos_entrenamiento")
    if not isinstance(rangos_raw, dict):
        return {}

    rangos: dict[str, tuple[float, float]] = {}
    for columna, rango in rangos_raw.items():
        if not isinstance(columna, str) or not isinstance(rango, dict):
            continue
        minimo = rango.get("min")
        maximo = rango.get("max")
        if (
            isinstance(minimo, (int, float))
            and not isinstance(minimo, bool)
            and isinstance(maximo, (int, float))
            and not isinstance(maximo, bool)
        ):
            rangos[columna] = (float(minimo), float(maximo))
    return rangos


def construir_reporte_calidad(
    df: pd.DataFrame,
    metadata: dict[str, object],
) -> tuple[DataQualityReport, list[str]]:
    """Construye el reporte de calidad y la lista de errores bloqueantes."""
    filas = int(len(df))
    faltantes = [col for col in COLUMNAS_ENTRADA if col not in df.columns]
    valores_faltantes = {
        col: int(df[col].isna().sum())
        for col in COLUMNAS_ENTRADA
        if col in df.columns
    }
    duplicados = int(df["id"].duplicated().sum()) if "id" in df.columns else 0

    errores: list[str] = []
    advertencias: list[str] = []

    if filas == 0:
        errores.append("El archivo no contiene filas.")
    if faltantes:
        errores.append(f"Faltan columnas requeridas: {', '.join(faltantes)}.")

    for columna in COLUMNAS_NO_NULABLES:
        if columna in df.columns:
            nulos = int(df[columna].isna().sum())
            if nulos > 0:
                errores.append(
                    f"La columna '{columna}' no admite valores faltantes; "
                    f"se encontraron {nulos}."
                )

    for columna in COLUMNAS_ENTRADA:
        if columna not in df.columns:
            continue
        serie = pd.to_numeric(df[columna], errors="coerce")
        no_numericos = df[columna].notna() & serie.isna()
        if bool(no_numericos.any()):
            errores.append(
                f"La columna '{columna}' contiene "
                f"{int(no_numericos.sum())} valores no numéricos."
            )
        if columna == "loan_term_months":
            terminos = serie.dropna()
            invalidos = terminos[~terminos.isin([36, 60])]
            if len(invalidos) > 0:
                errores.append(
                    "La columna 'loan_term_months' solo admite los valores 36 o 60."
                )

    if duplicados > 0:
        advertencias.append(
            f"Se encontraron {duplicados} identificadores duplicados; "
            "se procesan sin rechazarlos."
        )

    valores_fuera: list[ValorFueraRango] = []
    total_fuera = 0
    columnas_fuera: set[str] = set()
    for columna, (minimo, maximo) in rangos_entrenamiento(metadata).items():
        if columna not in COLUMNAS_ENTRADA or columna not in df.columns:
            continue
        serie = pd.to_numeric(df[columna], errors="coerce")
        fuera = serie.notna() & ((serie < minimo) | (serie > maximo))
        cantidad = int(fuera.sum())
        if cantidad > 0:
            total_fuera += cantidad
            columnas_fuera.add(columna)
        if len(valores_fuera) < 100:
            posiciones = np.flatnonzero(fuera.to_numpy())[: 100 - len(valores_fuera)]
            for posicion in posiciones:
                valores_fuera.append(
                    ValorFueraRango(
                        columna=columna,
                        fila=int(posicion),
                        valor=float(serie.iloc[int(posicion)]),
                        minimo=minimo,
                        maximo=maximo,
                    )
                )

    if total_fuera > 0:
        advertencias.append(
            f"Se encontraron {total_fuera} valores fuera del rango de "
            f"entrenamiento en {len(columnas_fuera)} columna(s)."
        )

    reporte = DataQualityReport(
        filas_leidas=filas,
        filas_procesadas=0,
        columnas_faltantes=faltantes,
        valores_faltantes=valores_faltantes,
        total_fuera_rango=total_fuera,
        valores_fuera_rango=valores_fuera,
        identificadores_duplicados=duplicados,
        advertencias=advertencias,
    )
    return reporte, errores


def _construir_summary(job_id: str, datos: pd.DataFrame) -> JobSummaryResponse:
    id_col = "id" if "id" in datos.columns else "credito_id"
    conteo, bordes = np.histogram(
        datos["pd"].to_numpy(dtype=float),
        bins=10,
        range=(0.0, 1.0),
    )
    histograma = [
        HistogramaPD(
            bin_inicio=float(bordes[i]),
            bin_fin=float(bordes[i + 1]),
            n=int(conteo[i]),
        )
        for i in range(10)
    ]

    por_decil: list[DecilRiesgo] = []
    for banda in range(1, 11):
        grupo = datos[datos["banda_riesgo"] == banda]
        por_decil.append(
            DecilRiesgo(
                banda_riesgo=banda,
                n=int(len(grupo)),
                pd_media=float(grupo["pd"].mean()) if len(grupo) > 0 else 0.0,
                ecl_calibrado=float(grupo["ecl_calibrado"].sum()),
                ecl_final=float(grupo["ecl_final"].sum()),
            )
        )

    por_plazo: list[AgrupacionPlazo] = []
    plazos = datos["loan_term_months"].round()
    for plazo in (36, 60):
        grupo = datos[plazos == plazo]
        por_plazo.append(
            AgrupacionPlazo(
                plazo_meses=plazo,
                n=int(len(grupo)),
                exposicion_total=float(grupo["funded_amnt"].sum()),
                ecl_calibrado=float(grupo["ecl_calibrado"].sum()),
                ecl_final=float(grupo["ecl_final"].sum()),
            )
        )

    por_ano: list[AgrupacionAno] = []
    anios = sorted(
        int(anio)
        for anio in datos["issue_date_year"].dropna().unique().tolist()
    )
    for anio in anios:
        grupo = datos[datos["issue_date_year"] == anio]
        por_ano.append(
            AgrupacionAno(
                anio=anio,
                n=int(len(grupo)),
                exposicion_total=float(grupo["funded_amnt"].sum()),
                ecl_calibrado=float(grupo["ecl_calibrado"].sum()),
                ecl_final=float(grupo["ecl_final"].sum()),
            )
        )

    top = datos.sort_values("ecl_final", ascending=False).head(20)
    top_creditos = [
        TopCredito(
            id=normalizar_id(fila[id_col]),
            funded_amnt=float(fila["funded_amnt"]),
            pd=float(fila["pd"]),
            ecl_final=float(fila["ecl_final"]),
        )
        for _, fila in top.iterrows()
    ]

    return JobSummaryResponse(
        job_id=job_id,
        histograma_pd=histograma,
        por_decil=por_decil,
        por_plazo=por_plazo,
        por_ano=por_ano,
        top_creditos=top_creditos,
    )


def _escribir_json(ruta: Path, contenido: object) -> None:
    ruta.write_text(
        json.dumps(contenido, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _ruta_si_existe(ruta: Path) -> Path | None:
    return ruta if ruta.exists() else None


class JobManager:
    """Coordina cargas, predicciones en segundo plano e histórico en disco."""

    def __init__(
        self,
        modelo: ModeloECL,
        metadata: dict[str, object],
        predictions_dir: str | Path,
        uploads_dir: str | Path,
    ) -> None:
        self.modelo = modelo
        self.metadata = metadata
        self.predictions_dir = Path(predictions_dir)
        self.uploads_dir = Path(uploads_dir)
        self.predictions_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="ecl-job",
        )
        self._cargar_historial()

    @staticmethod
    def nuevo_id() -> str:
        marca = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return f"{marca}_{uuid4().hex[:8]}"

    def ruta_upload(self, job_id: str) -> Path:
        return self.uploads_dir / f"{job_id}.csv"

    def crear_job(self, job_id: str, ruta: Path, nombre_archivo: str) -> None:
        job = Job(
            job_id=job_id,
            nombre_archivo=nombre_archivo,
            created_at=datetime.now(timezone.utc).isoformat(),
            version_modelo=self.modelo.version,
        )
        with self._lock:
            self._jobs[job_id] = job
        self._executor.submit(self._procesar, job_id, ruta)

    def _marcar(
        self,
        job_id: str,
        status: EstadoJob,
        mensaje: str,
        reporte: DataQualityReport | None = None,
        quality_path: Path | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = status
            job.mensaje = mensaje
            if reporte is not None:
                job.reporte_calidad = reporte
            if quality_path is not None:
                job.quality_path = quality_path

    def _marcar_done(
        self,
        job_id: str,
        totales: TotalesCartera,
        reporte: DataQualityReport,
        summary: JobSummaryResponse,
        resultado: ResultadoCartera,
        summary_path: Path,
        quality_path: Path,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "done"
            job.mensaje = f"Procesados {totales.n} créditos."
            job.totales = totales
            job.reporte_calidad = reporte
            job.summary = summary
            job.summary_path = summary_path
            job.quality_path = quality_path
            job.csv_path = resultado.csv_path
            job.parquet_path = resultado.parquet_path
            job.resumen_path = resultado.resumen_path

    def _procesar(self, job_id: str, ruta: Path) -> None:
        self._marcar(job_id, "running", "Leyendo archivo CSV...")
        try:
            df = pd.read_csv(ruta, low_memory=False)
        except Exception as exc:
            logger.exception("No se pudo leer el CSV del job %s", job_id)
            self._marcar(job_id, "error", f"No se pudo leer el CSV: {exc}")
            return

        reporte, errores = construir_reporte_calidad(df, self.metadata)
        quality_path = self.predictions_dir / f"ecl_{job_id}_quality.json"
        _escribir_json(quality_path, reporte.model_dump())
        if errores:
            self._marcar(
                job_id,
                "error",
                " ".join(errores),
                reporte=reporte,
                quality_path=quality_path,
            )
            return

        try:
            df_entrada = df[list(COLUMNAS_ENTRADA)].copy()
            for columna in COLUMNAS_ENTRADA:
                df_entrada[columna] = pd.to_numeric(
                    df_entrada[columna],
                    errors="coerce",
                )
            if "id" in df.columns:
                df_entrada.insert(0, "id", df["id"])

            resultado = predecir_cartera(
                df_entrada,
                self.modelo,
                self.predictions_dir,
                job_id=job_id,
            )
            salida = pd.read_parquet(resultado.parquet_path)
            datos = salida.copy()
            datos["loan_term_months"] = df_entrada["loan_term_months"].to_numpy(
                dtype=float
            )
            datos["issue_date_year"] = df_entrada["issue_date_year"].to_numpy(
                dtype=float
            )

            reporte.filas_procesadas = int(len(salida))
            _escribir_json(quality_path, reporte.model_dump())

            totales = TotalesCartera(**calcular_totales(salida))
            summary = _construir_summary(job_id, datos)
            summary_path = self.predictions_dir / f"ecl_{job_id}_summary.json"
            _escribir_json(summary_path, summary.model_dump())

            self._marcar_done(
                job_id,
                totales,
                reporte,
                summary,
                resultado,
                summary_path,
                quality_path,
            )
        except Exception as exc:
            logger.exception("Error al procesar el job %s", job_id)
            self._marcar(
                job_id,
                "error",
                f"Error al procesar la cartera: {exc}",
                reporte=reporte,
                quality_path=quality_path,
            )

    def _cargar_historial(self) -> None:
        for resumen_path in sorted(
            self.predictions_dir.glob("ecl_*_resumen.json")
        ):
            job_id = (
                resumen_path.name.removeprefix("ecl_").removesuffix(
                    "_resumen.json"
                )
            )
            if job_id in self._jobs:
                continue
            try:
                data = json.loads(resumen_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                logger.warning("No se pudo leer el resumen %s", resumen_path)
                continue
            if not isinstance(data, dict):
                continue

            n = int(_numero(data.get("n", data.get("n_creditos", 0))))
            ratio_raw = data.get("ratio_final_calibrado")
            totales = TotalesCartera(
                n=n,
                exposicion_total=_numero(data.get("exposicion_total")),
                ecl_calibrado_total=_numero(data.get("ecl_calibrado_total")),
                ecl_final_total=_numero(data.get("ecl_final_total")),
                ratio_final_calibrado=(
                    _numero(ratio_raw) if ratio_raw is not None else None
                ),
                pct_marcados=_numero(data.get("pct_marcados")),
                pd_media=_numero(data.get("pd_media")),
            )
            creado = datetime.fromtimestamp(
                resumen_path.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()
            self._jobs[job_id] = Job(
                job_id=job_id,
                nombre_archivo="histórico",
                created_at=creado,
                version_modelo=_texto(data.get("version_modelo"), "desconocida"),
                status="done",
                mensaje="Corrida cargada desde disco.",
                csv_path=_ruta_si_existe(
                    self.predictions_dir / f"ecl_{job_id}.csv"
                ),
                parquet_path=_ruta_si_existe(
                    self.predictions_dir / f"ecl_{job_id}.parquet"
                ),
                resumen_path=resumen_path,
                summary_path=_ruta_si_existe(
                    self.predictions_dir / f"ecl_{job_id}_summary.json"
                ),
                quality_path=_ruta_si_existe(
                    self.predictions_dir / f"ecl_{job_id}_quality.json"
                ),
                totales=totales,
            )

    def estado(self, job_id: str) -> JobStatusResponse | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            copia = copy.deepcopy(job)
        return JobStatusResponse(
            job_id=copia.job_id,
            status=copia.status,
            mensaje=copia.mensaje,
            fecha_creacion=copia.created_at,
            nombre_archivo=copia.nombre_archivo,
            reporte_calidad=copia.reporte_calidad,
            totales=copia.totales,
        )

    def leer_resumen(self, job_id: str) -> JobSummaryResponse:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNoEncontrado(job_id)
            copia = copy.deepcopy(job)
        if copia.summary is not None:
            return copia.summary
        if copia.status != "done":
            raise JobNoListo(job_id)
        if copia.summary_path is None or not copia.summary_path.exists():
            raise JobNoListo(job_id)
        data = json.loads(copia.summary_path.read_text(encoding="utf-8"))
        return JobSummaryResponse.model_validate(data)

    def leer_filas(
        self,
        job_id: str,
        page: int,
        page_size: int,
        sort_by: str,
        order: str,
        min_pd: float | None,
        marcado: bool | None,
    ) -> RowsResponse:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNoEncontrado(job_id)
            copia = copy.deepcopy(job)
        if (
            copia.status != "done"
            or copia.parquet_path is None
            or not copia.parquet_path.exists()
        ):
            raise JobNoListo(job_id)

        datos = pd.read_parquet(copia.parquet_path)
        if min_pd is not None:
            datos = datos[datos["pd"] >= min_pd]
        if marcado is not None:
            datos = datos[datos["marcado"] == marcado]

        columna_orden = sort_by
        if sort_by == "id" and "id" not in datos.columns:
            columna_orden = "credito_id"
        if columna_orden not in datos.columns:
            raise ValueError(f"Columna de orden no válida: {sort_by}")

        datos = datos.sort_values(
            columna_orden,
            ascending=(order == "asc"),
            kind="mergesort",
        )
        total = int(len(datos))
        inicio = (page - 1) * page_size
        pagina = datos.iloc[inicio : inicio + page_size]
        id_col = "id" if "id" in pagina.columns else "credito_id"

        filas = [
            LoanRow(
                id=normalizar_id(fila[id_col]),
                funded_amnt=float(fila["funded_amnt"]),
                pd=float(fila["pd"]),
                lgd=float(fila["lgd"]),
                ead=float(fila["ead"]),
                ecl_calibrado=float(fila["ecl_calibrado"]),
                ecl_final=float(fila["ecl_final"]),
                marcado=bool(fila["marcado"]),
                banda_riesgo=int(fila["banda_riesgo"]),
            )
            for _, fila in pagina.iterrows()
        ]
        return RowsResponse(
            job_id=job_id,
            total=total,
            page=page,
            page_size=page_size,
            rows=filas,
        )

    def ruta_csv(self, job_id: str) -> Path:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNoEncontrado(job_id)
            copia = copy.deepcopy(job)
        if (
            copia.status != "done"
            or copia.csv_path is None
            or not copia.csv_path.exists()
        ):
            raise JobNoListo(job_id)
        return copia.csv_path

    def listar_historial(self) -> list[HistoryItem]:
        with self._lock:
            jobs = [copy.deepcopy(job) for job in self._jobs.values()]

        items: list[HistoryItem] = []
        for job in jobs:
            if job.status != "done" or job.totales is None:
                continue
            items.append(
                HistoryItem(
                    job_id=job.job_id,
                    fecha=job.created_at,
                    nombre_archivo=job.nombre_archivo,
                    n=job.totales.n,
                    exposicion_total=job.totales.exposicion_total,
                    ecl_calibrado_total=job.totales.ecl_calibrado_total,
                    ecl_final_total=job.totales.ecl_final_total,
                    pct_marcados=job.totales.pct_marcados,
                    pd_media=job.totales.pd_media,
                    version_modelo=job.version_modelo,
                )
            )
        return sorted(items, key=lambda item: item.fecha, reverse=True)

    def cerrar(self) -> None:
        self._executor.shutdown(wait=True)

