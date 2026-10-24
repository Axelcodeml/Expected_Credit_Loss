"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, History } from "lucide-react";

import { downloadUrl, getHistory, mensajeError } from "@/lib/api";
import {
  formatCurrency,
  formatDate,
  formatNumber,
  formatPercent,
} from "@/lib/format";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
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

export function HistoryList() {
  const historyQuery = useQuery({
    queryKey: ["history"],
    queryFn: getHistory,
    staleTime: 15_000,
  });

  if (historyQuery.isLoading) {
    return <LoadingState label="Cargando historial…" />;
  }

  if (historyQuery.isError) {
    return (
      <ErrorState
        title="No fue posible cargar el historial"
        message={mensajeError(historyQuery.error)}
      />
    );
  }

  const items = historyQuery.data ?? [];

  if (items.length === 0) {
    return (
      <EmptyState
        title="Aún no hay corridas guardadas"
        description="Procese una cartera desde la página Cartera. Cuando termine, la corrida aparecerá en este historial."
      />
    );
  }

  const totalExposicion = items.reduce(
    (total, item) => total + item.exposicion_total,
    0,
  );
  const totalEclFinal = items.reduce(
    (total, item) => total + item.ecl_final_total,
    0,
  );

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <Resumen label="Corridas" value={formatNumber(items.length)} />
        <Resumen label="Exposición acumulada" value={formatCurrency(totalExposicion)} />
        <Resumen label="ECL con margen acumulada" value={formatCurrency(totalEclFinal)} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="size-4" />
            Corridas procesadas
          </CardTitle>
          <CardDescription>
            Ordenadas de la más reciente a la más antigua.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Fecha</TableHead>
                  <TableHead>Archivo</TableHead>
                  <TableHead className="text-right">Créditos</TableHead>
                  <TableHead className="text-right">Exposición</TableHead>
                  <TableHead className="text-right">ECL calibrada</TableHead>
                  <TableHead className="text-right">ECL con margen</TableHead>
                  <TableHead className="text-right">% marcados</TableHead>
                  <TableHead>Versión</TableHead>
                  <TableHead className="text-right">Detalle</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.job_id}>
                    <TableCell className="whitespace-nowrap">
                      {formatDate(item.fecha)}
                    </TableCell>
                    <TableCell className="max-w-56">
                      <p className="truncate font-medium">{item.nombre_archivo}</p>
                      <p className="truncate font-mono text-xs text-muted-foreground">
                        {item.job_id}
                      </p>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatNumber(item.n)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(item.exposicion_total)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(item.ecl_calibrado_total)}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatCurrency(item.ecl_final_total)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatPercent(item.pct_marcados)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">v{item.version_modelo}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <a
                        href={downloadUrl(item.job_id)}
                        download
                        className={buttonVariants({ variant: "outline", size: "sm" })}
                      >
                        <Download />
                        CSV
                      </a>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Resumen({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
      </CardContent>
    </Card>
  );
}

