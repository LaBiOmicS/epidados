# Plano do projeto: Saúde em Dados (nome provisório)

Plataforma aberta de ensino com dados reais do DATASUS, com duas portas de entrada:

- **Saúde**: estudos de caso interprofissionais (veterinária, medicina, farmácia, enfermagem, odontologia)
- **Dados/IA**: datasets prontos para machine learning (scikit-learn) para TI, estatística e ciência de dados

Tudo gratuito: GitHub Pages (site), GitHub Actions (atualização), OpenML (datasets) e Zenodo (DOI).

---

## 1. Escopo da v1

### Estudos de caso (saúde)

| # | Caso | Bases | Cursos |
|---|---|---|---|
| 1 | Sífilis congênita | SINAN (SIFG, SIFC), SINASC, SIM | Med, Farm, Enf, Odonto |
| 2 | Intoxicações exógenas | SINAN (IEXO), SIM | Vet, Med, Farm, Enf |
| 3 | Acidentes com material biológico | SINAN (ACBI), CNES | Med, Farm, Enf, Odonto |
| 4 | Zoonoses e Saúde Única | SINAN (LEIV, LEPT, ANTR), SIM | Vet, Med, Farm, Enf |
| 5 | Violência | SINAN (VIOL), SIM | Med, Enf, Odonto |
| T | Onde estão os profissionais? (transversal) | CNES | Todos |

Cada caso traz um tronco comum (contexto, mapa, série, conceitos), lentes por profissão (perguntas), um quadro "Limites do dado" e um gabarito para o professor (separado).

### Datasets de ML

| Dataset | Base | Tarefa |
|---|---|---|
| Baixo peso ao nascer | SINASC | Classificação binária (vazamento, categóricas) |
| Óbito por leishmaniose visceral | SINAN LEIV | Classificação desbalanceada |
| Dengue semanal por UF | SINAN DENG | Séries temporais |

Cada dataset traz uma versão mini (≤10 mil linhas) e uma completa, uma ficha técnica (*Datasheets for Datasets*), um notebook de linha de base no Colab e publicação no OpenML (`fetch_openml`).

### Fora da v1

MCP, SIH/SIA, dados de doença animal, análises espaciais avançadas no site.

---

## 2. Arquitetura

```
ftp.datasus.gov.br ─┐
IBGE (pop., malhas) ─┤
                     ▼
        pipeline/ (Python + DuckDB)
        baixa .dbc → descompacta → harmoniza → agrega → valida
                     │
       ┌─────────────┼──────────────────┐
       ▼             ▼                  ▼
  site/dados/   datasets/ml/        testes contra TabNet
  (CSV/JSON)    (Parquet/CSV)       (totais oficiais)
       │             │
       ▼             ├──► OpenML
  site/ (Quarto) ────┴──► GitHub Pages
       │
       └──► Zenodo (DOI por versão anual)
```

### Escolhas técnicas

| Item | Escolha | Motivo |
|---|---|---|
| Pipeline | Python 3.12, `uv`, DuckDB, pandas | DuckDB agrega milhões de linhas em segundos, sem servidor |
| Leitura `.dbc` | `pyreaddbc` (ou PySUS) | Bibliotecas maduras para o formato |
| Site | **Quarto** + Observable JS / Plotly | Feito para conteúdo acadêmico; páginas com texto, gráficos e exercícios; exporta PDF para o professor; publica direto no GitHub Pages |
| Mapas | Malha municipal do IBGE (GeoJSON simplificado) | Pública; simplificada para carregar rápido |
| Automação | GitHub Actions (cron mensal) | Gratuito; reexecuta o pipeline e republica |
| ML | `openml-python` para publicar | Integração nativa com `sklearn.datasets.fetch_openml` |

### Estrutura do repositório

```
epidados/
├── pipeline/
│   ├── baixar.py          # FTP DATASUS + IBGE, com cache
│   ├── harmonizar/        # um módulo por sistema (sinan.py, sim.py, sinasc.py, cnes.py)
│   ├── agregar.py         # recortes para o site
│   ├── ml/                # um script por dataset de ML
│   └── validar.py         # compara totais com o TabNet
├── site/                  # projeto Quarto
│   ├── casos/             # um .qmd por estudo de caso
│   ├── dados-ia/          # páginas dos datasets
│   └── professor/         # gabaritos (fora da navegação pública)
├── notebooks/             # linhas de base no Colab
├── docs/armadilhas.md     # decisões de tratamento e armadilhas dos dados
└── .github/workflows/
```

---

## 3. Regras de tratamento (valem para tudo)

