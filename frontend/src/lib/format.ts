const currency0 = new Intl.NumberFormat("es-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const currency2 = new Intl.NumberFormat("es-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactCurrency = new Intl.NumberFormat("es-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

const number0 = new Intl.NumberFormat("es-CO", {
  maximumFractionDigits: 0,
});

const number2 = new Intl.NumberFormat("es-CO", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const number4 = new Intl.NumberFormat("es-CO", {
  minimumFractionDigits: 4,
  maximumFractionDigits: 4,
});

const percent2 = new Intl.NumberFormat("es-CO", {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const dateTime = new Intl.DateTimeFormat("es-CO", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatCurrency(value: number, decimals: 0 | 2 = 0): string {
  return decimals === 2 ? currency2.format(value) : currency0.format(value);
}

export function formatCompactCurrency(value: number): string {
  return compactCurrency.format(value);
}

export function formatNumber(value: number, decimals: 0 | 2 | 4 = 0): string {
  if (decimals === 4) {
    return number4.format(value);
  }

  return decimals === 2 ? number2.format(value) : number0.format(value);
}

export function formatPercent(value: number, decimals: 2 | 1 = 2): string {
  if (!Number.isFinite(value)) {
    return "—";
  }

  if (decimals === 1) {
    return new Intl.NumberFormat("es-CO", {
      style: "percent",
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }).format(value);
  }

  return percent2.format(value);
}

export function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return dateTime.format(date);
}

export function orDash(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  return String(value);
}
