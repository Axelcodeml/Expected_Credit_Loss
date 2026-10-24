"use client";

import { useMutation } from "@tanstack/react-query";
import { AlertCircle, Calculator, Loader2, RotateCcw } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";

import type { LoanInput, LoanPrediction } from "@/lib/api";
import { mensajeError, predict } from "@/lib/api";
import {
  LOAN_DEFAULT_VALUES,
  LOAN_FIELDS,
  LOAN_GROUPS,
  loanInputFromForm,
  validarFormulario,
} from "@/lib/loan-fields";
import type { LoanFieldKey } from "@/lib/loan-fields";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/format";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

const SELECT_CLASS =
  "h-8 w-full rounded-md border border-input bg-background px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50";

export function CreditSimulator() {
  const [values, setValues] = useState<Record<LoanFieldKey, string>>({
    ...LOAN_DEFAULT_VALUES,
  });
  const [id, setId] = useState("");
  const [errors, setErrors] = useState<string[]>([]);

  const mutation = useMutation({
    mutationFn: (credito: LoanInput) => predict([credito]),
  });

  const prediccion = mutation.data?.creditos[0] ?? null;

  function setField(key: LoanFieldKey, value: string) {
    setValues((current) => ({ ...current, [key]: value }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = validarFormulario(values);

    if (validation.length > 0) {
      setErrors(validation);
      return;
    }

    setErrors([]);
    mutation.mutate(loanInputFromForm(values, id));
  }

  function resetForm() {
    setValues({ ...LOAN_DEFAULT_VALUES });
    setId("");
    setErrors([]);
    mutation.reset();
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
      <form onSubmit={handleSubmit} className="space-y-4">
        {errors.length > 0 ? (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertTitle>Revise los datos del crédito</AlertTitle>
            <AlertDescription>
              <ul className="list-disc pl-4">
                {errors.map((error) => (
                  <li key={error}>{error}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>Identificación</CardTitle>
            <CardDescription>
              El ID es opcional. Si no lo informa, la API genera un identificador
              interno para la respuesta.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="max-w-sm space-y-1.5">
              <label htmlFor="credito-id" className="text-sm font-medium">
                ID del crédito
              </label>
              <Input
                id="credito-id"
                value={id}
                onChange={(event) => setId(event.target.value)}
                placeholder="Ej. CR-0001"
              />
            </div>
          </CardContent>
        </Card>

        {LOAN_GROUPS.map((group) => {
          const fields = LOAN_FIELDS.filter((field) => field.group === group);

          return (
            <Card key={group}>
              <CardHeader>
                <CardTitle>{group}</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 sm:grid-cols-2">
                {fields.map((field) => (
                  <div key={field.key} className="space-y-1.5">
                    <label
                      htmlFor={field.key}
                      className="flex items-center gap-1 text-sm font-medium"
                    >
                      {field.label}
                      {!field.required ? (
                        <span className="text-xs font-normal text-muted-foreground">
                          (opcional)
                        </span>
                      ) : null}
                    </label>

                    {field.type === "select" ? (
                      <select
                        id={field.key}
                        value={values[field.key]}
                        onChange={(event) => setField(field.key, event.target.value)}
                        className={SELECT_CLASS}
                        required={field.required}
                      >
                        {field.options?.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Input
                        id={field.key}
                        type="number"
                        inputMode="decimal"
                        value={values[field.key]}
                        onChange={(event) => setField(field.key, event.target.value)}
                        min={field.min}
                        max={field.max}
                        step={field.step}
                        required={field.required}
                      />
                    )}

                    {field.hint ? (
                      <p className="text-xs text-muted-foreground">{field.hint}</p>
                    ) : null}
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })}

        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Calculator />
            )}
            Estimar crédito
          </Button>
          <Button type="button" variant="outline" onClick={resetForm}>
            <RotateCcw />
            Restablecer
          </Button>
        </div>
      </form>

      <div className="space-y-4 lg:sticky lg:top-24 lg:self-start">
        {mutation.isPending ? (
          <Card>
            <CardContent className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Calculando estimación…
            </CardContent>
          </Card>
        ) : mutation.isError ? (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertTitle>No fue posible estimar el crédito</AlertTitle>
            <AlertDescription>{mensajeError(mutation.error)}</AlertDescription>
          </Alert>
        ) : prediccion ? (
          <CreditResult prediccion={prediccion} />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Resultado</CardTitle>
              <CardDescription>
                Complete el formulario y ejecute la estimación para ver PD, LGD,
                EAD, ECL y los principales factores de riesgo.
              </CardDescription>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              La respuesta incluye la probabilidad de default, la pérdida esperada
              calibrada y la pérdida esperada con margen de prudencia.
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function CreditResult({ prediccion }: { prediccion: LoanPrediction }) {
  const advertencias = prediccion.advertencias ?? [];
  const topContribuciones = [...(prediccion.contribuciones ?? [])]
    .sort((a, b) => a.contribucion - b.contribucion)
    .slice(0, 3);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Resultado del crédito</CardTitle>
          <Badge
            variant={prediccion.marcado ? "destructive" : "secondary"}
            className={cn(
              !prediccion.marcado && "border-emerald-200 bg-emerald-50 text-emerald-700",
            )}
          >
            {prediccion.marcado ? "Marcado" : "No marcado"}
          </Badge>
        </div>
        <CardDescription>
          ID: <span className="font-mono">{String(prediccion.id ?? "—")}</span>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-2 gap-3">
          <Dato label="PD" value={formatPercent(prediccion.pd)} />
          <Dato label="LGD" value={formatPercent(prediccion.lgd)} />
          <Dato label="EAD" value={formatCurrency(prediccion.ead)} />
          <Dato label="Banda de riesgo" value={`B${prediccion.banda_riesgo} / 10`} />
          <Dato
            label="ECL calibrado"
            value={formatCurrency(prediccion.ecl_calibrado)}
            tooltip="Pérdida esperada calibrada: PD × LGD × EAD, sin el margen de prudencia del modelo."
          />
          <Dato
            label="ECL con margen"
            value={formatCurrency(prediccion.ecl_final)}
            tooltip="Pérdida esperada final: ECL calibrado multiplicado por el factor de cobertura definido en el modelo."
          />
        </div>

        {advertencias.length > 0 ? (
          <Alert>
            <AlertCircle />
            <AlertTitle>Advertencias</AlertTitle>
            <AlertDescription>
              <ul className="list-disc pl-4">
                {advertencias.map((advertencia) => (
                  <li key={advertencia}>{advertencia}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        ) : null}

        <section>
          <h3 className="mb-2 text-sm font-medium">
            Principales factores de riesgo
          </h3>
          {topContribuciones.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No hay contribuciones disponibles para este crédito.
            </p>
          ) : (
            <div className="space-y-2">
              {topContribuciones.map((contribucion) => (
                <div
                  key={`${contribucion.variable}-${contribucion.contribucion}`}
                  className="rounded-lg border bg-muted/20 p-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium">{contribucion.variable}</p>
                    <span className="text-xs font-medium tabular-nums text-muted-foreground">
                      {formatNumber(contribucion.contribucion, 2)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    WoE {formatNumber(contribucion.valor_woe, 2)} · coeficiente{" "}
                    {formatNumber(contribucion.coeficiente, 2)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </CardContent>
    </Card>
  );
}

function Dato({
  label,
  value,
  tooltip,
}: {
  label: string;
  value: string;
  tooltip?: string;
}) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        {label}
        {tooltip ? (
          <Tooltip>
            <TooltipTrigger
              type="button"
              className="inline-flex size-4 items-center justify-center rounded-full hover:text-foreground"
              aria-label={`Más información sobre ${label}`}
            >
              i
            </TooltipTrigger>
            <TooltipContent>{tooltip}</TooltipContent>
          </Tooltip>
        ) : null}
      </div>
      <p className="mt-1 text-base font-semibold tabular-nums">{value}</p>
    </div>
  );
}
