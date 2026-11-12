"""Conversão dos arquivos .dbc do SINAN em Parquet e harmonização com DuckDB."""

from __future__ import annotations

import datetime as dt
import logging
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
from dbfread import DBF
from pyreaddbc import dbc2dbf

from .baixar import ArquivoSinan, baixar_sinan, inventario
from .config import AGRAVOS, PARQUET

log = logging.getLogger(__name__)

VERSAO_CONVERSAO = "1"  # incremente para forçar reconversão de todos os arquivos


def _parquet_destino(arq: ArquivoSinan) -> Path:
    return PARQUET / "sinan" / arq.agravo / f"{arq.ano}.parquet"


def _normalizar(valor):
    if valor is None:
        return None
    if isinstance(valor, (dt.date, dt.datetime)):
        return valor.isoformat()[:10]
    texto = str(valor).strip()
    return texto or None


def converter(arq: ArquivoSinan) -> Path:
    """Converte um .dbc em Parquet com as colunas configuradas do agravo (todas como texto)."""
    destino = _parquet_destino(arq)
    marca = destino.with_suffix(".meta")
    assinatura = f"{arq.nome}|{arq.situacao}|{arq.tamanho}|{VERSAO_CONVERSAO}"
    if destino.exists() and marca.exists() and marca.read_text() == assinatura:
        return destino

    origem = baixar_sinan(arq)
    colunas = AGRAVOS[arq.agravo].colunas
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        dbf = Path(tmp) / "x.dbf"
        dbc2dbf(str(origem), str(dbf))
        tabela = DBF(str(dbf), encoding="iso-8859-1", load=False, char_decode_errors="replace")
        presentes = [c for c in colunas if c in tabela.field_names]
        ausentes = [c for c in colunas if c not in tabela.field_names]
        if ausentes:
            log.info("%s: colunas ausentes nesta ficha: %s", arq.nome, ", ".join(ausentes))
        registros = ([_normalizar(r[c]) for c in presentes] for r in tabela)
        df = pd.DataFrame(registros, columns=presentes, dtype="string")
    for c in ausentes:
        df[c] = pd.Series(pd.NA, index=df.index, dtype="string")
    df = df[list(colunas)]
    df["ano"] = arq.ano
    df["situacao"] = arq.situacao
    df.to_parquet(destino, index=False)
    marca.write_text(assinatura)
    log.info("convertido %s: %d registros", arq.nome, len(df))
    return destino


def preparar(agravos: list[str], anos: list[int] | None = None, processos: int | None = None) -> list[Path]:
    """Baixa e converte os arquivos dos agravos em paralelo (um processo por arquivo).

    Os arquivos maiores (ex.: ANTR, ~600 mil registros/ano) vão primeiro, para os
    processos terminarem juntos."""
    arquivos = [a for ag in agravos for a in inventario(ag) if not anos or a.ano in anos]
    arquivos.sort(key=lambda a: a.tamanho, reverse=True)
    nivel = logging.getLogger().level
    with ProcessPoolExecutor(processos or os.cpu_count(), initializer=_configurar_log, initargs=(nivel,)) as ex:
        return list(ex.map(converter, arquivos))


def _configurar_log(nivel: int) -> None:
    logging.basicConfig(level=nivel, format="%(asctime)s %(levelname)s %(message)s")


# ------------------------------------------------------------ harmonização

SQL_IDADE = """
CASE
  WHEN NU_IDADE_N IS NULL OR length(NU_IDADE_N) <> 4 OR NOT regexp_matches(NU_IDADE_N, '^[0-9]+$') THEN NULL
  WHEN substr(NU_IDADE_N, 1, 1) = '4' THEN CAST(substr(NU_IDADE_N, 2) AS INTEGER)
  WHEN substr(NU_IDADE_N, 1, 1) IN ('1', '2', '3') THEN 0
  ELSE NULL
END
"""

SQL_DATA_REF = """
COALESCE(
  CASE WHEN TRY_CAST(DT_SIN_PRI AS DATE) BETWEEN make_date(ano - 1, 1, 1) AND make_date(ano, 12, 31)
       THEN TRY_CAST(DT_SIN_PRI AS DATE) END,
  TRY_CAST(DT_NOTIFIC AS DATE)
)
"""


def view_harmonizada(con, agravo: str) -> str:
    """Cria a view `<agravo>_h` com campos derivados e município de residência IBGE (7 dígitos).

    Requer a tabela `municipios` (codigo7, codigo6, uf_sigla...) já registrada na conexão.
    """
    cfg = AGRAVOS[agravo]
    caminho = (PARQUET / "sinan" / agravo / "*.parquet").as_posix()
    confirmado = "CLASSI_FIN = '1'" if cfg.usa_classificacao else "TRUE"
    obito = f"EVOLUCAO = '{cfg.obito_codigo}'" if cfg.obito_codigo else "FALSE"
    nome = f"{agravo.lower()}_h"
    con.execute(f"""
        CREATE OR REPLACE VIEW {nome} AS
        SELECT s.*,
               {SQL_IDADE} AS idade_anos,
               {SQL_DATA_REF} AS data_ref,
               m.codigo7 AS mun_res,
               m.uf_sigla AS uf_res,
               m.regiao AS regiao_res,
               ({confirmado}) AS confirmado,
               ({obito}) AS obito_agravo
        FROM read_parquet('{caminho}', union_by_name = true) s
        LEFT JOIN municipios m ON m.codigo6 = s.ID_MN_RESI
    """)
    return nome
