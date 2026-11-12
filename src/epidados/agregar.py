"""Gera os arquivos agregados (CSV/JSON) consumidos pelo site."""

from __future__ import annotations

import datetime as dt
import json
import logging

import duckdb

from . import codigos as C
from .config import AGRAVOS, SITE_DADOS
from .sinan import view_harmonizada

log = logging.getLogger(__name__)

LIMIAR_SUPRESSAO = 5  # células de perfil com 1 a 4 casos são suprimidas


def _csv(con, sql: str, nome: str) -> int:
    SITE_DADOS.mkdir(parents=True, exist_ok=True)
    destino = SITE_DADOS / nome
    con.execute(f"COPY ({sql}) TO '{destino.as_posix()}' (HEADER, DELIMITER ',')")
    n = con.execute(f"SELECT count(*) FROM ({sql})").fetchone()[0]
    log.info("%s: %d linhas, %.0f KB", nome, n, destino.stat().st_size / 1024)
    return n


def _suprimir(expr: str) -> str:
    return f"CASE WHEN {expr} BETWEEN 1 AND {LIMIAR_SUPRESSAO - 1} THEN NULL ELSE {expr} END"


def zoonoses(con) -> None:
    partes_mun, partes_uf, partes_mes, partes_perfil = [], [], [], []
    for ag in ("LEIV", "LEPT"):
        v = view_harmonizada(con, ag)
        base = f"(SELECT * FROM {v} WHERE confirmado)"
        partes_mun.append(f"""
            SELECT '{ag}' AS agravo, mun_res AS codigo7, ano,
                   count(*) AS casos, count(*) FILTER (WHERE obito_agravo) AS obitos
            FROM {base} WHERE mun_res IS NOT NULL GROUP BY ALL""")
        partes_uf.append(f"""
            SELECT '{ag}' AS agravo, uf_res AS uf, ano, any_value(situacao) AS situacao,
                   count(*) AS casos, count(*) FILTER (WHERE obito_agravo) AS obitos
            FROM {base} WHERE uf_res IS NOT NULL GROUP BY ALL""")
        partes_mes.append(f"""
            SELECT '{ag}' AS agravo, uf_res AS uf, year(data_ref) AS ano, month(data_ref) AS mes,
                   count(*) AS casos
            FROM {base} WHERE uf_res IS NOT NULL AND data_ref IS NOT NULL
              AND year(data_ref) >= (SELECT min(ano) FROM {v})
            GROUP BY ALL""")
        dims = {
            "Sexo": C.sql_case("CS_SEXO", C.SEXO),
            "Faixa etária": C.sql_faixa(),
            "Raça/cor": C.sql_case("CS_RACA", C.RACA),
        }
        if ag == "LEIV":
            dims["Coinfecção HIV"] = C.sql_case("HIV", C.LEIV_HIV)
            dims["Evolução"] = C.sql_case("EVOLUCAO", C.LEIV_EVOLUCAO)
            dims["Entrada"] = C.sql_case("ENTRADA", C.LEIV_ENTRADA)
        else:
            dims["Hospitalização"] = C.sql_case("ATE_HOSP", C.SIM_NAO)
            dims["Evolução"] = C.sql_case("EVOLUCAO", C.LEPT_EVOLUCAO)
        for nome, expr in dims.items():
            partes_perfil.append(f"""
                SELECT '{ag}' AS agravo, ano, '{nome}' AS dimensao, {expr} AS categoria, count(*) AS casos
                FROM {base} GROUP BY ALL""")
        if ag == "LEPT":
            for campo, rotulo in C.LEPT_EXPOSICAO.items():
                partes_perfil.append(f"""
                    SELECT 'LEPT' AS agravo, ano, 'Exposição de risco' AS dimensao,
                           '{rotulo.replace("'", "''")}' AS categoria,
                           count(*) FILTER (WHERE {campo} = '1') AS casos
                    FROM {base} GROUP BY ALL""")

    _csv(con, f"""
        SELECT z.*, round(p.pop) AS pop
        FROM ({' UNION ALL '.join(partes_mun)}) z
        LEFT JOIN populacao p ON p.codigo7 = z.codigo7 AND p.ano = z.ano
        ORDER BY agravo, codigo7, ano""", "zoonoses_municipio_ano.csv")

    _csv(con, f"""
        WITH z AS ({' UNION ALL '.join(partes_uf)}),
             pu AS (SELECT m.uf_sigla AS uf, p.ano, sum(p.pop) AS pop
                    FROM populacao p JOIN municipios m USING (codigo7) GROUP BY ALL)
        SELECT z.*, round(pu.pop) AS pop,
               round(100000 * z.casos / pu.pop, 3) AS incidencia_100mil,
               round(100 * z.obitos / z.casos, 2) AS letalidade_pct
        FROM z LEFT JOIN pu USING (uf, ano)
        ORDER BY agravo, uf, ano""", "zoonoses_uf_ano.csv")

    _csv(con, f"SELECT * FROM ({' UNION ALL '.join(partes_mes)}) ORDER BY agravo, uf, ano, mes",
         "zoonoses_uf_mes.csv")

    _csv(con, f"""
        SELECT agravo, ano, dimensao, categoria, {_suprimir('casos')} AS casos
        FROM ({' UNION ALL '.join(partes_perfil)})
        ORDER BY agravo, dimensao, ano, categoria""", "zoonoses_perfil_brasil.csv")


