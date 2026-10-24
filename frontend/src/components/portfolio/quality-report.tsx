import { AlertTriangle, CheckCircle2 } from "lucide-react";

import type { DataQualityReport } from "@/lib/api";
import { formatNumber } from "@/lib/format";
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

export function QualityReport({ report }: { report: DataQualityReport }) {
  const valoresFaltantes = Object.entries(report.valores_faltantes).filter(
    ([, cantidad]) => cantidad > 0,
  );
  const sinProblemas =
    report.columnas_faltantes.length === 0 &&
    valoresFaltantes.length === 0 &&
    report.total_fuera_rango === 0 &&
    report.identificadores_duplicados === 0 &&
    report.advertencias.length === 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Reporte de calidad de datos</CardTitle>
          <Badge variant={sinProblemas ? "secondary" : "outline"}>
            {sinProblemas ? (
              <>
                <CheckCircle2 /> Sin hallazgos
              </>
            ) : (
              <>
                <AlertTriangle /> Revisar
              </>
            )}
          </Badge>
        </div>
        <CardDescription>
          Validaciones aplicadas antes de calcular las estimaciones.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Dato label="Filas leídas" value={formatNumber(report.filas_leidas)} />
          <Dato
            label="Filas procesadas"
            value={formatNumber(report.filas_procesadas)}
          />
          <Dato
            label="Columnas faltantes"
            value={formatNumber(report.columnas_faltantes.length)}
          />
          <Dato
            label="Valores fuera de rango"
            value={formatNumber(report.total_fuera_rango)}
          />
          <Dato
            label="IDs duplicados"
            value={formatNumber(report.identificadores_duplicados)}
          />
        </div>

        {report.columnas_faltantes.length > 0 ? (
          <section>
            <h3 className="mb-2 text-sm font-medium">Columnas faltantes</h3>
            <div className="flex flex-wrap gap-1.5">
              {report.columnas_faltantes.map((columna) => (
                <Badge key={columna} variant="destructive">
                  {columna}
                </Badge>
              ))}
            </div>
          </section>
        ) : null}

        {valoresFaltantes.length > 0 ? (
          <section>
            <h3 className="mb-2 text-sm font-medium">Valores faltantes por columna</h3>
            <div className="flex flex-wrap gap-1.5">
              {valoresFaltantes.map(([columna, cantidad]) => (
                <Badge key={columna} variant="outline">
                  {columna}: {formatNumber(cantidad)}
                </Badge>
              ))}
            </div>
          </section>
        ) : null}

        {report.valores_fuera_rango.length > 0 ? (
          <section>
            <h3 className="mb-2 text-sm font-medium">
              Primeros valores fuera del rango de entrenamiento
            </h3>
            <div className="overflow-hidden rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Columna</TableHead>
                    <TableHead>Fila</TableHead>
                    <TableHead>Valor</TableHead>
                    <TableHead>Rango observado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {report.valores_fuera_rango.slice(0, 10).map((item, index) => (
                    <TableRow key={`${item.columna}-${item.fila}-${index}`}>
                      <TableCell className="font-medium">{item.columna}</TableCell>
                      <TableCell>{formatNumber(item.fila)}</TableCell>
                      <TableCell>{formatNumber(item.valor, 2)}</TableCell>
                      <TableCell>
                        {formatNumber(item.minimo, 2)} – {formatNumber(item.maximo, 2)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </section>
        ) : null}

        {report.advertencias.length > 0 ? (
          <section>
            <h3 className="mb-2 text-sm font-medium">Advertencias</h3>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {report.advertencias.map((advertencia) => (
                <li key={advertencia}>{advertencia}</li>
              ))}
            </ul>
          </section>
        ) : null}
      </CardContent>
    </Card>
  );
}

function Dato({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{value}</p>
    </div>
  );
}
