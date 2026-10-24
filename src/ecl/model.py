"""Modelo de pérdida crediticia esperada: ECL = PD x LGD x EAD."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression

from src.ecl.config import CRITERIO, MODEL_VERSION, OBJ_R1, OBJ_VIOL, Q_GRID, S_GRID
from src.ecl.preprocessing import PreprocesadorECL

FEATS_EAD_LGD: list[str] = [
    "funded_amnt",
    "interest_rate",
    "loan_term_months",
    "monthly_payment",
    "annual_income",
    "dept_paym_income_ratio",
    "issue_date_year",
]


def construir_reales(df: pd.DataFrame) -> pd.DataFrame:
    """Construye la clave de respuestas con la definición A.

    Usa variables de desempeño y la etiqueta ``y``. Solo debe emplearse para
    entrenar y evaluar; nunca como entrada de inferencia.
    """
    out = pd.DataFrame(index=df.index)
    out["y"] = df["y"]

    out["ead_real"] = (df["funded_amnt"] - df["princ_rec"]).clip(lower=0)

    cobrado_base = df["princ_rec"] + df["interest_rec"] + df["late_fees_rec"]
    out["recuperado"] = (
        df["paym_rec_for_tot_amnt_fund"] - cobrado_base
    ).clip(lower=0)

    es_def = (out["y"] == 1) & (out["ead_real"] > 0)
    lgd = 1 - out["recuperado"] / out["ead_real"].where(out["ead_real"] > 0)
    out["lgd_real"] = lgd.where(es_def).clip(0, 1)

    out["ecl_real_A"] = (out["ead_real"] * out["lgd_real"]).where(es_def, 0.0)
    out["ecl_real_B"] = (
        (df["funded_amnt"] - df["paym_rec_for_tot_amnt_fund"])
        .clip(lower=0)
        .where(out["y"] == 1, 0.0)
    )
    return out


def calcular_ecl_calibrado(
    pd_hat: Sequence[float] | np.ndarray,
    lgd_hat: Sequence[float] | np.ndarray,
    ead_hat: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Calcula la ECL calibrada por crédito: PD x LGD x EAD."""
    return (
        np.asarray(pd_hat, dtype=float)
        * np.asarray(lgd_hat, dtype=float)
        * np.asarray(ead_hat, dtype=float)
    )


def calcular_puntaje(
    pd_hat: Sequence[float] | np.ndarray,
    funded_amnt: Sequence[float] | np.ndarray,
    criterio: str,
) -> np.ndarray:
    """Calcula el puntaje usado para seleccionar los créditos marcados."""
    pd_array = np.asarray(pd_hat, dtype=float)
    funded_array = np.asarray(funded_amnt, dtype=float)

    if criterio == "pd":
        return pd_array
    if criterio == "pd_por_monto":
        return pd_array / funded_array
    raise ValueError(f"Criterio no soportado: '{criterio}'.")


