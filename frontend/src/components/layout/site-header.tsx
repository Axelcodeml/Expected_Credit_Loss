"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Cartera" },
  { href: "/credito", label: "Crédito individual" },
  { href: "/modelo", label: "Modelo" },
  { href: "/historial", label: "Historial" },
] as const;

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <Link href="/" className="flex items-center gap-3">
          <span className="flex size-9 items-center justify-center rounded-lg bg-slate-900 text-xs font-bold tracking-tight text-white">
            ECL
          </span>
          <span>
            <span className="block text-sm font-semibold leading-tight">
              Pérdida crediticia esperada
            </span>
            <span className="block text-xs text-muted-foreground">
              Analítica para carteras de crédito
            </span>
          </span>
        </Link>

        <nav
          aria-label="Navegación principal"
          className="-mx-1 flex items-center gap-1 overflow-x-auto px-1"
        >
          {NAV_ITEMS.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                  active && "bg-slate-900 text-white hover:bg-slate-900 hover:text-white",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
