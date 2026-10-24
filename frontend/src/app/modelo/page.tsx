import { PageHeader } from "@/components/layout/page-header";
import { ModelOverview } from "@/components/model/model-overview";

export default function ModeloPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:py-8">
      <PageHeader
        title="Modelo"
        description="Ficha metodológica, métricas de validación, supuestos y límites del modelo de pérdida crediticia esperada."
      />
      <ModelOverview />
    </div>
  );
}
