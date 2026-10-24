from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ecl.model import ModeloECL
from src.ecl.preprocessing import COLUMNAS_ENTRADA


def _construir_cartera(seed: int = 42, n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    funded = rng.uniform(1_000, 20_000, n)
    interest = rng.uniform(5, 30, n)
    term = rng.choice([36.0, 60.0], n)
    monthly = funded / term * (1 + interest / 100)
    annual_income = rng.uniform(20_000, 200_000, n)
    dept = rng.uniform(0, 50, n)
    issue_year = rng.integers(2007, 2019, n).astype(float)
    earliest_year = issue_year - rng.integers(0, 30, n)
    num_rev = rng.integers(0, 10, n).astype(float)
    num_inq_6m = rng.integers(0, 10, n).astype(float)
    num_inq = rng.integers(0, 10, n).astype(float)
    num_derog = rng.integers(0, 3, n).astype(float)
    mths_last = rng.integers(0, 999, n).astype(float)
    bal_to = rng.uniform(0, 150, n)
    max_bal = rng.uniform(0, 50_000, n)
    used = rng.uniform(0, 100, n)

    mascara_nulos = rng.random(n) < 0.10
    mths_last[mascara_nulos] = np.nan
    num_rev[mascara_nulos] = np.nan
    num_inq[mascara_nulos] = np.nan
    bal_to[mascara_nulos] = np.nan
    max_bal[mascara_nulos] = np.nan

    y = np.zeros(n, dtype=int)
    y[:40] = 1
    y = y[rng.permutation(n)]

    princ_rec = np.where(y == 1, funded * rng.uniform(0, 0.95, n), funded)
    interest_rec = rng.uniform(0, 5_000, n)
    late_fees_rec = rng.uniform(0, 500, n)
    extra = np.where(y == 1, rng.uniform(0, 1_000, n), 0.0)
    paym_rec = princ_rec + interest_rec + late_fees_rec + extra

    df = pd.DataFrame(
        {
            "funded_amnt": funded,
            "interest_rate": interest,
            "loan_term_months": term,
            "monthly_payment": monthly,
            "annual_income": annual_income,
            "dept_paym_income_ratio": dept,
            "issue_date_year": issue_year,
            "earliest_cr_line_year": earliest_year,
            "num_rev_trades_op_in_24mths": num_rev,
            "num_inq_in_6mths": num_inq_6m,
            "num_inq": num_inq,
            "num_derogatory_pub_rec": num_derog,
            "mths_since_last_installment_acc_op": mths_last,
            "bal_to_cred_lim": bal_to,
            "max_bal_owed": max_bal,
            "used_credit_share": used,
            "y": y,
            "princ_rec": princ_rec,
            "interest_rec": interest_rec,
            "late_fees_rec": late_fees_rec,
            "paym_rec_for_tot_amnt_fund": paym_rec,
        }
    )
    return df.loc[:, list(COLUMNAS_ENTRADA) + [
        "y",
        "princ_rec",
        "interest_rec",
        "late_fees_rec",
        "paym_rec_for_tot_amnt_fund",
    ]]


@pytest.fixture(scope="session")
def cartera_sintetica() -> pd.DataFrame:
    return _construir_cartera()


@pytest.fixture(scope="session")
def modelo_entrenado(cartera_sintetica: pd.DataFrame) -> ModeloECL:
    return ModeloECL(obj_viol=1.0, obj_r1=0.0).fit(cartera_sintetica)
