import { Info } from "lucide-react";
import type { ReactNode } from "react";

import type { TotalesCartera } from "@/lib/api";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

function KpiCard({
  label,
  value,
  detail,
  tooltip,
}: {
  label: string;
  value: string;
  detail?: string;
  tooltip?: string;
}) {
  return (
    <Card>
      <CardContent className="space-y-1.5 py-4">
        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <span>{label}</span>
          {tooltip ? (
            <Tooltip>
              <TooltipTrigger
                type="button"
                className="inline-flex size-4 items-center justify-center rounded-full text-muted-foreground hover:text-foreground"
                aria-label={`Más información sobre ${label}`}
              >
                <Info className="size-3.5" />
              </TooltipTrigger>
              <TooltipContent>{tooltip}</TooltipContent>
            </Tooltip>
          ) : null}
        </div>
        <p className="text-2xl font-semibold tracking-tight tabular-nums">
          {value}
        </p>
        {detail ? (
          <p className="text-xs text-muted-foreground tabular-nums">{detail}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function KpiGrid({ totales }: { totales: TotalesCartera }) {
  const ratio =
    totales.ratio_final_calibrado === null
      ? "—"
      : `${formatNumber(totales.ratio_final_calibrado, 2)}×`;

  const items: {
    label: string;
    value: string;
    detail?: string;
    tooltip?: string;
  }[] = [
    {
      label: "Créditos",
      value: formatNumber(totales.n),
      detail: "Registros procesados",
    },
    {
      label: "Exposición total",
      value: formatCurrency(totales.exposicion_total),
      detail: "Monto financiado agregado",
    },
    {
      label: "ECL calibrado",
      value: formatCurrency(totales.ecl_calibrado_total),
      detail: "PD × LGD × EAD",
      tooltip:
        "Pérdida esperada calibrada: PD × LGD × EAD, sin el margen de prudencia del modelo.",
    },
    {
      label: "ECL con margen",
      value: formatCurrency(totales.ecl_final_total),
      detail: "Estimación final de la cartera",
      tooltip:
        "Pérdida esperada final: ECL calibrado multiplicado por el factor de cobertura definido en el modelo.",
    },
    {
      label: "Relación margen / calibrado",
      value: ratio,
      detail: "Efecto del margen de prudencia",
      tooltip:
        "ECL con margen dividido por ECL calibrado. Mide el efecto del margen de prudencia.",
    },
    {
      label: "Créditos marcados",
      value: formatPercent(totales.pct_marcados),
      detail: "Sobre el total procesado",
      tooltip:
        "Porcentaje de créditos cuya PD supera el umbral de marcación definido por el modelo.",
    },
    {
      label: "PD media",
      value: formatPercent(totales.pd_media),
      detail: "Probabilidad de default promedio",
      tooltip: "Probabilidad de default promedio de la cartera procesada.",
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
      {items.map((item) => (
        <KpiCard key={item.label} {...item} />
      ))}
    </div>
  );
}

export function KpiGridFallback({ children }: { children: ReactNode }) {
  return <div className="grid gap-3">{children}</div>;
}
