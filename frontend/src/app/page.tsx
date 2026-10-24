import { PageHeader } from "@/components/layout/page-header";
import { PortfolioDashboard } from "@/components/portfolio/portfolio-dashboard";

export default function HomePage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:py-8">
      <PageHeader
        title="Análisis de cartera"
        description="Cargue una cartera de crédito para estimar la probabilidad de default, la pérdida esperada y el detalle por crédito."
      />
      <PortfolioDashboard />
    </div>
  );
}
