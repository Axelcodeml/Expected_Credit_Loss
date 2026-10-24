import { Loader2 } from "lucide-react";

import type { JobStatusResponse } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

const ESTADOS: Record<
  JobStatusResponse["status"],
  { label: string; progress: number; description: string }
> = {
  queued: {
    label: "En cola",
    progress: 25,
    description: "La cartera fue recibida y está esperando un trabajador.",
  },
  running: {
    label: "Procesando",
    progress: 65,
    description: "Se están calculando PD, LGD, EAD y ECL para cada crédito.",
  },
  done: {
    label: "Completado",
    progress: 100,
    description: "El procesamiento terminó. Los resultados ya están disponibles.",
  },
  error: {
    label: "Error",
    progress: 100,
    description: "El procesamiento no pudo completarse. Revise el reporte de calidad.",
  },
};

interface JobProgressProps {
  job: JobStatusResponse | null;
  isUploading: boolean;
  fileName: string | null;
}

export function JobProgress({ job, isUploading, fileName }: JobProgressProps) {
  if (!job && !isUploading) {
    return null;
  }

  const estado = job ? ESTADOS[job.status] : null;
  const progress = estado ? estado.progress : isUploading ? 15 : 0;
  const nombre = job?.nombre_archivo || fileName || "archivo CSV";

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2">
            {isUploading || job?.status === "queued" || job?.status === "running" ? (
              <Loader2 className="size-4 animate-spin" />
            ) : null}
            {isUploading ? "Subiendo cartera" : estado?.label ?? "Procesando"}
          </CardTitle>
          {job ? (
            <Badge variant={job.status === "error" ? "destructive" : "secondary"}>
              {estado?.label ?? job.status}
            </Badge>
          ) : null}
        </div>
        <CardDescription>
          {isUploading
            ? "Transfiriendo el archivo a la API local."
            : estado?.description}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Progress value={progress} />
        <div className="flex flex-wrap justify-between gap-2 text-xs text-muted-foreground">
          <span className="truncate">{nombre}</span>
          {job ? <span className="font-mono">job: {job.job_id}</span> : null}
        </div>
        {job?.mensaje ? (
          <p className="text-xs text-muted-foreground">{job.mensaje}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
