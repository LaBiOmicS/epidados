"""Download com cache dos arquivos do SINAN (FTP DATASUS) e das bases do IBGE."""

from __future__ import annotations

import ftplib
import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from .config import ANO_INICIAL, FTP_HOST, FTP_SINAN, RAW

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ArquivoSinan:
    agravo: str
    ano: int
    situacao: str  # "final" ou "preliminar"
    nome: str  # ex.: LEIVBR23.dbc
    tamanho: int

    @property
    def caminho_remoto(self) -> str:
        pasta = "FINAIS" if self.situacao == "final" else "PRELIM"
        return f"{FTP_SINAN}/{pasta}/{self.nome}"

    @property
    def caminho_local(self) -> Path:
        return RAW / "sinan" / self.situacao / self.nome


def _ftp() -> ftplib.FTP:
    ftp = ftplib.FTP(FTP_HOST, timeout=120)
    ftp.login()
    return ftp


def _listar(ftp: ftplib.FTP, pasta: str) -> dict[str, int]:
    linhas: list[str] = []
    ftp.retrlines(f"LIST {FTP_SINAN}/{pasta}", linhas.append)
    arquivos = {}
    for linha in linhas:
        partes = linha.split()
        if len(partes) >= 4 and partes[-1].lower().endswith(".dbc"):
            arquivos[partes[-1]] = int(partes[2])
    return arquivos


def _ano(nome: str) -> int:
    aa = int(re.search(r"(\d{2})\.dbc$", nome, re.I).group(1))
    return 2000 + aa if aa < 90 else 1900 + aa


def inventario(agravo: str) -> list[ArquivoSinan]:
    """Lista os arquivos do agravo. Se um ano existe em FINAIS, ignora o PRELIM."""
    with _ftp() as ftp:
        finais = _listar(ftp, "FINAIS")
        prelim = _listar(ftp, "PRELIM")
    padrao = re.compile(rf"^{agravo}BR\d{{2}}\.dbc$", re.I)
    por_ano: dict[int, ArquivoSinan] = {}
    for situacao, lista in (("preliminar", prelim), ("final", finais)):
        for nome, tamanho in lista.items():
            if padrao.match(nome) and _ano(nome) >= ANO_INICIAL:
                por_ano[_ano(nome)] = ArquivoSinan(agravo, _ano(nome), situacao, nome, tamanho)
    return [por_ano[a] for a in sorted(por_ano)]


def baixar_sinan(arquivo: ArquivoSinan, tentativas: int = 3) -> Path:
    destino = arquivo.caminho_local
    if destino.exists() and destino.stat().st_size == arquivo.tamanho:
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(".part")
    for i in range(1, tentativas + 1):
        try:
            with _ftp() as ftp, open(tmp, "wb") as fh:
                ftp.retrbinary(f"RETR {arquivo.caminho_remoto}", fh.write)
            if tmp.stat().st_size != arquivo.tamanho:
                raise OSError(f"tamanho divergente para {arquivo.nome}")
            tmp.replace(destino)
            log.info("baixado %s (%s)", arquivo.nome, arquivo.situacao)
            return destino
        except (OSError, ftplib.Error) as erro:
            log.warning("falha ao baixar %s (tentativa %d): %s", arquivo.nome, i, erro)
            time.sleep(5 * i)
    raise RuntimeError(f"não foi possível baixar {arquivo.nome}")


# --------------------------------------------------------------------- IBGE

IBGE_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
IBGE_MALHA = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
    "?formato=application/vnd.geo%2Bjson&qualidade=minima&intrarregiao={nivel}"
)
SIDRA = "https://apisidra.ibge.gov.br/values"


def _get_json(url: str, destino: Path, forcar: bool = False):
    if destino.exists() and not forcar:
        return json.loads(destino.read_text())
    destino.parent.mkdir(parents=True, exist_ok=True)
    for i in range(1, 4):
        try:
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            dados = r.json()
            destino.write_text(json.dumps(dados))
            return dados
        except (requests.RequestException, ValueError) as erro:
            log.warning("falha em %s (tentativa %d): %s", url, i, erro)
            time.sleep(5 * i)
    raise RuntimeError(f"não foi possível obter {url}")


def ibge_municipios():
    return _get_json(IBGE_MUNICIPIOS, RAW / "ibge" / "municipios.json")


def ibge_malha(nivel: str):
    """nivel: 'municipio' ou 'UF'."""
    return _get_json(IBGE_MALHA.format(nivel=nivel), RAW / "ibge" / f"malha_{nivel.lower()}.json")


def ibge_populacao_bruta() -> dict[int, list[dict]]:
    """Valores de população por município e ano, conforme disponíveis no SIDRA.

    - Tabela 6579: estimativas anuais (não há 2007, 2010, 2022 e 2023)
    - Tabela 202: Censo 2010
    - Tabela 4709: Censo 2022
    """
    periodos = [p["id"] for p in _get_json(
        "https://servicodados.ibge.gov.br/api/v3/agregados/6579/periodos",
        RAW / "ibge" / "periodos_6579.json",
        forcar=True,
    )]
    consultas = {int(p): f"{SIDRA}/t/6579/n6/all/v/9324/p/{p}" for p in periodos}
    consultas[2010] = f"{SIDRA}/t/202/n6/all/v/93/p/2010"
    consultas[2022] = f"{SIDRA}/t/4709/n6/all/v/93/p/2022"
    saida = {}
    for ano, url in sorted(consultas.items()):
        if ano < ANO_INICIAL - 1:
            continue
        saida[ano] = _get_json(url, RAW / "ibge" / f"pop_{ano}.json")[1:]
    return saida
