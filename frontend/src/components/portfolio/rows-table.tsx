"use client";

import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  Download,
  SlidersHorizontal,
} from "lucide-react";

import type { RowsResponse, SortField, SortOrder } from "@/lib/api";
import { downloadUrl } from "@/lib/api";
import {
  formatCurrency,
  formatNumber,
  formatPercent,
} from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

const PAGE_SIZES = [10, 25, 50, 100] as const;

const SORT_OPTIONS: { value: SortField; label: string }[] = [
  { value: "ecl_final", label: "ECL con margen" },
  { value: "ecl_calibrado", label: "ECL calibrado" },
  { value: "pd", label: "PD" },
  { value: "funded_amnt", label: "Monto financiado" },
  { value: "banda_riesgo", label: "Banda de riesgo" },
  { value: "id", label: "ID" },
];

const NATIVE_SELECT_CLASS =
  "h-8 rounded-md border border-input bg-background px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:opacity-50";

function bandaClass(banda: number): string {
  if (banda <= 2) return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (banda <= 4) return "border-lime-200 bg-lime-50 text-lime-700";
  if (banda <= 6) return "border-amber-200 bg-amber-50 text-amber-700";
  if (banda <= 8) return "border-orange-200 bg-orange-50 text-orange-700";
  return "border-red-200 bg-red-50 text-red-700";
}

interface RowsTableProps {
  jobId: string;
  rows: RowsResponse | undefined;
  isLoading: boolean;
  isFetching: boolean;
  page: number;
  pageSize: number;
  sortBy: SortField;
  order: SortOrder;
  minPdPct: string;
  soloMarcados: boolean;
  minPdInvalido: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange: (pageSize: number) => void;
  onSortByChange: (sortBy: SortField) => void;
  onOrderChange: (order: SortOrder) => void;
  onMinPdPctChange: (value: string) => void;
  onSoloMarcadosChange: (value: boolean) => void;
}

export function RowsTable({
  jobId,
  rows,
  isLoading,
  isFetching,
  page,
  pageSize,
  sortBy,
  order,
  minPdPct,
  soloMarcados,
  minPdInvalido,
  onPageChange,
  onPageSizeChange,
  onSortByChange,
  onOrderChange,
  onMinPdPctChange,
  onSoloMarcadosChange,
}: RowsTableProps) {
  const total = rows?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoBack = page > 1;
  const canGoForward = page < totalPages;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Créditos procesados</CardTitle>
            <CardDescription>
              Detalle paginado con filtros y ordenamiento del resultado.
            </CardDescription>
          </div>
          <a
            href={downloadUrl(jobId)}
            className={buttonVariants({ variant: "outline", size: "sm" })}
            download
          >
            <Download />
            Descargar CSV
          </a>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-3 rounded-lg border bg-muted/20 p-3 lg:flex-row lg:flex-wrap lg:items-end">
          <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground lg:pb-2">
            <SlidersHorizontal className="size-3.5" />
            Filtros
          </div>

          <div className="space-y-1">
            <label htmlFor="min-pd" className="text-xs text-muted-foreground">
              PD mínima (%)
            </label>
            <Input
              id="min-pd"
              type="number"
              min={0}
              max={100}
              step={1}
              value={minPdPct}
              onChange={(event) => onMinPdPctChange(event.target.value)}
              placeholder="0"
              className="w-full bg-background sm:w-28"
              aria-invalid={minPdInvalido}
            />
          </div>

          <label className="flex h-8 cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={soloMarcados}
              onChange={(event) => onSoloMarcadosChange(event.target.checked)}
              className="size-4 accent-slate-900"
            />
            Solo marcados
          </label>

          <div className="space-y-1">
            <label htmlFor="sort-by" className="text-xs text-muted-foreground">
              Ordenar por
            </label>
            <select
              id="sort-by"
              value={sortBy}
              onChange={(event) => onSortByChange(event.target.value as SortField)}
              className={NATIVE_SELECT_CLASS}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={() => onOrderChange(order === "asc" ? "desc" : "asc")}
            className={cn(
              buttonVariants({ variant: "outline", size: "sm" }),
              "h-8",
            )}
            aria-label={order === "asc" ? "Orden ascendente" : "Orden descendente"}
          >
            {order === "asc" ? <ArrowUp /> : <ArrowDown />}
            {order === "asc" ? "Asc" : "Desc"}
          </button>

          <div className="space-y-1 lg:ml-auto">
            <label htmlFor="page-size" className="text-xs text-muted-foreground">
              Filas por página
            </label>
            <select
              id="page-size"
              value={pageSize}
              onChange={(event) => onPageSizeChange(Number(event.target.value))}
              className={NATIVE_SELECT_CLASS}
            >
              {PAGE_SIZES.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </div>
        </div>

        {minPdInvalido ? (
          <p className="text-xs text-destructive">
            Ingrese una PD entre 0 y 100.
          </p>
        ) : null}

        <div className="overflow-hidden rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead className="text-right">Monto</TableHead>
                <TableHead className="text-right">PD</TableHead>
                <TableHead className="text-right">LGD</TableHead>
                <TableHead className="text-right">EAD</TableHead>
                <TableHead className="text-right">ECL calibrado</TableHead>
                <TableHead className="text-right">ECL con margen</TableHead>
                <TableHead>Banda</TableHead>
                <TableHead>Marcado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell
                    colSpan={9}
                    className="py-10 text-center text-sm text-muted-foreground"
                  >
                    Cargando créditos…
                  </TableCell>
                </TableRow>
              ) : !rows || rows.rows.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={9}
                    className="py-10 text-center text-sm text-muted-foreground"
                  >
                    No hay créditos que coincidan con los filtros.
                  </TableCell>
                </TableRow>
              ) : (
                rows.rows.map((row, index) => (
                  <TableRow key={`${row.id ?? "sin-id"}-${index}`}>
                    <TableCell className="max-w-36 truncate font-mono text-xs">
                      {row.id ?? "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(row.funded_amnt)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatPercent(row.pd)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatPercent(row.lgd)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(row.ead)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatCurrency(row.ecl_calibrado)}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatCurrency(row.ecl_final)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={bandaClass(row.banda_riesgo)}>
                        B{row.banda_riesgo}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={row.marcado ? "destructive" : "secondary"}>
                        {row.marcado ? "Sí" : "No"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            {formatNumber(total)} créditos · página {page} de {totalPages}
            {isFetching ? " · actualizando…" : ""}
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onPageChange(page - 1)}
              disabled={!canGoBack || isFetching}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              <ChevronLeft />
              Anterior
            </button>
            <button
              type="button"
              onClick={() => onPageChange(page + 1)}
              disabled={!canGoForward || isFetching}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              Siguiente
              <ChevronRight />
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
