"""Datasets didáticos para machine learning (scikit-learn)."""

from __future__ import annotations

import json
import logging
import shutil

import pandas as pd

from . import codigos as C
from .config import ML_SAIDA, RAIZ
from .sinan import view_harmonizada

log = logging.getLogger(__name__)

SEMENTE = 20240601
TAMANHO_MINI = 5000

SINAIS_LEIV = {
    "FEBRE": "febre", "FRAQUEZA": "fraqueza", "EDEMA": "edema", "EMAGRA": "emagrecimento",
    "TOSSE": "tosse_diarreia", "PALIDEZ": "palidez", "BACO": "esplenomegalia",
    "INFECCIOSO": "quadro_infeccioso", "FEN_HEMORR": "fenomenos_hemorragicos",
    "FIGADO": "hepatomegalia", "ICTERICIA": "ictericia",
}
EXAME = {"1": "Positivo", "2": "Negativo", "3": "Não realizado"}


def _rotulo(col: str, mapa: dict, padrao: str = "Ignorado") -> str:
    return C.sql_case(col, mapa, padrao)


def leishmaniose_obito(con) -> dict:
    """Óbito por leishmaniose visceral × cura, entre casos confirmados.

    Granularidade reduzida para proteger a privacidade: região (não município),
    ano (não data), idade limitada a 90.
    """
    v = view_harmonizada(con, "LEIV")
    sinais = ",\n".join(f"{_rotulo(c, C.SIM_NAO)} AS {n}" for c, n in SINAIS_LEIV.items())
    sql = f"""
        SELECT
            ano,
            regiao_res AS regiao,
            least(idade_anos, 90) AS idade,
            {_rotulo('CS_SEXO', C.SEXO)} AS sexo,
            {_rotulo('CS_RACA', C.RACA)} AS raca_cor,
            CASE WHEN CS_SEXO = 'F' AND CS_GESTANT IN ('1','2','3','4') THEN 'Sim'
                 WHEN CS_SEXO = 'F' AND CS_GESTANT = '5' THEN 'Não'
                 WHEN CS_SEXO = 'M' OR CS_GESTANT = '6' THEN 'Não se aplica'
                 ELSE 'Ignorado' END AS gestante,
            {sinais},
            {_rotulo('HIV', C.SIM_NAO)} AS coinfeccao_hiv,
            {_rotulo('DIAG_PAR_N', EXAME)} AS exame_parasitologico,
            {_rotulo('IFI', EXAME)} AS exame_ifi,
            {_rotulo('ENTRADA', C.LEIV_ENTRADA)} AS tipo_entrada,
            CASE EVOLUCAO WHEN '3' THEN 1 ELSE 0 END AS obito
        FROM {v}
        WHERE confirmado AND EVOLUCAO IN ('1', '3') AND regiao_res IS NOT NULL
          AND idade_anos IS NOT NULL AND situacao = 'final'
        ORDER BY ano
    """
    df = con.execute(sql).df()
    df["idade"] = df["idade"].astype(int)
    df["obito"] = df["obito"].astype(int)

    ML_SAIDA.mkdir(parents=True, exist_ok=True)
    completo = ML_SAIDA / "leishmaniose_obito.csv"
    df.to_csv(completo, index=False)

    # Amostra mini estratificada pelo desfecho
    frac = min(1.0, TAMANHO_MINI / len(df))
    mini = df.groupby("obito", group_keys=False).sample(frac=frac, random_state=SEMENTE)
    mini = mini.sort_values("ano").reset_index(drop=True)
    mini.to_csv(ML_SAIDA / "leishmaniose_obito_mini.csv", index=False)

    resumo = {
        "dataset": "leishmaniose_obito",
        "linhas": int(len(df)),
        "linhas_mini": int(len(mini)),
        "colunas": list(df.columns),
        "alvo": "obito",
        "prevalencia_alvo": round(float(df.obito.mean()), 4),
        "anos": [int(df.ano.min()), int(df.ano.max())],
        "obitos": int(df.obito.sum()),
        "pct_ignorado": {
            c: round(float((df[c] == "Ignorado").mean()), 3)
            for c in df.columns
            if not pd.api.types.is_numeric_dtype(df[c]) and (df[c] == "Ignorado").any()
        },
    }
    (ML_SAIDA / "leishmaniose_obito.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2))
    log.info("leishmaniose_obito: %d linhas, %.1f%% óbitos", len(df), 100 * resumo["prevalencia_alvo"])
    return resumo


def gerar(con) -> None:
    leishmaniose_obito(con)
    # Notebooks de linha de base acompanham os datasets no site
    for nb in (RAIZ / "notebooks").glob("*.ipynb"):
        shutil.copy2(nb, ML_SAIDA / nb.name)
