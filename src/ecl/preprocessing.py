"""Preprocesamiento y codificación Weight of Evidence (WoE) para el modelo ECL."""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence

import numpy as np
import pandas as pd

COLUMNAS_ENTRADA: tuple[str, ...] = (
    "funded_amnt",
    "interest_rate",
    "loan_term_months",
    "monthly_payment",
    "annual_income",
    "dept_paym_income_ratio",
    "issue_date_year",
    "earliest_cr_line_year",
    "num_rev_trades_op_in_24mths",
    "num_inq_in_6mths",
    "num_inq",
    "num_derogatory_pub_rec",
    "mths_since_last_installment_acc_op",
    "bal_to_cred_lim",
    "max_bal_owed",
    "used_credit_share",
)

COLUMNAS_NULABLES: tuple[str, ...] = (
    "mths_since_last_installment_acc_op",
    "num_rev_trades_op_in_24mths",
    "num_inq",
    "max_bal_owed",
    "bal_to_cred_lim",
)

COLUMNAS_NO_NULABLES: tuple[str, ...] = tuple(
    columna for columna in COLUMNAS_ENTRADA if columna not in COLUMNAS_NULABLES
)


class WOEEncoderV2:
    """Calcula y aplica mapas WoE aprendidos únicamente con el conjunto de train."""

    def __init__(self) -> None:
        self.mapas: dict[str, dict[Hashable, float]] = {}
        self.bins_def: dict[str, Sequence[float] | pd.IntervalIndex | None] = {}
        self.categoricas: list[str] = []
        self.iv_final: dict[str, float] = {}

    def fit(
        self,
        df: pd.DataFrame,
        target: str,
        variables_bins: Mapping[str, Sequence[float] | None],
        categoricas: Sequence[str] | None = None,
    ) -> "WOEEncoderV2":
        """Aprende el WoE de cada bin o categoría usando el target indicado."""
        if target not in df.columns:
            raise ValueError(f"La columna objetivo '{target}' no existe en el DataFrame.")

        self.categoricas = list(categoricas or [])

        for col, bins in variables_bins.items():
            if col not in df.columns:
                raise ValueError(f"La columna '{col}' no existe en el DataFrame.")

            df_temp = df[[col, target]].copy()

            if col in self.categoricas:
                df_temp["bin"] = df_temp[col]
            elif bins is not None:
                df_temp["bin"] = pd.cut(df_temp[col], bins=bins, duplicates="drop")
            else:
                df_temp["bin"] = pd.qcut(df_temp[col], q=10, duplicates="drop")

            grupo = df_temp.groupby("bin", observed=True)[target].agg(["count", "sum"])
            grupo.columns = ["total", "malos"]
            grupo["buenos"] = grupo["total"] - grupo["malos"]

            total_malos = grupo["malos"].sum()
            total_buenos = grupo["buenos"].sum()

            grupo["pct_malos"] = (grupo["malos"] + 0.5) / (total_malos + 0.5)
            grupo["pct_buenos"] = (grupo["buenos"] + 0.5) / (total_buenos + 0.5)
            grupo["woe"] = np.log(grupo["pct_buenos"] / grupo["pct_malos"])
            grupo["iv"] = (grupo["pct_buenos"] - grupo["pct_malos"]) * grupo["woe"]

            self.mapas[col] = {
                clave: float(valor) for clave, valor in grupo["woe"].to_dict().items()
            }

            if col in self.categoricas:
                self.bins_def[col] = None
            elif bins is not None:
                self.bins_def[col] = list(bins)
            else:
                self.bins_def[col] = pd.IntervalIndex(df_temp["bin"].cat.categories)

            self.iv_final[col] = float(grupo["iv"].sum())

        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Reemplaza cada variable por su WoE y conserva el resto de columnas."""
        df_out = df.copy()

        for col, mapa in self.mapas.items():
            if col not in df_out.columns:
                raise ValueError(f"La columna '{col}' no existe en el DataFrame.")

            if col in self.categoricas:
                codificado = df_out[col].map(mapa)
            else:
                bins = self.bins_def[col]
                if bins is None:
                    raise RuntimeError(f"No hay bins definidos para la variable '{col}'.")
                binned = pd.cut(df_out[col], bins=bins)
                codificado = binned.astype(object).map(mapa)

            df_out[f"{col}_woe"] = (
                pd.to_numeric(codificado, errors="coerce")
                .astype("float64")
                .fillna(0.0)
            )

        return df_out


class PreprocesadorECL:
    """Reproduce las transformaciones fijas y aprendidas del notebook ECL."""

    def __init__(self, tope_ingresos: float = 1_000_000.0) -> None:
        self.tope_ingresos = float(tope_ingresos)
        self.parametros: dict[str, float] = {}
        self.woe_encoder = WOEEncoderV2()
        self.categoricas: list[str] = ["loan_term_months"]
        self.variables_bins: dict[str, Sequence[float] | None] = {
            "num_rev_trades_op_in_24mths": [-0.1, 0, 1, 2, 5, np.inf],
            "num_inq_in_6mths": [-0.1, 0, 1, 2, 5, np.inf],
            "num_inq": [-0.1, 0, 1, 2, 5, np.inf],
            "num_derogatory_pub_rec": [-0.1, 0, np.inf],
            "mths_since_last_installment_acc_op": [-0.1, 12, 24, 48, 998, np.inf],
            "interest_rate": None,
            "bal_to_cred_lim": None,
            "max_bal_owed": None,
            "dept_paym_income_ratio": None,
            "used_credit_share": None,
            "annual_income": None,
            "monthly_payment": None,
            "loan_term_months": None,
            "credit_history_length": None,
        }

    def validar_entrada(self, df: pd.DataFrame) -> None:
        """Valida columnas requeridas y valores faltantes en columnas no nulables."""
        columnas_faltantes = [
            columna for columna in COLUMNAS_ENTRADA if columna not in df.columns
        ]
        if columnas_faltantes:
            faltantes = ", ".join(columnas_faltantes)
            raise ValueError(f"Faltan columnas requeridas: {faltantes}.")

        for columna in COLUMNAS_NO_NULABLES:
            cantidad_nulos = int(df[columna].isna().sum())
            if cantidad_nulos > 0:
                raise ValueError(
                    f"La columna '{columna}' no admite valores faltantes; "
                    f"se encontraron {cantidad_nulos} valores nulos."
                )

    def _features_fijas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica las transformaciones Tipo A, idénticas para train e inferencia."""
        df_out = df.copy()
        df_out["credit_history_length"] = (
            df_out["issue_date_year"] - df_out["earliest_cr_line_year"]
        ).clip(lower=0)
        df_out["mths_since_last_installment_acc_op"] = df_out[
            "mths_since_last_installment_acc_op"
        ].fillna(999)
        for columna in ("num_rev_trades_op_in_24mths", "num_inq"):
            df_out[columna] = df_out[columna].fillna(0)
        df_out["annual_income"] = df_out["annual_income"].clip(
            upper=self.tope_ingresos
        )
        return df_out

    def fit(self, train_df: pd.DataFrame, target: str = "y") -> "PreprocesadorECL":
        """Aprende imputaciones y mapas WoE usando solo el conjunto de train."""
        self.validar_entrada(train_df)
        if target not in train_df.columns:
            raise ValueError(f"La columna objetivo '{target}' no existe en el DataFrame.")

        train = self._features_fijas(train_df)

        self.parametros["mediana_max_bal_owed"] = float(train["max_bal_owed"].median())
        self.parametros["media_bal_to_cred_lim"] = float(train["bal_to_cred_lim"].mean())

        train["max_bal_owed"] = train["max_bal_owed"].fillna(
            self.parametros["mediana_max_bal_owed"]
        )
        train["bal_to_cred_lim"] = train["bal_to_cred_lim"].fillna(
            self.parametros["media_bal_to_cred_lim"]
        )

        self.woe_encoder.fit(
            train,
            target,
            self.variables_bins,
            categoricas=self.categoricas,
        )
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aplica las transformaciones fijas y los parámetros aprendidos en train."""
        if not self.parametros:
            raise RuntimeError("El preprocesador no está ajustado. Ejecute fit primero.")

        self.validar_entrada(df)
        df_out = self._features_fijas(df)
        df_out["max_bal_owed"] = df_out["max_bal_owed"].fillna(
            self.parametros["mediana_max_bal_owed"]
        )
        df_out["bal_to_cred_lim"] = df_out["bal_to_cred_lim"].fillna(
            self.parametros["media_bal_to_cred_lim"]
        )
        return self.woe_encoder.transform(df_out)

    def get_features_finales(self) -> list[str]:
        """Devuelve los nombres de las columnas WoE usadas por el modelo PD."""
        return [f"{columna}_woe" for columna in self.variables_bins]
