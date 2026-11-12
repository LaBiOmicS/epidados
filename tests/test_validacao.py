"""Validação do pipeline contra os totais oficiais do TabNet/DATASUS.

Referências: casos confirmados por ano de notificação, consultados no TabNet
(sinannet/cnv/leishvbr.def e leptobr.def) em 2026-11-12. Só anos com base FINAL,
que não mudam mais.
"""

from __future__ import annotations

import json

import duckdb
import pandas as pd
import pytest

from epidados.config import ML_SAIDA, PARQUET, SITE_DADOS

TABNET_LEIV = {
    2007: 3565, 2008: 3991, 2009: 3894, 2010: 3704, 2011: 4107, 2012: 3269, 2013: 3472,
    2014: 3733, 2015: 3558, 2016: 3455, 2017: 4456, 2018: 3851, 2019: 2827, 2020: 2202,
    2021: 1936, 2022: 1983, 2023: 1720, 2024: 1459, 2025: 1612,
}
TABNET_LEPT = {
    2007: 3302, 2008: 3654, 2009: 3996, 2010: 3787, 2011: 5011, 2012: 3222, 2013: 4130,
    2014: 4757, 2015: 4337, 2016: 3065, 2017: 3014, 2018: 3079, 2019: 3704, 2020: 1939,
    2021: 1783, 2022: 3244, 2023: 3408, 2024: 4186,
}


@pytest.fixture(scope="module")
def con():
    return duckdb.connect()


def _confirmados(con, agravo: str) -> dict[int, int]:
    caminho = (PARQUET / "sinan" / agravo / "*.parquet").as_posix()
    return dict(con.execute(f"""
        SELECT ano, count(*) FILTER (WHERE CLASSI_FIN = '1')
        FROM read_parquet('{caminho}', union_by_name = true)
        WHERE situacao = 'final' GROUP BY ano
    """).fetchall())


@pytest.mark.parametrize("agravo,referencia", [("LEIV", TABNET_LEIV), ("LEPT", TABNET_LEPT)])
def test_confirmados_batem_com_tabnet(con, agravo, referencia):
    nossos = _confirmados(con, agravo)
    for ano, esperado in referencia.items():
        if ano in nossos:
            assert nossos[ano] == esperado, f"{agravo} {ano}: {nossos[ano]} ≠ TabNet {esperado}"


@pytest.mark.parametrize("agravo,referencia", [("LEIV", TABNET_LEIV), ("LEPT", TABNET_LEPT)])
def test_poucos_casos_perdidos_no_municipio_de_residencia(agravo, referencia):
    uf = pd.read_csv(SITE_DADOS / "zoonoses_uf_ano.csv")
    por_ano = uf[uf.agravo == agravo].groupby("ano").casos.sum()
    for ano, esperado in referencia.items():
        if ano in por_ano:
            assert esperado - por_ano[ano] >= 0
            assert (esperado - por_ano[ano]) / esperado < 0.01, f"{agravo} {ano}: perda > 1%"


def test_municipio_e_uf_consistentes():
    mun = pd.read_csv(SITE_DADOS / "zoonoses_municipio_ano.csv")
    uf = pd.read_csv(SITE_DADOS / "zoonoses_uf_ano.csv")
    assert mun.groupby(["agravo", "ano"]).casos.sum().equals(uf.groupby(["agravo", "ano"]).casos.sum())


def test_codigos_ibge_7_digitos():
    for arquivo in ("zoonoses_municipio_ano.csv", "antr_municipio_ano.csv", "municipios.csv"):
        codigos = pd.read_csv(SITE_DADOS / arquivo, dtype={"codigo7": str}).codigo7
        assert codigos.str.fullmatch(r"\d{7}").all(), arquivo


def test_supressao_no_perfil():
    perfil = pd.read_csv(SITE_DADOS / "zoonoses_perfil_brasil.csv")
    assert not perfil.casos.between(1, 4).any()


def test_antirrabico_especies_somam_total():
    antr = pd.read_csv(SITE_DADOS / "antr_municipio_ano.csv")
    especies = ["cao", "gato", "morcego", "primata", "raposa", "herbivoro", "outro"]
    assert (antr[especies].sum(axis=1) <= antr.total).all()
    assert antr[especies].sum().sum() / antr.total.sum() > 0.99


def test_dataset_ml_leishmaniose():
    df = pd.read_csv(ML_SAIDA / "leishmaniose_obito.csv")
    resumo = json.loads((ML_SAIDA / "leishmaniose_obito.json").read_text())
    assert set(df.obito.unique()) == {0, 1}
    assert len(df) == resumo["linhas"]
    assert df.idade.between(0, 90).all()
    proibidas = {"codigo7", "municipio", "ID_MN_RESI", "DT_NOTIFIC", "DT_SIN_PRI", "uf"}
    assert not proibidas & set(df.columns), "dataset não pode ter município, UF ou datas"
    mini = pd.read_csv(ML_SAIDA / "leishmaniose_obito_mini.csv")
    assert len(mini) <= 5000
    assert abs(mini.obito.mean() - df.obito.mean()) < 0.01