def aplicar_margen(
    ecl_calibrado: Sequence[float] | np.ndarray,
    pd_hat: Sequence[float] | np.ndarray,
    funded_amnt: Sequence[float] | np.ndarray,
    s: float,
    corte: float,
    criterio: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Aplica el margen de conservadurismo a los créditos marcados."""
    cal = np.asarray(ecl_calibrado, dtype=float)
    funded = np.asarray(funded_amnt, dtype=float)
    puntaje = calcular_puntaje(pd_hat, funded, criterio)
    marcado = puntaje >= corte
    ecl_final = np.where(marcado, np.maximum(cal, s * funded), cal)
    return ecl_final, marcado


def asignar_bandas(
    pd_hat: Sequence[float] | np.ndarray,
    cortes: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Asigna bandas de riesgo de 1 (menor PD) a 10 (mayor PD)."""
    pd_array = np.asarray(pd_hat, dtype=float)
    cortes_array = np.asarray(cortes, dtype=float)
    if cortes_array.size == 0:
        return np.ones(len(pd_array), dtype=int)
    bandas = np.digitize(pd_array, cortes_array, right=False) + 1
    return np.clip(bandas, 1, 10).astype(int)


class ModeloECL:
    """Pipeline completo: preprocesamiento, PD, EAD, LGD y margen de conservadurismo."""

    prep: PreprocesadorECL
    cols_pd: list[str]
    modelo_pd: LogisticRegression
    m_ead: LinearRegression
    m_lgd: LinearRegression

    def __init__(
        self,
        obj_viol: float = OBJ_VIOL,
        obj_r1: float = OBJ_R1,
        criterio: str = CRITERIO,
    ) -> None:
        self.obj_viol = float(obj_viol)
        self.obj_r1 = float(obj_r1)
        self.criterio = criterio
        self.version = MODEL_VERSION
        self.seed: int | None = None
        self.margen: dict[str, float] = {}
        self.cortes_bandas: np.ndarray = np.array([], dtype=float)

    def _componentes(self, df: pd.DataFrame) -> dict[str, np.ndarray]:
        pd_hat = self.modelo_pd.predict_proba(df[self.cols_pd])[:, 1]
        x_ead_lgd = df[FEATS_EAD_LGD]
        ead = np.clip(self.m_ead.predict(x_ead_lgd), 0.0, 1.0) * df[
            "funded_amnt"
        ].to_numpy(dtype=float)
        lgd = np.clip(self.m_lgd.predict(x_ead_lgd), 0.0, 1.0)
        return {
            "pd": pd_hat,
            "ead": ead,
            "lgd": lgd,
            "cal": calcular_ecl_calibrado(pd_hat, lgd, ead),
        }

    def _puntaje(
        self,
        pd_hat: Sequence[float] | np.ndarray,
        funded_amnt: Sequence[float] | np.ndarray,
    ) -> np.ndarray:
        return calcular_puntaje(pd_hat, funded_amnt, self.criterio)

    def _aplicar(
        self,
        ecl_calibrado: Sequence[float] | np.ndarray,
        pd_hat: Sequence[float] | np.ndarray,
        funded_amnt: Sequence[float] | np.ndarray,
        s: float,
        corte: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        return aplicar_margen(
            ecl_calibrado,
            pd_hat,
            funded_amnt,
            s,
            corte,
            self.criterio,
        )

    def _buscar_margen(
        self,
        componentes: dict[str, np.ndarray],
        funded_amnt: np.ndarray,
        real: np.ndarray,
    ) -> None:
        puntaje = self._puntaje(componentes["pd"], funded_amnt)
        mejor: dict[str, float] | None = None
        total_real = float(real.sum())

        for q in Q_GRID:
            corte = float(np.quantile(puntaje, 1.0 - q))
            for s in S_GRID:
                ecl, _ = self._aplicar(
                    componentes["cal"],
                    componentes["pd"],
                    funded_amnt,
                    s,
                    corte,
                )
                violaciones = float((ecl < real).mean())
                total = float(ecl.sum())
                if violaciones <= self.obj_viol and total >= self.obj_r1 * total_real:
                    if mejor is None or total < mejor["total"]:
                        mejor = {
                            "q": float(q),
                            "s": float(s),
                            "corte": corte,
                            "total": total,
                            "ratio": total / total_real,
                            "viol": violaciones,
                        }

        if mejor is None:
            raise ValueError(
                "Sin combinación viable: amplía la rejilla de q o relaja obj_viol."
            )
        self.margen = mejor

    def fit(self, train_crudo: pd.DataFrame) -> "ModeloECL":
        """Ajusta PD, EAD, LGD y el margen usando únicamente el train recibido."""
        self.prep = PreprocesadorECL()
        self.prep.fit(train_crudo)
        train = self.prep.transform(train_crudo)
        self.cols_pd = self.prep.get_features_finales()

        self.modelo_pd = LogisticRegression(C=1e10, max_iter=1000).fit(
            train[self.cols_pd],
            train["y"],
        )

        reales = construir_reales(train)
        es_def = (reales["y"] == 1) & reales["lgd_real"].notna()
        x_def = train.loc[es_def, FEATS_EAD_LGD]

        self.m_ead = LinearRegression().fit(
            x_def,
            reales.loc[es_def, "ead_real"] / train.loc[es_def, "funded_amnt"],
        )
        self.m_lgd = LinearRegression().fit(
            x_def,
            reales.loc[es_def, "lgd_real"],
        )

        componentes = self._componentes(train)
        self._buscar_margen(
            componentes,
            train["funded_amnt"].to_numpy(dtype=float),
            reales["ecl_real_A"].to_numpy(dtype=float),
        )
        self.cortes_bandas = np.quantile(
            componentes["pd"],
            np.linspace(0.1, 0.9, 9),
        )
        return self

    def predecir(self, df_crudo: pd.DataFrame) -> pd.DataFrame:
        """Predice los componentes y la ECL por crédito sin usar variables de desempeño."""
        df = self.prep.transform(df_crudo)
        componentes = self._componentes(df)
        ecl_final, marcado = self._aplicar(
            componentes["cal"],
            componentes["pd"],
            df["funded_amnt"].to_numpy(dtype=float),
            self.margen["s"],
            self.margen["corte"],
        )
        bandas = asignar_bandas(componentes["pd"], self.cortes_bandas)

        return pd.DataFrame(
            {
                "pd": componentes["pd"],
                "lgd": componentes["lgd"],
                "ead": componentes["ead"],
                "ecl_calibrado": componentes["cal"],
                "ecl_final": ecl_final,
                "marcado": marcado.astype(bool),
                "banda_riesgo": bandas.astype(int),
            },
            index=df_crudo.index,
        )

    def contribuciones(self, df_crudo: pd.DataFrame) -> pd.DataFrame:
        """Calcula la contribución ``coeficiente x WoE`` de cada variable al logit."""
        df = self.prep.transform(df_crudo)
        valores_woe = df[self.cols_pd].to_numpy(dtype=float)
        coeficientes = self.modelo_pd.coef_[0].astype(float)
        return pd.DataFrame(
            valores_woe * coeficientes,
            index=df_crudo.index,
            columns=self.cols_pd,
        )

    def guardar(self, ruta: str | Path) -> Path:
        """Serializa el modelo completo con joblib."""
        destino = Path(ruta)
        destino.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, destino)
        return destino

    @classmethod
    def cargar(cls, ruta: str | Path) -> "ModeloECL":
        """Carga un modelo serializado y valida su tipo."""
        modelo = joblib.load(Path(ruta))
        if not isinstance(modelo, cls):
            raise TypeError(
                f"El artefacto no contiene un {cls.__name__}: {type(modelo).__name__}."
            )
        return modelo
