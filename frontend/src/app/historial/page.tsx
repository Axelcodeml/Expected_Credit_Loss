import { HistoryList } from "@/components/history/history-list";
import { PageHeader } from "@/components/layout/page-header";

export default function HistorialPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:py-8">
      <PageHeader
        title="Historial"
        description="Corridas de cartera guardadas por la API local. Desde aquí puede descargar el detalle de cada procesamiento."
      />
      <HistoryList />
    </div>
  );
}
