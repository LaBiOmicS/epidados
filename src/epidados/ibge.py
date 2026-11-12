"""Tabelas de referência do IBGE: municípios, população anual e malhas simplificadas."""

from __future__ import annotations

import json
import logging

import pandas as pd

from .baixar import ibge_malha, ibge_municipios, ibge_populacao_bruta
from .config import ANO_INICIAL, PARQUET, SITE_DADOS

log = logging.getLogger(__name__)


def municipios() -> pd.DataFrame:
    linhas = []
    for m in ibge_municipios():
        uf = m["microrregiao"]["mesorregiao"]["UF"] if m.get("microrregiao") else m["regiao-imediata"]["regiao-intermediaria"]["UF"]
        linhas.append({
            "codigo7": str(m["id"]),
            "codigo6": str(m["id"])[:6],
            "municipio": m["nome"],
            "uf_sigla": uf["sigla"],
            "uf_nome": uf["nome"],
            "regiao": uf["regiao"]["nome"],
        })
    df = pd.DataFrame(linhas).sort_values("codigo7").reset_index(drop=True)
    assert df.codigo6.is_unique, "códigos de 6 dígitos deveriam ser únicos"
    return df


def populacao(ano_final: int) -> pd.DataFrame:
    """População por município (7 dígitos) e ano, de ANO_INICIAL até ano_final.

    Anos sem estimativa nem censo são interpolados linearmente; anos após a última
    estimativa repetem o último valor. A coluna `fonte` registra a origem.
    """
    bruto = ibge_populacao_bruta()
    linhas = []
    for ano, valores in bruto.items():
        for r in valores:
            v = r.get("V")
            if v and v.replace(".", "").isdigit():
                linhas.append({"codigo7": r["D1C"], "ano": ano, "pop": float(v)})
    df = pd.DataFrame(linhas)
    largo = df.pivot_table(index="codigo7", columns="ano", values="pop")
    anos = list(range(ANO_INICIAL, ano_final + 1))
    original = set(largo.columns)
    largo = largo.reindex(columns=sorted(set(largo.columns) | set(anos)))
    largo = largo.interpolate(axis=1, limit_area="inside").ffill(axis=1)
    longo = largo[anos].reset_index().melt(id_vars="codigo7", var_name="ano", value_name="pop")
    longo["ano"] = longo["ano"].astype(int)
    longo["fonte"] = longo["ano"].map(
        lambda a: "censo" if a in (2010, 2022) else ("estimativa" if a in original else "interpolada")
    )
    return longo.dropna(subset=["pop"])


def _arredondar(coords, casas=3):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], casas), round(coords[1], casas)]
    return [_arredondar(c, casas) for c in coords]


def _area(anel) -> float:
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(anel, anel[1:] + anel[:1])) / 2


def _orientar_para_d3(geometria: dict) -> dict:
    """d3-geo usa geometria esférica: anel externo no sentido HORÁRIO e buracos no anti-horário,
    o inverso do RFC 7946 seguido pelo IBGE. Com a orientação errada, o d3 preenche o
    complemento do polígono (o globo inteiro menos o município)."""
    def poligono(aneis):
        saida = []
        for i, anel in enumerate(aneis):
            horario = _area(anel) < 0
            externo = i == 0
            saida.append(anel if horario == externo else anel[::-1])
        return saida

    if geometria["type"] == "Polygon":
        geometria["coordinates"] = poligono(geometria["coordinates"])
    elif geometria["type"] == "MultiPolygon":
        geometria["coordinates"] = [poligono(p) for p in geometria["coordinates"]]
    return geometria


def exportar_malhas() -> None:
    """Grava as malhas de municípios e UFs com coordenadas arredondadas (arquivo menor)."""
    SITE_DADOS.mkdir(parents=True, exist_ok=True)
    for nivel, arquivo, casas in (("municipio", "malha_municipios.geojson", 3), ("UF", "malha_uf.geojson", 3)):
        malha = ibge_malha(nivel)
        for f in malha["features"]:
            f["geometry"]["coordinates"] = _arredondar(f["geometry"]["coordinates"], casas)
            _orientar_para_d3(f["geometry"])
            f["properties"] = {"codigo": f["properties"]["codarea"]}
        (SITE_DADOS / arquivo).write_text(json.dumps(malha, separators=(",", ":")))
        log.info("malha %s: %.1f MB", nivel, (SITE_DADOS / arquivo).stat().st_size / 1e6)


def registrar(con, ano_final: int) -> None:
    PARQUET.mkdir(parents=True, exist_ok=True)
    mun = municipios()
    pop = populacao(ano_final)
    con.register("municipios_df", mun)
    con.execute("CREATE OR REPLACE TABLE municipios AS SELECT * FROM municipios_df")
    con.register("populacao_df", pop)
    con.execute("CREATE OR REPLACE TABLE populacao AS SELECT * FROM populacao_df")
