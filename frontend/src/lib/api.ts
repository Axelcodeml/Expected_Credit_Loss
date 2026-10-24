import type { components } from "@/lib/api-types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type HealthResponse = components["schemas"]["HealthResponse"];
export type ModelInfoResponse = components["schemas"]["ModelInfoResponse"];
export type LoanInput = components["schemas"]["LoanInput"];
export type PredictRequest = components["schemas"]["PredictRequest"];
export type PredictResponse = components["schemas"]["PredictResponse"];
export type LoanPrediction = components["schemas"]["LoanPrediction"];
export type Contribucion = components["schemas"]["Contribucion"];
export type JobCreatedResponse = components["schemas"]["JobCreatedResponse"];
export type JobStatusResponse = components["schemas"]["JobStatusResponse"];
export type JobSummaryResponse = components["schemas"]["JobSummaryResponse"];
export type RowsResponse = components["schemas"]["RowsResponse"];
export type LoanRow = components["schemas"]["LoanRow"];
export type HistoryItem = components["schemas"]["HistoryItem"];
export type DataQualityReport = components["schemas"]["DataQualityReport"];
export type TotalesCartera = components["schemas"]["TotalesCartera"];
export type HistogramaPD = components["schemas"]["HistogramaPD"];
export type DecilRiesgo = components["schemas"]["DecilRiesgo"];
export type AgrupacionPlazo = components["schemas"]["AgrupacionPlazo"];
export type AgrupacionAno = components["schemas"]["AgrupacionAno"];
export type TopCredito = components["schemas"]["TopCredito"];

export type EstadoJob = JobStatusResponse["status"];
export type SortField =
  | "id"
  | "funded_amnt"
  | "pd"
  | "lgd"
  | "ead"
  | "ecl_calibrado"
  | "ecl_final"
  | "banda_riesgo";
export type SortOrder = "asc" | "desc";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function detalleDeError(payload: unknown, status: number): string {
  if (!isRecord(payload)) {
    return `La API respondió con un error HTTP ${status}.`;
  }

  const detail = payload.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const mensajes = detail.map((item) => {
      if (!isRecord(item)) {
        return String(item);
      }

      const ubicacion = Array.isArray(item.loc)
        ? item.loc.filter((parte) => typeof parte === "string" || typeof parte === "number").join(".")
        : "";
      const mensaje = typeof item.msg === "string" ? item.msg : "Valor inválido";

      return ubicacion ? `${ubicacion}: ${mensaje}` : mensaje;
    });

    return mensajes.filter(Boolean).join("; ") || `Error HTTP ${status}.`;
  }

  return `La API respondió con un error HTTP ${status}.`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      ...init,
    });
  } catch {
    throw new ApiError(
      0,
      "No fue posible comunicarse con la API. Verifique que el servicio esté disponible.",
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError(response.status, detalleDeError(payload, response.status));
  }

  return payload as T;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getModelInfo(): Promise<ModelInfoResponse> {
  return request<ModelInfoResponse>("/model/info");
}

export function predict(creditos: LoanInput[]): Promise<PredictResponse> {
  const body: PredictRequest = { creditos };
  return request<PredictResponse>("/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function uploadPortfolio(file: File): Promise<JobCreatedResponse> {
  const formData = new FormData();
  formData.append("file", file);

  return request<JobCreatedResponse>("/portfolio", {
    method: "POST",
    body: formData,
  });
}

export function getJob(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/jobs/${encodeURIComponent(jobId)}`);
}

export function getJobSummary(jobId: string): Promise<JobSummaryResponse> {
  return request<JobSummaryResponse>(
    `/jobs/${encodeURIComponent(jobId)}/summary`,
  );
}

export interface RowsQuery {
  page: number;
  pageSize: number;
  sortBy: SortField;
  order: SortOrder;
  minPd: number | null;
  marcado: boolean | null;
}

export function getRows(jobId: string, query: RowsQuery): Promise<RowsResponse> {
  const params = new URLSearchParams({
    page: String(query.page),
    page_size: String(query.pageSize),
    sort_by: query.sortBy,
    order: query.order,
  });

  if (query.minPd !== null) {
    params.set("min_pd", String(query.minPd));
  }

  if (query.marcado !== null) {
    params.set("marcado", String(query.marcado));
  }

  return request<RowsResponse>(
    `/jobs/${encodeURIComponent(jobId)}/rows?${params.toString()}`,
  );
}

export function getHistory(): Promise<HistoryItem[]> {
  return request<HistoryItem[]>("/history");
}

export function downloadUrl(jobId: string): string {
  return `${API_URL}/jobs/${encodeURIComponent(jobId)}/download`;
}

export function mensajeError(error: unknown): string {
  if (error instanceof ApiError || error instanceof Error) {
    return error.message;
  }

  return "Ocurrió un error inesperado.";
}
