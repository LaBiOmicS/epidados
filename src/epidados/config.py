"""Configuração central: caminhos, anos e agravos tratados pelo pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CACHE = RAIZ / "cache"
RAW = CACHE / "raw"
PARQUET = CACHE / "parquet"
SITE = RAIZ / "site"
SITE_DADOS = SITE / "dados"
ML_SAIDA = SITE / "dados-ia" / "arquivos"

FTP_HOST = "ftp.datasus.gov.br"
FTP_SINAN = "/dissemin/publicos/SINAN/DADOS"

# SINAN Net começa em 2007; arquivos anteriores têm fichas diferentes.
ANO_INICIAL = 2007


@dataclass(frozen=True)
class Agravo:
    codigo: str  # prefixo do arquivo no FTP (ex.: LEIV)
    nome: str
    colunas: tuple[str, ...]
    # Agravos de "atendimento" (ex.: antirrábico) não têm classificação final.
    usa_classificacao: bool = True
    obito_codigo: str | None = None  # valor de EVOLUCAO para óbito pelo agravo
    extras: dict = field(default_factory=dict)


COLUNAS_COMUNS = (
    "DT_NOTIFIC", "NU_ANO", "SG_UF_NOT", "ID_MUNICIP", "DT_SIN_PRI",
    "NU_IDADE_N", "CS_SEXO", "CS_GESTANT", "CS_RACA", "CS_ESCOL_N",
    "SG_UF", "ID_MN_RESI", "ID_PAIS",
)

AGRAVOS: dict[str, Agravo] = {
    "LEIV": Agravo(
        codigo="LEIV",
        nome="Leishmaniose visceral",
        colunas=COLUNAS_COMUNS + (
            "FEBRE", "FRAQUEZA", "EDEMA", "EMAGRA", "TOSSE", "PALIDEZ", "BACO",
            "INFECCIOSO", "FEN_HEMORR", "FIGADO", "ICTERICIA", "HIV",
            "DIAG_PAR_N", "IFI", "ENTRADA", "DROGA", "FALENCIA",
            "CLASSI_FIN", "CRITERIO", "TPAUTOCTO", "EVOLUCAO",
        ),
        obito_codigo="3",
    ),
    "LEPT": Agravo(
        codigo="LEPT",
        nome="Leptospirose",
        colunas=COLUNAS_COMUNS + (
            "ANT_CB_LAM", "ANT_CB_CRI", "ANT_CB_CAI", "ANT_CB_FOS", "ANT_CB_SIN",
            "ANT_CB_PLA", "ANT_CB_COR", "ANT_CB_ROE", "ANT_CB_GRA", "ANT_CB_TER",
            "ANT_CB_LIX", "ATE_HOSP", "CLASSI_FIN", "CRITERIO", "CON_AMBIEN",
            "EVOLUCAO",
        ),
        obito_codigo="2",
    ),
    "ANTR": Agravo(
        codigo="ANTR",
        nome="Atendimento antirrábico humano",
        colunas=COLUNAS_COMUNS + (
            "ANT_MORDED", "ANT_ARRANH", "ANT_LAMBED", "FERIMENTO", "ANIMAL",
            "CONDIC_ANI", "OBSERVACAO", "TRAT_ATUAL",
        ),
        usa_classificacao=False,
    ),
}
