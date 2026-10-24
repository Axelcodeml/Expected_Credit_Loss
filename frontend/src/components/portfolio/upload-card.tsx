"use client";

import {
  AlertCircle,
  FileSpreadsheet,
  Loader2,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent, KeyboardEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface UploadCardProps {
  onFile: (file: File) => void;
  onUseSample: () => void;
  isUploading: boolean;
  fileName: string | null;
  error: string | null;
}

export function UploadCard({
  onFile,
  onUseSample,
  isUploading,
  fileName,
  error,
}: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  function handleInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.item(0);
    if (file) {
      onFile(file);
    }
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files.item(0);
    if (file) {
      onFile(file);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      inputRef.current?.click();
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cargar cartera</CardTitle>
        <CardDescription>
          Suba un archivo CSV con hasta 16 columnas de entrada por crédito. La
          API valida el archivo y procesa la cartera en segundo plano.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div
          role="button"
          tabIndex={0}
          aria-label="Seleccionar archivo CSV"
          onClick={() => inputRef.current?.click()}
          onKeyDown={handleKeyDown}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border border-dashed px-5 py-10 text-center transition-colors",
            isDragging
              ? "border-slate-900 bg-slate-50"
              : "border-border bg-muted/20 hover:bg-muted/40",
            isUploading && "pointer-events-none opacity-70",
          )}
        >
          {isUploading ? (
            <Loader2 className="size-9 animate-spin text-slate-700" />
          ) : (
            <UploadCloud className="size-9 text-slate-700" />
          )}
          <div>
            <p className="text-sm font-medium">
              {isUploading
                ? "Subiendo archivo…"
                : "Arrastre el CSV aquí o haga clic para seleccionarlo"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Formato CSV · una fila por crédito · codificación UTF-8
            </p>
          </div>
          {fileName ? (
            <p className="flex items-center gap-1.5 rounded-md bg-background px-2.5 py-1 text-xs text-muted-foreground ring-1 ring-border">
              <FileSpreadsheet className="size-3.5" />
              {fileName}
            </p>
          ) : null}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={handleInputChange}
        />

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">
            También puede probar con la cartera de ejemplo incluida.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => inputRef.current?.click()}
              disabled={isUploading}
            >
              <FileSpreadsheet />
              Seleccionar CSV
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={onUseSample}
              disabled={isUploading}
            >
              <Sparkles />
              Usar cartera de ejemplo
            </Button>
          </div>
        </div>

        {error ? (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}
