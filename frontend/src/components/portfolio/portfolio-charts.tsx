"use client";

import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { JobSummaryResponse } from "@/lib/api";
import {
  formatCompactCurrency,
  formatCurrency,
  formatPercent,
} from "@/lib/format";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const COLOR_CALIBRADO = "#64748b";
const COLOR_FINAL = "#0f172a";
const COLOR_PD = "#d97706";

function ChartCard({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="h-72">{children}</CardContent>
    </Card>
  );
}

export function PortfolioCharts({ summary }: { summary: JobSummaryResponse }) {
  const histograma = summary.histograma_pd.map((item) => ({
    rango: `${Math.round(item.bin_inicio * 100)}–${Math.round(item.bin_fin * 100)}%`,
    creditos: item.n,
  }));

  const porDecil = summary.por_decil.map((item) => ({
    banda: `B${item.banda_riesgo}`,
    ecl_calibrado: item.ecl_calibrado,
    ecl_final: item.ecl_final,
    pd_media: item.pd_media * 100,
  }));

  const porPlazo = summary.por_plazo.map((item) => ({
    plazo: `${item.plazo_meses} m`,
    ecl_calibrado: item.ecl_calibrado,
    ecl_final: item.ecl_final,
  }));

  const porAno = summary.por_ano.map((item) => ({
    anio: String(item.anio),
    ecl_calibrado: item.ecl_calibrado,
    ecl_final: item.ecl_final,
  }));

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <ChartCard
        title="Distribución de PD"
        description="Cantidad de créditos por rango de probabilidad de default."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={histograma} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis
              dataKey="rango"
              tick={{ fontSize: 11 }}
              interval="preserveStartEnd"
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={48}
            />
            <Tooltip
              formatter={(value) => [formatNumberValue(value), "Créditos"]}
              labelFormatter={(label) => `PD ${String(label)}`}
            />
            <Bar dataKey="creditos" name="Créditos" fill={COLOR_FINAL} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="ECL por banda de riesgo"
        description="ECL calibrado y con margen; la línea muestra la PD media."
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={porDecil} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="banda" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
            <YAxis
              yAxisId="left"
              tickFormatter={(value: number) => formatCompactCurrency(value)}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={64}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tickFormatter={(value: number) => `${value.toFixed(0)}%`}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={40}
            />
            <Tooltip
              formatter={(value, name) => {
                const numeric = Number(value);
                if (name === "PD media") {
                  return [formatPercent(numeric / 100), String(name)];
                }
                return [formatCurrency(numeric), String(name)];
              }}
            />
            <Legend />
            <Bar
              yAxisId="left"
              dataKey="ecl_calibrado"
              name="ECL calibrado"
              fill={COLOR_CALIBRADO}
              radius={[3, 3, 0, 0]}
            />
            <Bar
              yAxisId="left"
              dataKey="ecl_final"
              name="ECL con margen"
              fill={COLOR_FINAL}
              radius={[3, 3, 0, 0]}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="pd_media"
              name="PD media"
              stroke={COLOR_PD}
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="ECL por plazo"
        description="Comparación de la pérdida esperada entre plazos de 36 y 60 meses."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={porPlazo} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="plazo" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
            <YAxis
              tickFormatter={(value: number) => formatCompactCurrency(value)}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={64}
            />
            <Tooltip
              formatter={(value) => formatCurrency(Number(value))}
              labelFormatter={(label) => `Plazo ${String(label)}`}
            />
            <Legend />
            <Bar
              dataKey="ecl_calibrado"
              name="ECL calibrado"
              fill={COLOR_CALIBRADO}
              radius={[3, 3, 0, 0]}
            />
            <Bar
              dataKey="ecl_final"
              name="ECL con margen"
              fill={COLOR_FINAL}
              radius={[3, 3, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="ECL por año de originación"
        description="Evolución de la pérdida esperada según el año del crédito."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={porAno} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
            <XAxis dataKey="anio" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
            <YAxis
              tickFormatter={(value: number) => formatCompactCurrency(value)}
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={64}
            />
            <Tooltip
              formatter={(value) => formatCurrency(Number(value))}
              labelFormatter={(label) => `Año ${String(label)}`}
            />
            <Legend />
            <Bar
              dataKey="ecl_calibrado"
              name="ECL calibrado"
              fill={COLOR_CALIBRADO}
              radius={[3, 3, 0, 0]}
            />
            <Bar
              dataKey="ecl_final"
              name="ECL con margen"
              fill={COLOR_FINAL}
              radius={[3, 3, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

function formatNumberValue(value: unknown): string {
  return new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 }).format(
    Number(value),
  );
}