1. **Casos confirmados** por padrão (`CLASSI_FIN`), declarado em cada página.
2. **Município de residência** para epidemiologia; o de notificação só quando o caso for sobre o serviço.
3. **Código IBGE com 7 dígitos** em todas as saídas (o SINAN usa 6).
4. **Final × preliminar** marcado em todo dado, com a data de extração.
5. **Supressão de células com menos de 5 casos** em recortes de perfil.
6. **Datasets individuais de ML**: município vira UF ou região, datas viram ano ou mês, idades extremas são agrupadas. **Violência e HIV nunca entram em nível individual.**
7. **Validação**: os totais por UF e ano precisam bater com o TabNet (tolerância documentada).

---

## 4. Fases

A estratégia é uma **fatia vertical primeiro**: um caso e um dataset completos, publicados de ponta a ponta, antes de expandir. Assim os riscos técnicos aparecem cedo.

### Fase 0: Verificação (semana 1)
- Baixar 1 ano de LEIV, LEPT, ANTR, SINASC, SIM e CNES; inspecionar os campos reais
- Confirmar as fontes de população e malha do IBGE
- Identificar o arquivo `ESPOBR`
- Medir tamanhos e tempos de processamento (cabem no GitHub Actions?)
- **Entrega:** `docs/armadilhas.md` (1ª versão) e decisão de seguir ou ajustar o escopo

### Fase 1: Fatia vertical (semanas 2–4)
- Pipeline completo para **zoonoses** (LEIV, LEPT, ANTR) e **SIM**
- Site Quarto com **Caso 4 (Zoonoses)**: mapa, série, lentes, limites do dado
- Dataset de ML **Óbito por leishmaniose visceral** com ficha e notebook
- Publicação no GitHub Pages + automação mensal
- **Entrega:** link público funcionando, que você mostra a um colega

### Fase 2: Saúde materno-infantil (semanas 5–7)
- SINASC + SINAN sífilis
- **Caso 1 (Sífilis congênita)**
- Datasets **Baixo peso ao nascer** (classificação + versão de regressão)

### Fase 3: Restante dos casos (semanas 8–10)
- **Casos 2 (Intoxicações), 3 (Material biológico), 5 (Violência)** e **módulo CNES**
- Dataset **Dengue semanal por UF**

### Fase 4: Acabamento e publicação (semanas 11–12)
- Revisão das lentes por docentes de cada área
- Gabaritos do professor, exportação em PDF
- Publicação no OpenML; release v1.0 com DOI no Zenodo
- Página "Como citar" e "Como usar em aula"

### Fase 5: Piloto e artigos (semestre seguinte)
- Uso em pelo menos uma disciplina de saúde e uma de dados/IA
- Coleta de avaliação (**requer aprovação no CEP antes**)
- Artigos: data paper (datasets) e relato de experiência (ensino)

---

## 5. Divisão de trabalho

| Quem | O quê |
|---|---|
| **Claude** | Pipeline, site, datasets, notebooks, validação, rascunho dos textos e das perguntas |
| **Você** | Validar conteúdo, escolher a ordem dos casos, recrutar docentes revisores, piloto, CEP, conta GitHub |
| **Docentes revisores** | Revisar as lentes da sua profissão (1 por área) |

---

## 6. Riscos

| Risco | Mitigação |
|---|---|
| DATASUS fora do ar ou mudança de formato | Cache dos arquivos brutos; versões congeladas no Zenodo |
| Pipeline estoura o tempo do GitHub Actions | Medir na Fase 0; processar só os anos novos (incremental) |
| Números divergem do TabNet | Testes automáticos de validação; divergências documentadas |
| Conteúdo de uma área fica raso | Revisão obrigatória por docente da área antes do piloto |
| Reidentificação nos datasets de ML | Regras da seção 3.6; revisão antes de publicar no OpenML |

---

## 7. Decisões pendentes

1. Nome do projeto
2. Conta/organização no GitHub onde ficará o repositório
3. Disciplina(s) do piloto (define a ordem dos casos; hoje a Fase 1 começa por Zoonoses)
4. Docentes revisores por área
5. Coautores e afiliação institucional (para Zenodo e artigos)

---

## 8. Situação (2026-11-12)

**Fase 0 e Fase 1 concluídas** (fatia vertical):

- Pipeline: SINAN (LEIV, LEPT, ANTR, 2007–2026) + IBGE (municípios, população, malhas)
- Validação: casos confirmados de LEIV e LEPT **idênticos ao TabNet** em todos os anos (9 testes)
- Site: estudo de caso Zoonoses (mapas, séries, perfis, lentes por profissão), metodologia, Dados para IA
- Dataset de IA: óbito por leishmaniose visceral (45 mil casos) + notebook de linha de base
- Roteiro do professor em PDF (`professor/`, fora do site)
- Workflow do GitHub Actions pronto (falta o repositório)

Mudança de rumo registrada: os dados de 2007–2025 **não** mostram a leishmaniose migrando para o Sudeste. A história real é "menos casos, mais mortes" (casos em adultos e coinfecção por HIV).

Próximo: Fase 2 (SINASC + sífilis, dataset de baixo peso ao nascer).
