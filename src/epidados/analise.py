"""Análise comentada do dataset de óbito por leishmaniose visceral.

Gera um JSON com resultados reais (exploração, modelos, curvas, limiar, equidade)
que a página `dados-ia/leishmaniose-analise.qmd` desenha. Usa scikit-learn
(grupo `dev`), por isso é importado só quando a etapa `ml` roda.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

SEMENTE = 0
ANO_CORTE = 2019  # treino até este ano; teste depois
FAIXAS = [(0, 0, "<1"), (1, 4, "1–4"), (5, 9, "5–9"), (10, 19, "10–19"), (20, 39, "20–39"),
          (40, 59, "40–59"), (60, 200, "60+")]
VARIAVEIS_RISCO = ["coinfeccao_hiv", "fenomenos_hemorragicos", "ictericia", "edema",
                   "quadro_infeccioso", "tipo_entrada"]


def _wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centro - meia, centro + meia)


def _risco(df: pd.DataFrame, coluna: str) -> list[dict]:
    linhas = []
    ordenar = isinstance(df[coluna].dtype, pd.CategoricalDtype)  # faixas etárias em ordem
    for categoria, g in df.groupby(coluna, sort=ordenar, observed=True):
        k, n = int(g.obito.sum()), len(g)
        li, ls = _wilson(k, n)
        linhas.append({"categoria": str(categoria), "n": n, "obitos": k,
                       "risco": round(k / n, 4), "ic_inf": round(li, 4), "ic_sup": round(ls, 4)})
    return linhas


def _r(x, casas: int = 4) -> float:
    return round(float(x), casas)


def _pipeline(modelo, categoricas, numericas):
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categoricas),
        ("num", StandardScaler(), numericas),
    ])
    return make_pipeline(pre, modelo)


def _metricas(y, prob, limiar: float = 0.5) -> dict:
    from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                                 precision_score, recall_score, roc_auc_score)
    pred = (prob >= limiar).astype(int)
    return {
        "acuracia": _r(accuracy_score(y, pred), 3),
        "acuracia_balanceada": _r(balanced_accuracy_score(y, pred), 3),
        "auc_roc": _r(roc_auc_score(y, prob), 3),
        "auc_pr": _r(average_precision_score(y, prob), 3),
        "recall": _r(recall_score(y, pred, zero_division=0), 3),
        "precisao": _r(precision_score(y, pred, zero_division=0), 3),
    }


def leishmaniose(csv: Path, saida: Path) -> dict:
    from sklearn.calibration import calibration_curve
    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.inspection import permutation_importance
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import precision_recall_curve, roc_curve
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(csv)
    r: dict = {"n": len(df), "obitos": int(df.obito.sum()), "ano_corte": ANO_CORTE}

    # ---------- 1. Exploração ----------
    por_ano = df.groupby("ano").obito.agg(["sum", "size"]).reset_index()
    r["por_ano"] = [{"ano": int(a), "n": int(n), "obitos": int(k), "risco": _r(k / n),
                     **dict(zip(("ic_inf", "ic_sup"), map(_r, _wilson(int(k), int(n)))))}
                    for a, k, n in por_ano.itertuples(index=False)]

    rotulo_faixa = pd.cut(df.idade, [f[0] - 0.5 for f in FAIXAS] + [FAIXAS[-1][1] + 0.5],
                          labels=[f[2] for f in FAIXAS])
    r["por_idade"] = _risco(df.assign(faixa=rotulo_faixa), "faixa")
    r["por_variavel"] = {v: _risco(df, v) for v in VARIAVEIS_RISCO}

    # HIV × faixa etária: confundimento clássico (HIV concentra-se em adultos)
    adultos = df[df.idade >= 20]
    r["hiv_adultos"] = _risco(adultos, "coinfeccao_hiv")
    r["hiv_por_faixa"] = [
        {"faixa": str(f), **{k: v for k, v in linha.items()}}
        for f, g in df.assign(faixa=rotulo_faixa).groupby("faixa", observed=True)
        for linha in _risco(g, "coinfeccao_hiv")
    ]

    # ---------- 2. Modelos ----------
    y = df.pop("obito")
    X = df
    categoricas = list(X.select_dtypes(exclude="number").columns)
    numericas = ["idade"]
    treino = X.ano <= ANO_CORTE
    X_tr, X_te, y_tr, y_te = X[treino], X[~treino], y[treino], y[~treino]
    r["treino"] = {"n": int(len(y_tr)), "risco": _r(y_tr.mean())}
    r["teste"] = {"n": int(len(y_te)), "risco": _r(y_te.mean())}

    modelos = {
        "Sempre \"não morreu\"": DummyClassifier(strategy="most_frequent"),
        "Regressão logística": _pipeline(LogisticRegression(max_iter=2000, class_weight="balanced"),
                                         categoricas, numericas),
        "Gradient boosting": _pipeline(HistGradientBoostingClassifier(class_weight="balanced",
                                                                      random_state=SEMENTE),
                                       categoricas, numericas),
    }
    probs = {}
    r["modelos"] = []
    for nome, m in modelos.items():
        m.fit(X_tr, y_tr)
        probs[nome] = m.predict_proba(X_te)[:, 1]
        r["modelos"].append({"modelo": nome, **_metricas(y_te, probs[nome])})

    gb = modelos["Gradient boosting"]
    prob = probs["Gradient boosting"]

    # Separação aleatória × temporal (mesmo modelo, mesmo tamanho de teste)
    X_tr2, X_te2, y_tr2, y_te2 = train_test_split(X, y, test_size=len(y_te), stratify=y,
                                                  random_state=SEMENTE)
    gb2 = _pipeline(HistGradientBoostingClassifier(class_weight="balanced", random_state=SEMENTE),
                    categoricas, numericas).fit(X_tr2, y_tr2)
    # 'ano' como variável numérica (pergunta 3 da ficha)
    gb3 = _pipeline(HistGradientBoostingClassifier(class_weight="balanced", random_state=SEMENTE),
                    categoricas, numericas + ["ano"]).fit(X_tr, y_tr)
    r["separacao"] = [
        {"cenario": "Aleatória (todos os anos misturados)", **_metricas(y_te2, gb2.predict_proba(X_te2)[:, 1])},
        {"cenario": f"Temporal (treino ≤ {ANO_CORTE}, teste depois)", **_metricas(y_te, prob)},
        {"cenario": "Temporal, com 'ano' como variável", **_metricas(y_te, gb3.predict_proba(X_te)[:, 1])},
    ]

    # ---------- 3. Curvas ----------
    def amostrar(a, b, n=120):
        idx = np.unique(np.linspace(0, len(a) - 1, n).round().astype(int))
        return a[idx], b[idx]

    r["roc"], r["pr"] = {}, {}
    for nome in ("Regressão logística", "Gradient boosting"):
        fpr, tpr, _ = roc_curve(y_te, probs[nome])
        fpr, tpr = amostrar(fpr, tpr)
        r["roc"][nome] = [{"fpr": _r(a), "tpr": _r(b)} for a, b in zip(fpr, tpr)]
        prec, rec, _ = precision_recall_curve(y_te, probs[nome])
        rec, prec = amostrar(rec[::-1], prec[::-1])
        r["pr"][nome] = [{"recall": _r(a), "precisao": _r(b)} for a, b in zip(rec, prec)]

    # Calibração: class_weight='balanced' infla as probabilidades
    frac, media = calibration_curve(y_te, prob, n_bins=10, strategy="quantile")
    r["calibracao"] = [{"previsto": _r(m), "observado": _r(f)} for m, f in zip(media, frac)]
    r["prob_media_prevista"] = _r(prob.mean())

    # ---------- 4. Limiar ----------
    yv = y_te.to_numpy()
    r["limiares"] = []
    for t in np.round(np.arange(0.05, 0.96, 0.01), 2):
        p = prob >= t
        tp, fp = int((p & (yv == 1)).sum()), int((p & (yv == 0)).sum())
        fn, tn = int((~p & (yv == 1)).sum()), int((~p & (yv == 0)).sum())
        r["limiares"].append({"limiar": float(t), "vp": tp, "fp": fp, "fn": fn, "vn": tn})

    # ---------- 5. Equidade (limiar 0,5) ----------
    pred = prob >= 0.5
    r["equidade"] = {}
    for col in ("regiao", "raca_cor", "sexo"):
        linhas = []
        for cat, idx in X_te.groupby(col).groups.items():
            yy, pp = yv[X_te.index.get_indexer(idx)], pred[X_te.index.get_indexer(idx)]
            pos = int(yy.sum())
            if pos < 20:  # poucos óbitos: estimativa instável demais para mostrar
                continue
            vp = int((pp & (yy == 1)).sum())
            li, ls = _wilson(vp, pos)
            linhas.append({"grupo": str(cat), "obitos": pos, "recall": _r(vp / pos, 3),
                           "ic_inf": _r(li, 3), "ic_sup": _r(ls, 3),
                           "alarmes": int(pp.sum()), "n": int(len(yy))})
        r["equidade"][col] = sorted(linhas, key=lambda d: -d["obitos"])

    # ---------- 6. Importância por permutação ----------
    imp = permutation_importance(gb, X_te, y_te, scoring="average_precision", n_repeats=10,
                                 random_state=SEMENTE)
    r["importancia"] = sorted(
        [{"variavel": c, "media": _r(m), "dp": _r(s)}
         for c, m, s in zip(X_te.columns, imp.importances_mean, imp.importances_std)],
        key=lambda d: -d["media"])[:12]

    saida.write_text(json.dumps(r, ensure_ascii=False, indent=1))
    gbm = r["modelos"][2]
    log.info("análise leishmaniose: AUC-ROC %.3f, AUC-PR %.3f", gbm["auc_roc"], gbm["auc_pr"])
    return r


def gerar(pasta: Path) -> None:
    leishmaniose(pasta / "leishmaniose_obito.csv", pasta / "leishmaniose_obito_analise.json")
