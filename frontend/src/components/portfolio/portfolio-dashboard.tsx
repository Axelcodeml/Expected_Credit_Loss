"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowRight, FileCheck2, UploadCloud } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";

import type { SortField, SortOrder } from "@/lib/api";
import {
  getJob,
  getJobSummary,
  getRows,
  mensajeError,
  uploadPortfolio,
} from "@/lib/api";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState, ErrorState, LoadingCards, LoadingState } from "@/components/common/states";
import { JobProgress } from "@/components/portfolio/job-progress";
import { KpiGrid } from "@/components/portfolio/kpi-grid";
import { PortfolioCharts } from "@/components/portfolio/portfolio-charts";
import { QualityReport } from "@/components/portfolio/quality-report";
import { RowsTable } from "@/components/portfolio/rows-table";
import { UploadCard } from "@/components/portfolio/upload-card";

export function PortfolioDashboard() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [sortBy, setSortBy] = useState<SortField>("ecl_final");
  const [order, setOrder] = useState<SortOrder>("desc");
  const [minPdPct, setMinPdPct] = useState("");
  const [soloMarcados, setSoloMarcados] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: uploadPortfolio,
    onMutate: () => {
      setUploadError(null);
      setJobId(null);
    },
    onSuccess: (data) => {
      setJobId(data.job_id);
      setPage(1);
    },
    onError: (error) => {
      setUploadError(mensajeError(error));
    },
  });

  const jobQuery = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId as string),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const estado = query.state.data?.status;
      return estado === "queued" || estado === "running" ? 1_500 : false;
    },
  });

  const job = jobQuery.data ?? null;
  const listo = job?.status === "done";

  const summaryQuery = useQuery({
    queryKey: ["summary", jobId],
    queryFn: () => getJobSummary(jobId as string),
    enabled: Boolean(jobId && listo),
  });

  const minPdNumber = minPdPct.trim() === "" ? null : Number(minPdPct);
  const minPdInvalido =
    minPdNumber !== null &&
    (!Number.isFinite(minPdNumber) || minPdNumber < 0 || minPdNumber > 100);
  const minPd =
    minPdNumber === null || minPdInvalido ? null : minPdNumber / 100;

  const rowsQuery = useQuery({
    queryKey: [
      "rows",
      jobId,
      page,
      pageSize,
      sortBy,
      order,
      minPd,
      soloMarcados,
    ],
    queryFn: () =>
      getRows(jobId as string, {
        page,
        pageSize,
        sortBy,
        order,
        minPd,
        marcado: soloMarcados ? true : null,
      }),
    enabled: Boolean(jobId && listo && !minPdInvalido),
  });

  function handleFile(file: File) {
    setUploadError(null);

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setUploadError("Seleccione un archivo con extensión .csv.");
      return;
    }

    if (file.size === 0) {
      setUploadError("El archivo está vacío.");
      return;
    }

    setFileName(file.name);
    uploadMutation.mutate(file);
  }

  async function handleUseSample() {
    setUploadError(null);

    try {
      const response = await fetch("/cartera_demo.csv", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(
          "No se encontró la cartera de ejemplo. Genérela con scripts/make_sample.py y cópiela en frontend/public.",
        );
      }

      const blob = await response.blob();
      handleFile(
        new File([blob], "cartera_demo.csv", { type: "text/csv" }),
      );
    } catch (error) {
      setUploadError(mensajeError(error));
    }
  }

  function handleMinPdChange(value: string) {
    setMinPdPct(value);
    setPage(1);
  }

  function handleSoloMarcadosChange(value: boolean) {
    setSoloMarcados(value);
    setPage(1);
  }

  function handleSortByChange(value: SortField) {
    setSortBy(value);
    setPage(1);
  }

  function handleOrderChange(value: SortOrder) {
    setOrder(value);
    setPage(1);
  }

  function handlePageSizeChange(value: number) {
    setPageSize(value);
    setPage(1);
  }

  const jobError = jobQuery.isError
    ? mensajeError(jobQuery.error)
    : job?.status === "error"
      ? job.mensaje
      : null;

  return (
    <div className="space-y-5">
      <UploadCard
        onFile={handleFile}
        onUseSample={handleUseSample}
        isUploading={uploadMutation.isPending}
        fileName={fileName}
        error={uploadError}
      />

      <JobProgress
        job={job}
        isUploading={uploadMutation.isPending}
        fileName={fileName}
      />

      {jobError ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>El procesamiento no pudo completarse</AlertTitle>
          <AlertDescription>{jobError}</AlertDescription>
        </Alert>
      ) : null}

      {job?.reporte_calidad ? <QualityReport report={job.reporte_calidad} /> : null}

      {!jobId && !uploadMutation.isPending ? (
        <Card>
          <CardHeader>
            <CardTitle>Cómo funciona</CardTitle>
            <CardDescription>
              El flujo completo se ejecuta en la API local.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3">
            <Paso
              icon={<UploadCloud className="size-4" />}
              title="1. Cargue la cartera"
              description="Un CSV con una fila por crédito y las 16 columnas de entrada."
            />
            <Paso
              icon={<FileCheck2 className="size-4" />}
              title="2. Revise la calidad"
              description="La API reporta columnas faltantes, faltantes y valores fuera de rango."
            />
            <Paso
              icon={<ArrowRight className="size-4" />}
              title="3. Analice el resultado"
              description="Consulte KPIs, gráficos, créditos marcados y descargue el detalle."
            />
          </CardContent>
        </Card>
      ) : null}

      {listo && job?.totales ? <KpiGrid totales={job.totales} /> : null}

      {listo ? (
        summaryQuery.isLoading ? (
          <LoadingCards count={2} />
        ) : summaryQuery.isError ? (
          <ErrorState
            title="No fue posible cargar los gráficos"
            message={mensajeError(summaryQuery.error)}
          />
        ) : summaryQuery.data ? (
          <PortfolioCharts summary={summaryQuery.data} />
        ) : null
      ) : null}

      {listo && jobId ? (
        rowsQuery.isLoading && !rowsQuery.data ? (
          <LoadingState label="Cargando créditos…" />
        ) : rowsQuery.isError ? (
          <ErrorState
            title="No fue posible cargar los créditos"
            message={mensajeError(rowsQuery.error)}
          />
        ) : (
          <RowsTable
            jobId={jobId}
            rows={rowsQuery.data}
            isLoading={rowsQuery.isLoading}
            isFetching={rowsQuery.isFetching}
            page={page}
            pageSize={pageSize}
            sortBy={sortBy}
            order={order}
            minPdPct={minPdPct}
            soloMarcados={soloMarcados}
            minPdInvalido={minPdInvalido}
            onPageChange={setPage}
            onPageSizeChange={handlePageSizeChange}
            onSortByChange={handleSortByChange}
            onOrderChange={handleOrderChange}
            onMinPdPctChange={handleMinPdChange}
            onSoloMarcadosChange={handleSoloMarcadosChange}
          />
        )
      ) : null}

      {job?.status === "done" && !job.totales ? (
        <EmptyState
          title="Sin totales disponibles"
          description="El job terminó, pero la API no devolvió los agregados de la cartera."
        />
      ) : null}
    </div>
  );
}

function Paso({
  icon,
  title,
  description,
}: {
  icon: ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border bg-muted/20 p-4">
      <div className="mb-2 flex size-8 items-center justify-center rounded-md bg-slate-900 text-white">
        {icon}
      </div>
      <p className="text-sm font-medium">{title}</p>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{description}</p>
    </div>
  );
}
