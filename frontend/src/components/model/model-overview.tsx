"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BookOpen, Info } from "lucide-react";
import type { ReactNode } from "react";

import { getModelInfo, mensajeError } from "@/lib/api";
import {
  asRecord,
  getNumber,
  getRecord,
  getString,
  getStringArray,
} from "@/lib/metadata";
import {
  formatCurrency,
  formatDate,
  formatNumber,
  formatPercent,
} from "@/lib/format";
import { ErrorState, LoadingState } from "@/components/common/states";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Formatter = (value: number) => string;

export function ModelOverview() {
  const infoQuery = useQuery({
    queryKey: ["model-info"],
    queryFn: getModelInfo,
    staleTime: Number.POSITIVE_INFINITY,
  });

  if (infoQuery.isLoading) {
    return <LoadingState label="Cargando ficha del modelo…" />;
  }

  if (infoQuery.isError) {
    return (
      <ErrorState
        title="No fue posible cargar el modelo"
        message={mensajeError(infoQuery.error)}
      />
    );
  }

  if (!infoQuery.data) {
    return (
      <ErrorState
        title="Sin información del modelo"
        message="La API no devolvió la ficha del modelo."
      />
    );
  }

  const info = infoQuery.data;
  const metadata = asRecord(info.metadata);
  const margen = getRecord(metadata, "margen");
  const metricas = getRecord(metadata, "metricas_holdout");
  const robustez = getRecord(metadata, "robustez_bootstrap");
  const columnasEntrada = getStringArray(metadata, "columnas_entrada");

  const version = getString(metadata, "version_modelo") ?? "—";
  const seed = getNumber(metadata, "seed");
  const fecha = getString(metadata, "fecha_entrenamiento");
  const criterio = getString(metadata, "criterio") ?? "—";
  const q = getNumber(margen, "q");
  const s = getNumber(margen, "s");
  const margenRatio = getNumber(margen, "ratio");
  const margenViolaciones = getNumber(margen, "viol");

  const metricasHoldout: {
    label: string;
    value: number | null;
    format: Formatter;
    description: string;
  }[] = [
    {
      label: "AUC",
      value: getNumber(metricas, "auc"),
      format: (value) => formatNumber(value, 4),
      description: "Capacidad discriminante del modelo PD.",
    },
    {
      label: "Gini",
      value: getNumber(metricas, "gini"),
      format: (value) => formatNumber(value, 4),
      description: "Discriminación normalizada a partir del AUC.",
    },
    {
      label: "KS",
      value: getNumber(metricas, "ks"),
      format: (value) => formatNumber(value, 4),
      description: "Separación máxima entre buenos y malos.",
    },
    {
      label: "ECL / real",
      value: getNumber(metricas, "ratio_ecl_real"),
      format: (value) => `${formatNumber(value, 4)}×`,
      description: "Relación entre la ECL estimada y la pérdida observada.",
    },
    {
      label: "Violaciones",
      value: getNumber(metricas, "violaciones_pct"),
      format: (value) => `${formatNumber(value, 2)}%`,
      description: "Porcentaje de créditos que superan el umbral de marcación.",
    },
    {
      label: "MAE",
      value: getNumber(metricas, "mae"),
      format: (value) => formatCurrency(value),
      description: "Error absoluto medio de la ECL en la muestra de validación.",
    },
    {
      label: "WAPE",
      value: getNumber(metricas, "wape"),
      format: (value) => formatPercent(value),
      description: "Error absoluto ponderado por el volumen de pérdida.",
    },
    {
      label: "MAPE",
      value: getNumber(metricas, "mape"),
      format: (value) => formatPercent(value),
      description: "Error porcentual absoluto medio.",
    },
    {
      label: "APE mediano",
      value: getNumber(metricas, "ape_mediano"),
      format: (value) => formatPercent(value),
      description: "Mediana del error porcentual absoluto.",
    },
    {
      label: "Precisión",
      value: getNumber(metricas, "precision"),
      format: (value) => formatPercent(value),
      description: "Proporción de créditos marcados que efectivamente incumplen.",
    },
    {
      label: "Recall",
      value: getNumber(metricas, "recall"),
      format: (value) => formatPercent(value),
      description: "Proporción de incumplimientos capturados por la marcación.",
    },
    {
      label: "Lift",
      value: getNumber(metricas, "lift"),
      format: (value) => `${formatNumber(value, 4)}×`,
      description: "Mejora frente a una selección aleatoria.",
    },
    {
      label: "Créditos marcados",
      value: getNumber(metricas, "pct_marcados"),
      format: (value) => formatPercent(value),
      description: "Cobertura de marcación sobre la muestra de validación.",
    },
  ];

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <InfoCard label="Versión" value={version} detail="Versión del artefacto" />
        <InfoCard
          label="Semilla"
          value={seed === null ? "—" : String(seed)}
          detail="Reproducibilidad del entrenamiento"
        />
        <InfoCard
          label="Entrenamiento"
          value={fecha ? formatDate(fecha) : "—"}
          detail="Fecha de generación del artefacto"
        />
        <InfoCard
          label="Criterio de calibración"
          value={criterio}
          detail="Criterio usado para seleccionar el margen"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <Card>
          <CardHeader>
            <CardTitle>Cómo se estima la pérdida</CardTitle>
            <CardDescription>
              El modelo combina una probabilidad de default con pérdida dado el
              incumplimiento y exposición al momento del default.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Formula
              title="ECL calibrada"
              formula="PD × LGD × EAD"
              description="Pérdida esperada antes de aplicar el margen de prudencia."
            />
            <Formula
              title="ECL con margen"
              formula="ECL calibrada × factor de cobertura"
              description="Estimación final usada en los reportes de cartera."
            />
            <Formula
              title="Probabilidad de default"
              formula="Regresión logística sobre variables transformadas a WoE"
              description="La PD se estima con las 14 variables de comportamiento y crédito del modelo."
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Margen de prudencia</CardTitle>
            <CardDescription>
              Parámetros de calibración del modelo.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <InfoRow
              label="q · cuantil de calibración"
              value={q === null ? "—" : formatNumber(q, 2)}
              tooltip="Cuantil usado para calibrar el margen de prudencia del modelo."
            />
            <InfoRow
              label="s · factor de cobertura"
              value={s === null ? "—" : formatNumber(s, 2)}
              tooltip="Factor de cobertura aplicado a la ECL calibrada."
            />
            <InfoRow
              label="Relación del margen"
              value={margenRatio === null ? "—" : `${formatNumber(margenRatio, 2)}×`}
            />
            <InfoRow
              label="Violaciones de calibración"
              value={
                margenViolaciones === null
                  ? "—"
                  : formatPercent(margenViolaciones)
              }
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Métricas de validación</CardTitle>
          <CardDescription>
            Resultados sobre la muestra holdout. Las métricas de calibración se
            interpretan junto con el margen de prudencia.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Métrica</TableHead>
                  <TableHead className="text-right">Valor</TableHead>
                  <TableHead>Lectura</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {metricasHoldout.map((metrica) => (
                  <TableRow key={metrica.label}>
                    <TableCell className="font-medium">{metrica.label}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {metrica.value === null ? "—" : metrica.format(metrica.value)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {metrica.description}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <ListCard
          title="Supuestos"
          description="Condiciones bajo las cuales el modelo fue construido."
          items={info.supuestos}
          icon={<BookOpen className="size-4" />}
        />
        <ListCard
          title="Límites"
          description="Restricciones de uso que deben considerarse al interpretar los resultados."
          items={info.limites}
          icon={<AlertTriangle className="size-4" />}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Variables de entrada</CardTitle>
          <CardDescription>
            Columnas requeridas para estimar un crédito o procesar una cartera.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-1.5">
            {columnasEntrada.map((columna) => (
              <Badge key={columna} variant="outline" className="font-mono">
                {columna}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Robustez</CardTitle>
          <CardDescription>
            Resultados del bootstrap sobre la muestra de validación.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <InfoCard
              label="Iteraciones"
              value={
                getNumber(robustez, "n_bootstrap") === null
                  ? "—"
                  : String(getNumber(robustez, "n_bootstrap"))
              }
              detail="Muestras bootstrap"
            />
            <InfoCard
              label="Ratio medio"
              value={formatNullable(getNumber(robustez, "ratio_medio"), (value) => `${formatNumber(value, 4)}×`)}
              detail="ECL / real promedio"
            />
            <InfoCard
              label="Ratio p05 – p95"
              value={`${formatNullable(getNumber(robustez, "ratio_p05"), (value) => formatNumber(value, 4))} – ${formatNullable(getNumber(robustez, "ratio_p95"), (value) => formatNumber(value, 4))}`}
              detail="Intervalo de robustez"
            />
            <InfoCard
              label="P(ratio < 1)"
              value={formatNullable(getNumber(robustez, "p_ratio_menor_1"), (value) => formatPercent(value))}
              detail="Riesgo de subestimación"
            />
          </div>
        </CardContent>
      </Card>

      <Alert>
        <Info />
        <AlertTitle>Aviso de uso</AlertTitle>
        <AlertDescription>{info.aviso}</AlertDescription>
      </Alert>
    </div>
  );
}

function InfoCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

function Formula({
  title,
  formula,
  description,
}: {
  title: string;
  formula: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <p className="text-sm font-medium">{title}</p>
      <p className="mt-1 font-mono text-sm">{formula}</p>
      <p className="mt-1 text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

function InfoRow({
  label,
  value,
  tooltip,
}: {
  label: string;
  value: string;
  tooltip?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b pb-2 last:border-b-0 last:pb-0">
      <span className="flex items-center gap-1 text-sm text-muted-foreground">
        {label}
        {tooltip ? (
          <span title={tooltip} className="inline-flex">
            <Info className="size-3.5" />
          </span>
        ) : null}
      </span>
      <span className="text-sm font-medium tabular-nums">{value}</span>
    </div>
  );
}

function ListCard({
  title,
  description,
  items,
  icon,
}: {
  title: string;
  description: string;
  items: string[];
  icon: ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {icon}
          {title}
        </CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-muted-foreground">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function formatNullable(
  value: number | null,
  formatter: (value: number) => string,
): string {
  return value === null ? "—" : formatter(value);
}
