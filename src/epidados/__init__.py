"""EpiDados: pipeline de dados do DATASUS para ensino."""

from __future__ import annotations

import argparse
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="epidados", description=__doc__)
    parser.add_argument("etapa", choices=["preparar", "agregar", "ml", "malhas", "referencia", "tudo"], default="tudo", nargs="?")
    parser.add_argument("--agravos", nargs="*", default=None, help="ex.: LEIV LEPT ANTR")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)

    if args.etapa == "referencia":
        from .baixar import atualizar_referencia_ibge

        atualizar_referencia_ibge()
        return 0

    import duckdb

    from . import agregar, ibge, ml, sinan
    from .config import AGRAVOS

    agravos = args.agravos or list(AGRAVOS)
    if args.etapa in ("preparar", "tudo"):
        for ag in agravos:
            sinan.preparar(ag)
    if args.etapa in ("malhas", "tudo"):
        ibge.exportar_malhas()
    if args.etapa in ("agregar", "ml", "tudo"):
        con = duckdb.connect()
        ano_final = max(int(p.stem) for ag in AGRAVOS for p in (sinan.PARQUET / "sinan" / ag).glob("*.parquet"))
        ibge.registrar(con, ano_final)
        if args.etapa in ("agregar", "tudo"):
            agregar.gerar(con)
        if args.etapa in ("ml", "tudo"):
            ml.gerar(con)
    return 0
