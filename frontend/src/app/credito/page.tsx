import { CreditSimulator } from "@/components/credit/credit-simulator";
import { PageHeader } from "@/components/layout/page-header";

export default function CreditoPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:py-8">
      <PageHeader
        title="Crédito individual"
        description="Ingrese las 16 variables del modelo para estimar PD, LGD, EAD y pérdida esperada de un crédito. El resultado es analítico y no constituye una decisión de crédito."
      />
      <CreditSimulator />
    </div>
  );
}
