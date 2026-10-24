"""Esquemas Pydantic v2 de entrada y salida de la API ECL."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EstadoJob = Literal["queued", "running", "done", "error"]
CampoOrden = Literal[
    "id",
    "funded_amnt",
    "pd",
    "lgd",
    "ead",
    "ecl_calibrado",
    "ecl_final",
    "banda_riesgo",
]


class LoanInput(BaseModel):
    """Crédito individual con las 16 columnas requeridas por el modelo."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str | int | None = None
    funded_amnt: float = Field(gt=0)
    interest_rate: float = Field(ge=0)
    loan_term_months: Literal[36, 60]
    monthly_payment: float = Field(ge=0)
    annual_income: float = Field(gt=0)
    dept_paym_income_ratio: float = Field(ge=0)
    issue_date_year: int = Field(ge=1900, le=2100)
    earliest_cr_line_year: int = Field(ge=1900, le=2100)
    num_rev_trades_op_in_24mths: float | None = Field(default=None, ge=0)
    num_inq_in_6mths: float = Field(ge=0)
    num_inq: float | None = Field(default=None, ge=0)
    num_derogatory_pub_rec: float = Field(ge=0)
    mths_since_last_installment_acc_op: float | None = Field(default=None, ge=0)
    bal_to_cred_lim: float | None = Field(default=None, ge=0)
    max_bal_owed: float | None = Field(default=None, ge=0)
    used_credit_share: float = Field(ge=0)


class PredictRequest(BaseModel):
    """Solicitud de predicción para un lote pequeño de créditos."""

    creditos: list[LoanInput] = Field(min_length=1, max_length=1_000)


class Contribucion(BaseModel):
    """Contribución de una variable al logit del modelo PD."""

    variable: str
    valor_woe: float
    coeficiente: float
    contribucion: float


class LoanPrediction(BaseModel):
    """Resultado ECL y factores de riesgo de un crédito."""

    id: str | int | None
    pd: float
    lgd: float
    ead: float
    ecl_calibrado: float
    ecl_final: float
    marcado: bool
    banda_riesgo: int
    advertencias: list[str] = Field(default_factory=list)
    contribuciones: list[Contribucion] = Field(default_factory=list)


class TotalesCartera(BaseModel):
    """Agregados principales de una cartera."""

    n: int
    exposicion_total: float
    ecl_calibrado_total: float
    ecl_final_total: float
    ratio_final_calibrado: float | None
    pct_marcados: float
    pd_media: float


class PredictResponse(BaseModel):
    """Respuesta del endpoint de predicción individual/lote pequeño."""

    creditos: list[LoanPrediction]
    totales: TotalesCartera
    advertencias: list[str] = Field(default_factory=list)


class ValorFueraRango(BaseModel):
    """Valor de entrada fuera del rango observado en entrenamiento."""

    columna: str
    fila: int
    valor: float
    minimo: float
    maximo: float


class DataQualityReport(BaseModel):
    """Reporte de calidad de datos de un CSV de cartera."""

    filas_leidas: int
    filas_procesadas: int
    columnas_faltantes: list[str]
    valores_faltantes: dict[str, int]
    total_fuera_rango: int
    valores_fuera_rango: list[ValorFueraRango]
    identificadores_duplicados: int
    advertencias: list[str]


class JobCreatedResponse(BaseModel):
    """Confirmación de encolamiento de una cartera."""

    job_id: str
    status: EstadoJob


class JobStatusResponse(BaseModel):
    """Estado y resultados de una corrida en segundo plano."""

    job_id: str
    status: EstadoJob
    mensaje: str
    fecha_creacion: str
    nombre_archivo: str
    reporte_calidad: DataQualityReport | None = None
    totales: TotalesCartera | None = None


class HistogramaPD(BaseModel):
    """Bin del histograma de probabilidades de default."""

    bin_inicio: float
    bin_fin: float
    n: int


class DecilRiesgo(BaseModel):
    """Agregados por banda de riesgo."""

    banda_riesgo: int
    n: int
    pd_media: float
    ecl_calibrado: float
    ecl_final: float


class AgrupacionPlazo(BaseModel):
    """Agregados por plazo del crédito."""

    plazo_meses: int
    n: int
    exposicion_total: float
    ecl_calibrado: float
    ecl_final: float


class AgrupacionAno(BaseModel):
    """Agregados por año de originación."""

    anio: int
    n: int
    exposicion_total: float
    ecl_calibrado: float
    ecl_final: float


class TopCredito(BaseModel):
    """Crédito con mayor ECL final."""

    id: str | int | None
    funded_amnt: float
    pd: float
    ecl_final: float


class JobSummaryResponse(BaseModel):
    """Agregados para los gráficos de la interfaz."""

    job_id: str
    histograma_pd: list[HistogramaPD]
    por_decil: list[DecilRiesgo]
    por_plazo: list[AgrupacionPlazo]
    por_ano: list[AgrupacionAno]
    top_creditos: list[TopCredito]


class LoanRow(BaseModel):
    """Fila paginada de una cartera procesada."""

    id: str | int | None
    funded_amnt: float
    pd: float
    lgd: float
    ead: float
    ecl_calibrado: float
    ecl_final: float
    marcado: bool
    banda_riesgo: int


class RowsResponse(BaseModel):
    """Página de créditos de una corrida."""

    job_id: str
    total: int
    page: int
    page_size: int
    rows: list[LoanRow]


class HistoryItem(BaseModel):
    """Resumen de una corrida guardada en disco."""

    job_id: str
    fecha: str
    nombre_archivo: str
    n: int
    exposicion_total: float
    ecl_calibrado_total: float
    ecl_final_total: float
    pct_marcados: float
    pd_media: float
    version_modelo: str


class HealthResponse(BaseModel):
    """Estado del servicio."""

    status: str
    model_version: str
    seed: int | None


class ModelInfoResponse(BaseModel):
    """Metadatos del modelo y textos de contexto."""

    metadata: dict[str, object]
    supuestos: list[str]
    limites: list[str]
    aviso: str
