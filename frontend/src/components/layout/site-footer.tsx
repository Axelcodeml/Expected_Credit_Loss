"use client";

import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/lib/api";

export function SiteFooter() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    staleTime: Number.POSITIVE_INFINITY,
  });

  const health = healthQuery.data;
  const estadoModelo = health
    ? `Modelo v${health.model_version}${
        health.seed === null ? "" : ` · Semilla ${health.seed}`
      }`
    : healthQuery.isError
      ? "API no disponible"
      : "Conectando con la API…";

  return (
    <footer className="border-t bg-background">
      <div className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-5 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
        <p>ECL · Herramienta de apoyo analítico. Uso interno.</p>
        <p className="tabular-nums">{estadoModelo}</p>
      </div>
    </footer>
  );
}
