import { ShieldAlert } from "lucide-react";

export function FixedNotice() {
  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-amber-950">
      <div className="mx-auto flex max-w-7xl items-start justify-center gap-2 text-center text-xs font-medium sm:items-center">
        <ShieldAlert className="mt-0.5 size-3.5 shrink-0 sm:mt-0" />
        <p>
          Estimación a nivel de cartera. No es un detector de fraude ni debe
          usarse para aprobar o rechazar créditos individuales.
        </p>
      </div>
    </div>
  );
}