def antirrabico(con) -> None:
    v = view_harmonizada(con, "ANTR")
    especie = C.sql_case("ANIMAL", C.ANTR_ANIMAL, "Ignorado")
    colunas = ", ".join(
        f"count(*) FILTER (WHERE ANIMAL = '{k}') AS {chave}" for k, chave in C.ANTR_ANIMAL_CHAVE.items()
    )
    _csv(con, f"""
        SELECT a.mun_res AS codigo7, a.ano, count(*) AS total, {colunas}, round(any_value(p.pop)) AS pop
        FROM {v} a LEFT JOIN populacao p ON p.codigo7 = a.mun_res AND p.ano = a.ano
        WHERE a.mun_res IS NOT NULL GROUP BY ALL ORDER BY codigo7, ano""", "antr_municipio_ano.csv")

    _csv(con, f"""
        SELECT uf_res AS uf, ano, any_value(situacao) AS situacao, {especie} AS especie, count(*) AS atendimentos
        FROM {v} WHERE uf_res IS NOT NULL GROUP BY ALL ORDER BY uf, ano, especie""", "antr_uf_ano_especie.csv")

    _csv(con, f"""
        SELECT ano, {especie} AS especie, {C.sql_case('CONDIC_ANI', C.ANTR_CONDICAO)} AS condicao,
               count(*) AS atendimentos
        FROM {v} GROUP BY ALL ORDER BY ano, especie, condicao""", "antr_especie_condicao.csv")

    _csv(con, f"""
        SELECT ano, {especie} AS especie, {C.sql_case('TRAT_ATUAL', C.ANTR_CONDUTA, 'Não informado')} AS conduta,
               count(*) AS atendimentos
        FROM {v} GROUP BY ALL ORDER BY ano, especie, conduta""", "antr_especie_conduta.csv")


def referencias(con) -> None:
    _csv(con, "SELECT codigo7, municipio, uf_sigla AS uf, regiao FROM municipios ORDER BY codigo7",
         "municipios.csv")
    anos = [r[0] for r in con.execute("SELECT DISTINCT ano FROM populacao ORDER BY ano").fetchall()]
    colunas = ", ".join(f"round(any_value(pop) FILTER (WHERE ano = {a})) AS p{a}" for a in anos)
    _csv(con, f"SELECT codigo7, {colunas} FROM populacao GROUP BY codigo7 ORDER BY codigo7",
         "populacao_municipio.csv")
    _csv(con, """SELECT m.uf_sigla AS uf, any_value(m.uf_nome) AS uf_nome, any_value(m.regiao) AS regiao,
                        p.ano, round(sum(p.pop)) AS pop
                 FROM populacao p JOIN municipios m USING (codigo7) GROUP BY ALL ORDER BY uf, ano""",
         "populacao_uf_ano.csv")


def metadados(con) -> None:
    info = {"gerado_em": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "agravos": {}}
    for ag, cfg in AGRAVOS.items():
        v = f"{ag.lower()}_h"
        linhas = con.execute(f"SELECT ano, any_value(situacao), count(*) FROM {v} GROUP BY ano ORDER BY ano").fetchall()
        info["agravos"][ag] = {
            "nome": cfg.nome,
            "anos": [{"ano": a, "situacao": s, "registros": n} for a, s, n in linhas],
        }
    (SITE_DADOS / "metadados.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))


def gerar(con: duckdb.DuckDBPyConnection) -> None:
    referencias(con)
    zoonoses(con)
    antirrabico(con)
    metadados(con)
