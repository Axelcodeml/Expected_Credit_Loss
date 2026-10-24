import type { LoanInput } from "@/lib/api";

export type LoanFieldKey = Exclude<keyof LoanInput, "id">;

export interface LoanFieldDefinition {
  key: LoanFieldKey;
  label: string;
  hint?: string;
  group: "Crédito" | "Ingresos y capacidad" | "Historial" | "Comportamiento";
  required: boolean;
  type: "number" | "select";
  step?: string;
  min?: number;
  max?: number;
  options?: { value: string; label: string }[];
  placeholder?: string;
}

export const LOAN_FIELDS: LoanFieldDefinition[] = [
  {
    key: "funded_amnt",
    label: "Monto financiado (USD)",
    group: "Crédito",
    required: true,
    type: "number",
    min: 1,
    step: "0.01",
  },
  {
    key: "interest_rate",
    label: "Tasa de interés (%)",
    group: "Crédito",
    required: true,
    type: "number",
    min: 0,
    step: "0.01",
  },
  {
    key: "loan_term_months",
    label: "Plazo (meses)",
    group: "Crédito",
    required: true,
    type: "select",
    options: [
      { value: "36", label: "36 meses" },
      { value: "60", label: "60 meses" },
    ],
  },
  {
    key: "monthly_payment",
    label: "Cuota mensual (USD)",
    group: "Crédito",
    required: true,
    type: "number",
    min: 0,
    step: "0.01",
  },
  {
    key: "annual_income",
    label: "Ingreso anual (USD)",
    group: "Ingresos y capacidad",
    required: true,
    type: "number",
    min: 1,
    step: "0.01",
  },
  {
    key: "dept_paym_income_ratio",
    label: "DTI (%)",
    hint: "Relación deuda / ingreso reportada.",
    group: "Ingresos y capacidad",
    required: true,
    type: "number",
    min: 0,
    step: "0.01",
  },
  {
    key: "issue_date_year",
    label: "Año de originación",
    group: "Historial",
    required: true,
    type: "number",
    min: 1900,
    max: 2100,
    step: "1",
  },
  {
    key: "earliest_cr_line_year",
    label: "Año de la primera línea de crédito",
    group: "Historial",
    required: true,
    type: "number",
    min: 1900,
    max: 2100,
    step: "1",
  },
  {
    key: "num_rev_trades_op_in_24mths",
    label: "Cuentas revolventes abiertas (24 m)",
    group: "Comportamiento",
    required: false,
    type: "number",
    min: 0,
    step: "1",
  },
  {
    key: "num_inq_in_6mths",
    label: "Consultas de crédito (6 m)",
    group: "Comportamiento",
    required: true,
    type: "number",
    min: 0,
    step: "1",
  },
  {
    key: "num_inq",
    label: "Consultas de crédito (total)",
    group: "Comportamiento",
    required: false,
    type: "number",
    min: 0,
    step: "1",
  },
  {
    key: "num_derogatory_pub_rec",
    label: "Registros públicos derogatorios",
    group: "Comportamiento",
    required: true,
    type: "number",
    min: 0,
    step: "1",
  },
  {
    key: "mths_since_last_installment_acc_op",
    label: "Meses desde la última cuota (cuenta abierta)",
    group: "Comportamiento",
    required: false,
    type: "number",
    min: 0,
    step: "1",
  },
  {
    key: "bal_to_cred_lim",
    label: "Saldo / límite de crédito (%)",
    group: "Comportamiento",
    required: false,
    type: "number",
    min: 0,
    step: "0.01",
  },
  {
    key: "max_bal_owed",
    label: "Saldo máximo adeudado (USD)",
    group: "Comportamiento",
    required: false,
    type: "number",
    min: 0,
    step: "0.01",
  },
  {
    key: "used_credit_share",
    label: "Uso de crédito (%)",
    group: "Comportamiento",
    required: true,
    type: "number",
    min: 0,
    step: "0.01",
  },
];

export const LOAN_GROUPS: LoanFieldDefinition["group"][] = [
  "Crédito",
  "Ingresos y capacidad",
  "Historial",
  "Comportamiento",
];

export const LOAN_DEFAULT_VALUES: Record<LoanFieldKey, string> = {
  funded_amnt: "12000",
  interest_rate: "13.5",
  loan_term_months: "36",
  monthly_payment: "406.55",
  annual_income: "65000",
  dept_paym_income_ratio: "18.5",
  issue_date_year: "2016",
  earliest_cr_line_year: "2008",
  num_rev_trades_op_in_24mths: "4",
  num_inq_in_6mths: "1",
  num_inq: "2",
  num_derogatory_pub_rec: "0",
  mths_since_last_installment_acc_op: "18",
  bal_to_cred_lim: "42",
  max_bal_owed: "14500",
  used_credit_share: "38",
};

export function validarFormulario(
  values: Record<LoanFieldKey, string>,
): string[] {
  const errors: string[] = [];

  for (const field of LOAN_FIELDS) {
    const raw = values[field.key].trim();

    if (field.required && raw === "") {
      errors.push(`${field.label} es obligatorio.`);
      continue;
    }

    if (raw === "") {
      continue;
    }

    const value = Number(raw);

    if (!Number.isFinite(value)) {
      errors.push(`${field.label} debe ser un número válido.`);
      continue;
    }

    if (field.min !== undefined && value < field.min) {
      errors.push(`${field.label} debe ser mayor o igual a ${field.min}.`);
    }

    if (field.max !== undefined && value > field.max) {
      errors.push(`${field.label} debe ser menor o igual a ${field.max}.`);
    }
  }

  return errors;
}

function numberFromInput(value: string): number {
  return Number(value.trim());
}

function optionalNumberFromInput(value: string): number | null {
  return value.trim() === "" ? null : Number(value.trim());
}

export function loanInputFromForm(
  values: Record<LoanFieldKey, string>,
  id: string,
): LoanInput {
  return {
    id: id.trim() === "" ? null : id.trim(),
    funded_amnt: numberFromInput(values.funded_amnt),
    interest_rate: numberFromInput(values.interest_rate),
    loan_term_months: values.loan_term_months === "60" ? 60 : 36,
    monthly_payment: numberFromInput(values.monthly_payment),
    annual_income: numberFromInput(values.annual_income),
    dept_paym_income_ratio: numberFromInput(values.dept_paym_income_ratio),
    issue_date_year: numberFromInput(values.issue_date_year),
    earliest_cr_line_year: numberFromInput(values.earliest_cr_line_year),
    num_rev_trades_op_in_24mths: optionalNumberFromInput(
      values.num_rev_trades_op_in_24mths,
    ),
    num_inq_in_6mths: numberFromInput(values.num_inq_in_6mths),
    num_inq: optionalNumberFromInput(values.num_inq),
    num_derogatory_pub_rec: numberFromInput(values.num_derogatory_pub_rec),
    mths_since_last_installment_acc_op: optionalNumberFromInput(
      values.mths_since_last_installment_acc_op,
    ),
    bal_to_cred_lim: optionalNumberFromInput(values.bal_to_cred_lim),
    max_bal_owed: optionalNumberFromInput(values.max_bal_owed),
    used_credit_share: numberFromInput(values.used_credit_share),
  };
}
